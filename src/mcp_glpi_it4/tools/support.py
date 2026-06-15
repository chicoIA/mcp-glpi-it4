"""Tools de apoio: referências, sessão, modo de escrita e reversão."""
from __future__ import annotations

from . import guard
from ..config import Settings
from ..glpi.core import GLPIClient


def register(mcp, client: GLPIClient, settings: Settings) -> None:

    @mcp.tool()
    @guard
    async def glpi_listar_categorias(limite: int = 50) -> dict:
        """Lista as categorias ITIL para classificar chamados."""
        data = await client.list_items("ITILCategory", start=0, limit=limite)
        return {"status": "ok", "items": data}

    @mcp.tool()
    @guard
    async def glpi_listar_entidades(limite: int = 50) -> dict:
        """Lista as entidades disponíveis no GLPI."""
        data = await client.list_items("Entity", start=0, limit=limite)
        return {"status": "ok", "items": data}

    @mcp.tool()
    @guard
    async def glpi_listar_grupos(limite: int = 50) -> dict:
        """Lista os grupos do GLPI (para atribuição de chamados)."""
        data = await client.list_items("Group", start=0, limit=limite)
        return {"status": "ok", "items": data}

    @mcp.tool()
    @guard
    async def glpi_status_sessao() -> dict:
        """Valida credenciais/conectividade autenticando na API (OAuth2)."""
        await client.authenticate()
        return {"status": "ok", "autenticado": True, "api_url": settings.api_url,
                "write_mode": settings.write_mode}

    @mcp.tool()
    @guard
    async def glpi_modo_escrita() -> dict:
        """Informa o modo de escrita atual: dry_run (simula) ou live (executa)."""
        return {"status": "ok", "write_mode": settings.write_mode,
                "dry_run": settings.dry_run,
                "nota": "Em dry_run nenhuma alteração é gravada no GLPI."}

    @mcp.tool()
    @guard
    async def glpi_reverter(audit_id: str | None = None) -> dict:
        """Reverte uma operação de escrita (por audit_id) ou TODAS as pendentes,
        em ordem reversa. Sem argumento, reverte o lote pendente registrado."""
        return await client.revert(audit_id)

    @mcp.tool()
    @guard
    async def glpi_listar_reversiveis() -> dict:
        """Lista as operações de escrita ainda reversíveis (pendentes de reversão)."""
        pend = client.audit.pending()
        return {"status": "ok", "count": len(pend),
                "items": [{"audit_id": p["audit_id"], "op": p["op"],
                           "resource": p.get("resource"), "id": p.get("id"),
                           "ts": p.get("ts")} for p in pend]}
