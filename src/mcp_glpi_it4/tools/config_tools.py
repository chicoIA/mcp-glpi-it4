"""Tools de Configuração de parâmetros do sistema — /Setup/Config.

Operações sensíveis. Leitura livre; escrita exige GLPI_WRITE_MODE=live e grava
o valor anterior para reversão. Parâmetros de risco ficam fora por allowlist.
"""
from __future__ import annotations

from . import guard
from ..glpi.core import GLPIClient

# Parâmetros bloqueados para escrita via API (segurança operacional).
CONFIG_BLOQUEADOS = {
    ("core", "url_base"), ("core", "url_base_api"),
    ("core", "smtp_password"), ("core", "proxy_passwd"),
    ("core", "glpinetwork_registration_key"),
}


def register(mcp, client: GLPIClient) -> None:

    @mcp.tool()
    @guard
    async def glpi_listar_config(context: str | None = None) -> dict:
        """Lista parâmetros de configuração. Sem 'context' lista todos os contextos;
        com 'context' (ex.: 'core') lista os parâmetros daquele contexto."""
        if context:
            data = await client.get_item("Config", context)
        else:
            data = await client.list_items("Config")
        return {"status": "ok", "context": context, "data": data}

    @mcp.tool()
    @guard
    async def glpi_consultar_config(context: str, name: str) -> dict:
        """Lê um parâmetro específico (ex.: context='core', name='default_requesttypes_id')."""
        data = await client.get_item("Config", f"{context}/{name}")
        return {"status": "ok", "context": context, "name": name, "data": data}

    @mcp.tool()
    @guard
    async def glpi_atualizar_config(context: str, name: str, value: str) -> dict:
        """Altera um parâmetro de configuração (reversível). Exige GLPI_WRITE_MODE=live.
        Parâmetros sensíveis (URL base, senhas, chaves) são bloqueados."""
        if (context, name) in CONFIG_BLOQUEADOS:
            return {"status": "error", "code": 403,
                    "detail": f"Parâmetro '{context}/{name}' bloqueado para escrita via API."}
        # usa o caminho composto context/name como 'item_id' do recurso Config
        return await client.update_item("Config", f"{context}/{name}", {"value": value})
