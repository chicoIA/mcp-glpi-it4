"""Cliente HTTP async para a GLPI High-level API v2.3 (OAuth2 Password Grant).

Recursos:
- Autenticação OAuth2 + auto-refresh (renova 60s antes de expirar).
- Re-autenticação automática única em caso de 401 numa chamada de negócio.
- Retry com backoff para GET / 429 / 5xx.
- Mapeamento HTTP → erro limpo (GLPIError) com 'hint'.
- Escrita protegida por dry_run e sempre auditada (rollback).
"""
from __future__ import annotations

import asyncio
import time

import httpx

from ..config import Settings
from .audit import Auditor
from . import maps

# Método de atualização da v2.3 (a confirmar no Swagger; ver SDD §1.2).
UPDATE_METHOD = "PATCH"

_HINTS = {
    400: "Payload ou filtro RSQL inválido. Verifique campos e sintaxe do 'filter'.",
    401: "Token inválido/expirado. Verifique Client ID/Secret e usuário/senha.",
    403: "Perfil OAuth sem permissão sobre o recurso.",
    404: "Recurso/endpoint inexistente. O path pode divergir nesta versão.",
    422: "Dados não processáveis. Confira tipos e campos obrigatórios.",
    429: "Limite de requisições atingido.",
}


class GLPIError(RuntimeError):
    def __init__(self, status: int, message: str, hint: str = ""):
        self.status = status
        self.hint = hint or _HINTS.get(status, "")
        super().__init__(message)

    def as_dict(self) -> dict:
        return {"status": "error", "code": self.status,
                "detail": str(self), "hint": self.hint}


class GLPIClient:
    def __init__(self, settings: Settings, auditor: Auditor | None = None,
                 http: httpx.AsyncClient | None = None):
        self.s = settings
        self.audit = auditor or Auditor(settings.audit_dir)
        self._http = http
        self._owns_http = http is None
        self._token: str | None = None
        self._expires_at: float = 0.0

    # ── ciclo de vida ───────────────────────────────────────────────────────
    @property
    def http(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self.s.timeout)
        return self._http

    async def aclose(self) -> None:
        if self._http is not None and self._owns_http:
            await self._http.aclose()
            self._http = None

    # ── autenticação ────────────────────────────────────────────────────────
    async def authenticate(self) -> None:
        resp = await self.http.post(self.s.token_url, data={
            "grant_type": "password",
            "client_id": self.s.client_id,
            "client_secret": self.s.client_secret,
            "username": self.s.username,
            "password": self.s.password,
            "scope": self.s.scope,
        })
        if resp.status_code != 200:
            raise GLPIError(resp.status_code,
                            f"Falha de autenticação: {resp.text}", _HINTS.get(401, ""))
        data = resp.json()
        self._token = data["access_token"]
        self._expires_at = time.time() + int(data.get("expires_in", 3600))

    async def _ensure_token(self) -> None:
        if not self._token or time.time() >= self._expires_at - 60:
            await self.authenticate()

    @property
    def _headers(self) -> dict:
        # Content-Type NÃO entra aqui: em GET (sem corpo) o GLPI v2.3 rejeitaria
        # com 400 "Invalid JSON body". Ele é adicionado só quando há payload.
        return {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}

    # ── requisição base com resiliência ───────────────────────────────────────
    async def request(self, method: str, path: str, *, params: dict | None = None,
                       json: dict | None = None, _reauthed: bool = False) -> httpx.Response:
        await self._ensure_token()
        url = f"{self.s.api_url}/{path.lstrip('/')}"
        headers = self._headers
        if json is not None:
            headers = {**headers, "Content-Type": "application/json"}
        attempt = 0
        while True:
            resp = await self.http.request(method, url, headers=headers,
                                           params=params, json=json)
            # 401 → re-autentica uma vez e repete
            if resp.status_code == 401 and not _reauthed:
                self._token = None
                await self._ensure_token()
                return await self.request(method, path, params=params, json=json,
                                          _reauthed=True)
            # retry para GET / 429 / 5xx
            retriable = resp.status_code == 429 or resp.status_code >= 500
            if retriable and (method.upper() == "GET" or resp.status_code == 429) \
                    and attempt < self.s.max_retries:
                await asyncio.sleep(0.5 * (2 ** attempt))
                attempt += 1
                continue
            if resp.status_code >= 400:
                self.audit.log_error(method, url, resp.status_code, resp.text, json)
                raise GLPIError(resp.status_code,
                                f"{method} /{path} → HTTP {resp.status_code}: {resp.text[:500]}")
            return resp

    # ── operações de leitura ──────────────────────────────────────────────────
    async def list_items(self, resource: str, *, rsql: str | None = None,
                          start: int | None = None, limit: int | None = None,
                          sort: str | None = None,
                          params: dict | None = None) -> list | dict:
        # A HL API v2 pagina por 'start'/'limit' (query string), não por 'range'.
        p = dict(params or {})
        if rsql:
            p["filter"] = rsql
        if start is not None:
            p["start"] = start
        if limit is not None:
            p["limit"] = limit
        if sort:
            p["sort"] = sort
        resp = await self.request("GET", maps.resource_path(resource), params=p)
        return resp.json()

    async def get_item(self, resource: str, item_id, *, sub: str | None = None,
                       params: dict | None = None) -> dict:
        path = f"{maps.resource_path(resource)}/{item_id}"
        if sub:
            path += f"/{sub}"
        resp = await self.request("GET", path, params=params)
        return resp.json()

    # ── operações de escrita (dry_run + auditoria) ────────────────────────────
    async def create_item(self, resource: str, payload: dict, *, name_key: str = "name") -> dict:
        path = maps.resource_path(resource)
        if self.s.dry_run:
            return {"status": "dry_run", "op": "create", "path": path, "would_send": payload}
        resp = await self.request("POST", path, json=payload)
        data = resp.json()
        if isinstance(data, list):
            data = data[0] if data else {}
        item_id = data.get("id")
        entry = self.audit.record_create(resource, path, item_id, str(payload.get(name_key, "")))
        return {"status": "ok", "op": "create", "id": item_id,
                "audit_id": entry["audit_id"], "data": data}

    async def update_item(self, resource: str, item_id, payload: dict) -> dict:
        path = maps.resource_path(resource)
        # snapshot dos campos que serão alterados (para reversão)
        before: dict = {}
        try:
            current = await self.get_item(resource, item_id)
            before = {k: current.get(k) for k in payload.keys()}
        except GLPIError:
            before = {}
        if self.s.dry_run:
            return {"status": "dry_run", "op": "update", "path": f"{path}/{item_id}",
                    "before": before, "would_send": payload}
        resp = await self.request(UPDATE_METHOD, f"{path}/{item_id}", json=payload)
        entry = self.audit.record_update(resource, path, item_id, before, payload)
        return {"status": "ok", "op": "update", "id": item_id,
                "audit_id": entry["audit_id"], "before": before, "data": resp.json()}

    async def delete_item(self, resource: str, item_id, *, soft: bool = True) -> dict:
        path = maps.resource_path(resource)
        if self.s.dry_run:
            return {"status": "dry_run", "op": "delete", "path": f"{path}/{item_id}", "soft": soft}
        if soft:
            # soft-delete reversível via flag is_deleted
            resp = await self.request(UPDATE_METHOD, f"{path}/{item_id}", json={"is_deleted": 1})
            result = resp.json() if resp.content else {}
        else:
            resp = await self.request("DELETE", f"{path}/{item_id}")
            result = {}
        entry = self.audit.record_delete(resource, path, item_id, {"soft": soft})
        return {"status": "ok", "op": "delete", "id": item_id,
                "audit_id": entry["audit_id"], "soft": soft, "data": result}

    async def create_sub(self, resource: str, item_id, sub_path: str, payload: dict) -> dict:
        """Cria um subitem (ex.: Timeline/Followup, TeamMember/{role})."""
        base = maps.resource_path(resource)
        full = f"{base}/{item_id}/{sub_path}"
        if self.s.dry_run:
            return {"status": "dry_run", "op": "create_sub", "path": full, "would_send": payload}
        resp = await self.request("POST", full, json=payload)
        data = resp.json()
        if isinstance(data, list):
            data = data[0] if data else {}
        entry = self.audit.record_create(f"{resource}:{sub_path}", full, data.get("id"), "")
        return {"status": "ok", "op": "create_sub", "path": full,
                "audit_id": entry["audit_id"], "data": data}

    # ── reversão ──────────────────────────────────────────────────────────────
    async def revert(self, audit_id: str | None = None) -> dict:
        """Reverte uma operação (audit_id) ou todas as pendentes, em ordem reversa."""
        targets = [self.audit.get(audit_id)] if audit_id else list(reversed(self.audit.pending()))
        targets = [t for t in targets if t and not t.get("reverted")]
        results = []
        for entry in targets:
            res = await self._revert_one(entry)
            results.append(res)
            if res.get("status") == "ok":
                self.audit.mark_reverted(entry["audit_id"])
        return {"status": "ok", "reverted": len([r for r in results if r["status"] == "ok"]),
                "details": results}

    async def _revert_one(self, entry: dict) -> dict:
        op, path, item_id = entry["op"], entry["path"], entry["id"]
        try:
            if op in ("create", "create_sub"):
                await self.request("DELETE", f"{path}/{item_id}")
            elif op == "update":
                await self.request(UPDATE_METHOD, f"{path}/{item_id}", json=entry.get("before", {}))
            elif op == "delete":
                await self.request(UPDATE_METHOD, f"{path}/{item_id}", json={"is_deleted": 0})
            return {"audit_id": entry["audit_id"], "op": op, "status": "ok"}
        except GLPIError as e:
            return {"audit_id": entry["audit_id"], "op": op, "status": "error", "detail": str(e)}
