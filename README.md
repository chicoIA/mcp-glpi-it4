# mcp-glpi-it4

**English** · [Português](README.pt-BR.md)

[![tests](https://github.com/chicoIA/mcp-glpi-it4/actions/workflows/tests.yml/badge.svg)](https://github.com/chicoIA/mcp-glpi-it4/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)

MCP Server for **GLPI** through the **High-level API v2.3 (OAuth2)**. It exposes tickets,
computer inventory, users and configuration parameters as tools for MCP clients such as
Claude Desktop and Claude Code.

- **API:** `api.php/v2.3` · **Auth:** OAuth2 Password Grant
- **Stack:** Python 3.12 · FastMCP · httpx (async)
- **Safety:** `dry_run` by default, and every write is revertible
- **Transports:** `stdio` (local) and `streamable-http` (shared container)

Works with any GLPI 11 instance that has the v2.3 API enabled — set `GLPI_BASE_URL` to yours.

## Why a new server

The public MCP servers we evaluated (`GMS64260/mcp-glpi`, `svtica/glpi-mcp`) authenticate through
the **legacy API** (Session-Token), which is incompatible with v2.3/OAuth2, and they do not cover
configuration parameters or rollback.

## Quick start — Docker

```bash
cp .env.example .env          # set GLPI_BASE_URL + OAuth credentials
docker build -t mcp-glpi-it4 .

# A) stdio — the MCP client starts one container per session
docker run -i --rm --env-file .env -v glpi_audit:/data mcp-glpi-it4

# B) streamable-http — one long-running server on http://localhost:8000/mcp
docker compose up -d
```

Mount `glpi_audit:/data`: that volume holds the rollback log. Full guide, client configuration and
security notes: **[docs/en/DOCKER.md](docs/en/DOCKER.md)**.

## Quick start — local install

```bash
pip install -e ".[dev]"   # or: uv sync
cp .env.example .env
mcp-glpi-it4              # stdio
```

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `GLPI_BASE_URL` | **yes** | — | Base URL of your GLPI instance |
| `GLPI_CLIENT_ID` / `GLPI_CLIENT_SECRET` | **yes** | — | OAuth client (`Setup > OAuth Clients`) |
| `GLPI_USERNAME` / `GLPI_PASSWORD` | **yes** | — | Service account |
| `GLPI_API_VERSION` | — | `v2.3` | API version |
| `GLPI_OAUTH_SCOPE` | — | `api` | OAuth scope |
| `GLPI_WRITE_MODE` | — | `dry_run` | `dry_run` (simulates) \| `live` (executes) |
| `GLPI_AUDIT_DIR` | — | `~/.mcp-glpi-it4` | Where the rollback/error logs are written (`/data` in Docker) |
| `GLPI_TIMEOUT` / `GLPI_MAX_RETRIES` | — | `15` / `3` | HTTP tuning |
| `MCP_TRANSPORT` | — | `stdio` | `stdio` \| `streamable-http` \| `sse` |
| `FASTMCP_HOST` / `FASTMCP_PORT` | — | `0.0.0.0` / `8000` | HTTP transports only (read by FastMCP) |

## Use with Claude Desktop

Without Docker — `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or
`%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "glpi-it4": {
      "command": "python",
      "args": ["-m", "mcp_glpi_it4.server"],
      "env": {
        "PYTHONPATH": "/path/to/mcp-glpi-it4/src",
        "GLPI_BASE_URL": "https://glpi.example.com",
        "GLPI_CLIENT_ID": "...", "GLPI_CLIENT_SECRET": "...",
        "GLPI_USERNAME": "...", "GLPI_PASSWORD": "...",
        "GLPI_WRITE_MODE": "dry_run"
      }
    }
  }
}
```

With Docker, see [docs/en/DOCKER.md](docs/en/DOCKER.md). Prompt examples: [docs/en/USAGE.md](docs/en/USAGE.md).

## Tools (29)

Tool names and arguments are in Portuguese and are kept stable — renaming them would break
existing prompts. Prompt in whatever language you like; the model maps your wording to the tool.

**Tickets:** `glpi_listar_chamados`, `glpi_consultar_chamado`, `glpi_criar_chamado`, `glpi_atualizar_chamado`, `glpi_adicionar_acompanhamento`, `glpi_adicionar_tarefa`, `glpi_adicionar_solucao`, `glpi_atribuir_chamado`, `glpi_excluir_chamado`.

**Inventory:** `glpi_listar_computadores`, `glpi_consultar_ativo`, `glpi_criar_computador`, `glpi_atualizar_computador`, `glpi_excluir_computador`.

**Users:** `glpi_listar_usuarios`, `glpi_consultar_usuario`, `glpi_listar_perfis`, `glpi_criar_usuario`, `glpi_excluir_usuario`.

**Configuration:** `glpi_listar_config`, `glpi_consultar_config`, `glpi_atualizar_config`.

**Support/Safety:** `glpi_listar_categorias`, `glpi_listar_entidades`, `glpi_listar_grupos`, `glpi_status_sessao`, `glpi_modo_escrita`, `glpi_reverter`, `glpi_listar_reversiveis`.

## Safety and rollback

- **`dry_run` (default):** every write only returns the payload it *would* send; nothing changes.
- **`live`:** performs the write; each operation is recorded in `rollback_log.json` with a snapshot
  of the previous state.
- **Revert:** `glpi_reverter` (one operation by `audit_id`, or all pending ones).
  See [docs/en/ROLLBACK.md](docs/en/ROLLBACK.md).

## Documentation

| | English | Português |
|---|---|---|
| Usage | [USAGE.md](docs/en/USAGE.md) | [USO.md](docs/pt-BR/USO.md) |
| Docker | [DOCKER.md](docs/en/DOCKER.md) | [DOCKER.md](docs/pt-BR/DOCKER.md) |
| Rollback | [ROLLBACK.md](docs/en/ROLLBACK.md) | [REVERSAO.md](docs/pt-BR/REVERSAO.md) |
| Development | [DEVELOPMENT.md](docs/en/DEVELOPMENT.md) | [DESENVOLVIMENTO.md](docs/pt-BR/DESENVOLVIMENTO.md) |

Translations are welcome: add `docs/<lang-tag>/` and `README.<lang-tag>.md`, then link them from the
language row at the top. See [DEVELOPMENT.md](docs/en/DEVELOPMENT.md#translations).

## Tests

```bash
pip install -e ".[dev]"
pytest -q
```

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 IT4Solução and contributors.

You may use, copy, modify, merge, publish, distribute, sublicense and sell copies of this software,
including commercially, provided the copyright notice and the license text are kept in all copies.
The software is provided "as is", without warranty of any kind.

GLPI itself is a separate project, licensed under the GPL, and is not distributed here.
