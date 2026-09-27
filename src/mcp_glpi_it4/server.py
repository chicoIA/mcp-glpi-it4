"""Entrypoint / MCP Server entrypoint (GLPI).

Run / Executar:  python -m mcp_glpi_it4.server
Transport: MCP_TRANSPORT=stdio (default) | streamable-http | sse
Host/port for HTTP transports: FASTMCP_HOST / FASTMCP_PORT.
Env vars GLPI_* são obrigatórias — ver .env.example.
"""
from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from .config import Settings
from .glpi.audit import Auditor
from .glpi.core import GLPIClient
from .tools import assets, config_tools, support, tickets, users


def build_server() -> FastMCP:
    settings = Settings.from_env()
    auditor = Auditor(settings.audit_dir)
    client = GLPIClient(settings, auditor=auditor)

    # FastMCP passa host/port explicitamente para o seu Settings, então as env
    # FASTMCP_* sozinhas não valem — em container tem que ser lido aqui.
    mcp = FastMCP("glpi-it4",
                  host=os.environ.get("FASTMCP_HOST", "127.0.0.1"),
                  port=int(os.environ.get("FASTMCP_PORT", "8000")))
    tickets.register(mcp, client)
    assets.register(mcp, client)
    config_tools.register(mcp, client)
    support.register(mcp, client, settings)
    users.register(mcp, client)
    return mcp


def main() -> None:
    # stdio para clientes locais (Claude Desktop/Code); streamable-http para
    # container de longa duração servindo vários clientes.
    build_server().run(transport=os.environ.get("MCP_TRANSPORT", "stdio"))


if __name__ == "__main__":
    main()
