"""Entrypoint do MCP Server GLPI (IT4Solução).

Executar:  python -m mcp_glpi_it4.server   (transporte stdio)
Requer as variáveis de ambiente de GLPI_* (ver .env.example).
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .config import Settings
from .glpi.audit import Auditor
from .glpi.core import GLPIClient
from .tools import assets, config_tools, support, tickets


def build_server() -> FastMCP:
    settings = Settings.from_env()
    auditor = Auditor(settings.audit_dir)
    client = GLPIClient(settings, auditor=auditor)

    mcp = FastMCP("glpi-it4")
    tickets.register(mcp, client)
    assets.register(mcp, client)
    config_tools.register(mcp, client)
    support.register(mcp, client, settings)
    return mcp


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
