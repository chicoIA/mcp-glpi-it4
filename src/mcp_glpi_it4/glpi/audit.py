"""Auditoria e reversão: registra toda escrita com snapshot para permitir rollback.

Mandato do projeto: TODA alteração feita via API precisa ter caminho de reversão.
- create → reversão = delete
- update → guarda o estado ANTERIOR dos campos alterados → reversão = re-aplicar
- delete → soft-delete (is_deleted=1) → reversão = restaurar (is_deleted=0)
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone

ROLLBACK_LOG = "rollback_log.json"
ERROR_LOG = "error_log.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Auditor:
    def __init__(self, audit_dir: str = "."):
        self.dir = audit_dir
        self.rollback_path = os.path.join(audit_dir, ROLLBACK_LOG)
        self.error_path = os.path.join(audit_dir, ERROR_LOG)
        self._lock = threading.Lock()

    # ── leitura/escrita de arquivo ────────────────────────────────────────────
    def _read(self, path: str) -> dict:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"_meta": {"created_at": _now()}, "items": []}

    def _write(self, path: str, data: dict) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── registro de operações ──────────────────────────────────────────────────
    def _append(self, entry: dict) -> dict:
        entry.setdefault("audit_id", uuid.uuid4().hex[:12])
        entry.setdefault("ts", _now())
        entry.setdefault("reverted", False)
        with self._lock:
            log = self._read(self.rollback_path)
            log["items"].append(entry)
            self._write(self.rollback_path, log)
        return entry

    def record_create(self, resource: str, path: str, item_id, name: str = "") -> dict:
        return self._append({
            "op": "create", "resource": resource, "path": path,
            "id": item_id, "name": name,
        })

    def record_update(self, resource: str, path: str, item_id, before: dict, after: dict) -> dict:
        return self._append({
            "op": "update", "resource": resource, "path": path,
            "id": item_id, "before": before, "after": after,
        })

    def record_delete(self, resource: str, path: str, item_id, before: dict | None = None) -> dict:
        return self._append({
            "op": "delete", "resource": resource, "path": path,
            "id": item_id, "before": before or {},
        })

    # ── consulta ────────────────────────────────────────────────────────────────
    def load(self) -> list[dict]:
        return self._read(self.rollback_path).get("items", [])

    def pending(self) -> list[dict]:
        return [i for i in self.load() if not i.get("reverted")]

    def get(self, audit_id: str) -> dict | None:
        return next((i for i in self.load() if i.get("audit_id") == audit_id), None)

    def mark_reverted(self, audit_id: str) -> None:
        with self._lock:
            log = self._read(self.rollback_path)
            for i in log["items"]:
                if i.get("audit_id") == audit_id:
                    i["reverted"] = True
                    i["reverted_at"] = _now()
            self._write(self.rollback_path, log)

    # ── erros ─────────────────────────────────────────────────────────────────
    def log_error(self, method: str, url: str, status: int, response: str,
                  payload: dict | None = None) -> None:
        with self._lock:
            log = self._read(self.error_path)
            log["items"].append({
                "ts": _now(), "method": method, "url": url,
                "status": status, "response": (response or "")[:2000],
                "payload": payload or {},
            })
            self._write(self.error_path, log)
