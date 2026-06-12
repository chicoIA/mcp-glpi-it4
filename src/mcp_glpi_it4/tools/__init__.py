"""Tools MCP, agrupadas por domínio. Cada módulo expõe register(mcp, client)."""
from __future__ import annotations

import functools

from ..glpi.core import GLPIError


def guard(fn):
    """Captura erros e devolve resposta MCP limpa, preservando a assinatura (schema)."""
    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except GLPIError as e:
            return e.as_dict()
        except Exception as e:  # noqa: BLE001
            return {"status": "error", "detail": str(e)}
    return wrapper


def build_rsql(equals: dict) -> str | None:
    """Monta filtro RSQL com AND (';') a partir de pares campo==valor não nulos."""
    parts = [f"{k}=={v}" for k, v in equals.items() if v is not None]
    return ";".join(parts) if parts else None


def compact(d: dict) -> dict:
    """Remove chaves com valor None (para montar payloads parciais)."""
    return {k: v for k, v in d.items() if v is not None}
