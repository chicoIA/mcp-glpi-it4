# mcp-glpi-it4

[English](README.md) · **Português**

[![tests](https://github.com/chicoIA/mcp-glpi-it4/actions/workflows/tests.yml/badge.svg)](https://github.com/chicoIA/mcp-glpi-it4/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)

MCP Server para integração com o **GLPI** via **High-level API v2.3 (OAuth2)**. Expõe chamados,
inventário de computadores, usuários e parâmetros de configuração como ferramentas (tools) para
clientes MCP como o Claude Desktop e o Claude Code.

- **API:** `api.php/v2.3` · **Auth:** OAuth2 Password Grant
- **Stack:** Python 3.12 · FastMCP · httpx (async)
- **Segurança:** `dry_run` por padrão e reversão de toda escrita
- **Transportes:** `stdio` (local) e `streamable-http` (container compartilhado)

Funciona com qualquer instância GLPI 11 com a API v2.3 ativa — basta apontar `GLPI_BASE_URL`.

## Por que um servidor novo

Os MCPs públicos avaliados (`GMS64260/mcp-glpi`, `svtica/glpi-mcp`) autenticam pela **API legacy**
(Session-Token), incompatível com a v2.3/OAuth2, e não cobrem configuração de parâmetros nem reversão.

## Início rápido — Docker

```bash
cp .env.example .env          # preencha GLPI_BASE_URL + credenciais OAuth
docker build -t mcp-glpi-it4 .

# A) stdio — o cliente MCP sobe um container por sessão
docker run -i --rm --env-file .env -v glpi_audit:/data mcp-glpi-it4

# B) streamable-http — um servidor de longa duração em http://localhost:8000/mcp
docker compose up -d
```

Monte `glpi_audit:/data`: é esse volume que guarda o log de rollback. Guia completo, configuração
dos clientes e notas de segurança: **[docs/pt-BR/DOCKER.md](docs/pt-BR/DOCKER.md)**.

## Início rápido — instalação local

```bash
pip install -e ".[dev]"   # ou: uv sync
cp .env.example .env
mcp-glpi-it4              # stdio
```

## Configuração

| Variável | Obrigatória | Default | Descrição |
|---|---|---|---|
| `GLPI_BASE_URL` | **sim** | — | URL base da sua instância GLPI |
| `GLPI_CLIENT_ID` / `GLPI_CLIENT_SECRET` | **sim** | — | Cliente OAuth (`Setup > OAuth Clients`) |
| `GLPI_USERNAME` / `GLPI_PASSWORD` | **sim** | — | Usuário de serviço |
| `GLPI_API_VERSION` | — | `v2.3` | Versão da API |
| `GLPI_OAUTH_SCOPE` | — | `api` | Escopo OAuth |
| `GLPI_WRITE_MODE` | — | `dry_run` | `dry_run` (simula) \| `live` (executa) |
| `GLPI_AUDIT_DIR` | — | `~/.mcp-glpi-it4` | Onde ficam os logs de rollback/erro (`/data` no Docker) |
| `GLPI_TIMEOUT` / `GLPI_MAX_RETRIES` | — | `15` / `3` | Tuning HTTP |
| `MCP_TRANSPORT` | — | `stdio` | `stdio` \| `streamable-http` \| `sse` |
| `FASTMCP_HOST` / `FASTMCP_PORT` | — | `0.0.0.0` / `8000` | Só nos transportes HTTP (lidos pelo FastMCP) |

## Uso com Claude Desktop

Sem Docker — `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) ou
`%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "glpi-it4": {
      "command": "python",
      "args": ["-m", "mcp_glpi_it4.server"],
      "env": {
        "PYTHONPATH": "/caminho/para/mcp-glpi-it4/src",
        "GLPI_BASE_URL": "https://glpi.example.com",
        "GLPI_CLIENT_ID": "...", "GLPI_CLIENT_SECRET": "...",
        "GLPI_USERNAME": "...", "GLPI_PASSWORD": "...",
        "GLPI_WRITE_MODE": "dry_run"
      }
    }
  }
}
```

Com Docker, veja [docs/pt-BR/DOCKER.md](docs/pt-BR/DOCKER.md). Exemplos de prompts: [docs/pt-BR/USO.md](docs/pt-BR/USO.md).

## Ferramentas (29)

**Chamados:** `glpi_listar_chamados`, `glpi_consultar_chamado`, `glpi_criar_chamado`, `glpi_atualizar_chamado`, `glpi_adicionar_acompanhamento`, `glpi_adicionar_tarefa`, `glpi_adicionar_solucao`, `glpi_atribuir_chamado`, `glpi_excluir_chamado`.

**Inventário:** `glpi_listar_computadores`, `glpi_consultar_ativo`, `glpi_criar_computador`, `glpi_atualizar_computador`, `glpi_excluir_computador`.

**Usuários:** `glpi_listar_usuarios`, `glpi_consultar_usuario`, `glpi_listar_perfis`, `glpi_criar_usuario`, `glpi_excluir_usuario`.

**Configuração:** `glpi_listar_config`, `glpi_consultar_config`, `glpi_atualizar_config`.

**Apoio/Segurança:** `glpi_listar_categorias`, `glpi_listar_entidades`, `glpi_listar_grupos`, `glpi_status_sessao`, `glpi_modo_escrita`, `glpi_reverter`, `glpi_listar_reversiveis`.

## Segurança e reversão

- **`dry_run` (padrão):** toda escrita apenas devolve o payload que *seria* enviado; nada é alterado.
- **`live`:** executa de verdade; cada operação é gravada em `rollback_log.json` com snapshot do
  estado anterior.
- **Reverter:** `glpi_reverter` (uma operação por `audit_id` ou todas as pendentes).
  Ver [docs/pt-BR/REVERSAO.md](docs/pt-BR/REVERSAO.md).

## Documentação

| | Português | English |
|---|---|---|
| Uso | [USO.md](docs/pt-BR/USO.md) | [USAGE.md](docs/en/USAGE.md) |
| Docker | [DOCKER.md](docs/pt-BR/DOCKER.md) | [DOCKER.md](docs/en/DOCKER.md) |
| Reversão | [REVERSAO.md](docs/pt-BR/REVERSAO.md) | [ROLLBACK.md](docs/en/ROLLBACK.md) |
| Desenvolvimento | [DESENVOLVIMENTO.md](docs/pt-BR/DESENVOLVIMENTO.md) | [DEVELOPMENT.md](docs/en/DEVELOPMENT.md) |

Traduções são bem-vindas: crie `docs/<tag-idioma>/` e `README.<tag-idioma>.md` e ligue na linha de
idiomas do topo. Ver [DESENVOLVIMENTO.md](docs/pt-BR/DESENVOLVIMENTO.md#traduções).

## Testes

```bash
pip install -e ".[dev]"
pytest -q
```

## Licença

MIT — ver [LICENSE](LICENSE). Copyright (c) 2026 IT4Solução e contribuidores.

Você pode usar, copiar, modificar, mesclar, publicar, distribuir, sublicenciar e vender cópias deste
software, inclusive comercialmente, desde que o aviso de copyright e o texto da licença sejam
mantidos em todas as cópias. O software é fornecido "como está", sem garantia de qualquer tipo.

O GLPI é um projeto separado, licenciado sob GPL, e não é distribuído aqui.
