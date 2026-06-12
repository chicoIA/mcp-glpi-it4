# mcp-glpi-it4

MCP Server para integração com o **GLPI** da IT4Solução via **High-level API v2.3 (OAuth2)**.
Expõe chamados, inventário de computadores e configuração de parâmetros como ferramentas (tools) para assistentes como o Claude.

- **Instância:** `https://suporte.sys.it4solucao.com.br`
- **API:** `api.php/v2.3` · **Auth:** OAuth2 Password Grant
- **Stack:** Python 3.12 · FastMCP · httpx (async)
- **Segurança:** `dry_run` por padrão + reversão de toda escrita

> Decisões de design e a análise "reusar vs. construir" estão no [SDD](../SDD_MCP_GLPI_IT4Solucao.md).

## Por que um servidor novo (e não os MCPs públicos)

Os MCPs avaliados (`GMS64260/mcp-glpi`, `svtica/glpi-mcp`) autenticam pela **API legacy** (Session-Token), incompatível com a v2.3/OAuth2 desta instância, e não cobrem configuração de parâmetros. Este projeto reaproveita o cliente OAuth2 e o mecanismo de rollback já validados em `scripts_glpi/`.

## Instalação

```bash
cd mcp-glpi-it4
uv sync            # ou: pip install -e ".[dev]"
cp .env.example .env   # preencha as credenciais
```

## Configuração (variáveis de ambiente)

| Variável | Obrigatória | Default | Descrição |
|---|---|---|---|
| `GLPI_BASE_URL` | — | `https://suporte.sys.it4solucao.com.br` | URL base |
| `GLPI_API_VERSION` | — | `v2.3` | Versão da API |
| `GLPI_CLIENT_ID` / `GLPI_CLIENT_SECRET` | **sim** | — | Cliente OAuth (`Setup > OAuth Clients`) |
| `GLPI_USERNAME` / `GLPI_PASSWORD` | **sim** | — | Usuário de serviço |
| `GLPI_OAUTH_SCOPE` | — | `api` | Escopo OAuth |
| `GLPI_WRITE_MODE` | — | `dry_run` | `dry_run` (simula) \| `live` (executa) |
| `GLPI_TIMEOUT` / `GLPI_MAX_RETRIES` | — | `15` / `3` | Tuning HTTP |

Como obter Client ID/Secret: `Setup > OAuth Clients` no GLPI (ver `../scripts_glpi/COMO_OBTER_CREDENCIAIS_OAUTH.md`).

## Uso com Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) ou `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "glpi-it4": {
      "command": "python",
      "args": ["-m", "mcp_glpi_it4.server"],
      "env": {
        "PYTHONPATH": "/caminho/para/mcp-glpi-it4/src",
        "GLPI_CLIENT_ID": "...", "GLPI_CLIENT_SECRET": "...",
        "GLPI_USERNAME": "...", "GLPI_PASSWORD": "...",
        "GLPI_WRITE_MODE": "dry_run"
      }
    }
  }
}
```

Detalhes e exemplos de prompts: [docs/USO.md](docs/USO.md).

## Ferramentas (24)

**Chamados:** `glpi_listar_chamados`, `glpi_consultar_chamado`, `glpi_criar_chamado`, `glpi_atualizar_chamado`, `glpi_adicionar_acompanhamento`, `glpi_adicionar_tarefa`, `glpi_adicionar_solucao`, `glpi_atribuir_chamado`, `glpi_excluir_chamado`.

**Inventário:** `glpi_listar_computadores`, `glpi_consultar_ativo`, `glpi_criar_computador`, `glpi_atualizar_computador`, `glpi_excluir_computador`.

**Configuração:** `glpi_listar_config`, `glpi_consultar_config`, `glpi_atualizar_config`.

**Apoio/Segurança:** `glpi_listar_categorias`, `glpi_listar_entidades`, `glpi_listar_grupos`, `glpi_status_sessao`, `glpi_modo_escrita`, `glpi_reverter`, `glpi_listar_reversiveis`.

## Segurança e reversão

- **`dry_run` (padrão):** toda escrita apenas devolve o payload que *seria* enviado; nada é alterado.
- **`live`:** executa de verdade; cada operação é gravada em `rollback_log.json` com snapshot do estado anterior.
- **Reverter:** `glpi_reverter` (uma operação por `audit_id` ou todas pendentes). Ver [docs/REVERSAO.md](docs/REVERSAO.md).

## Testes

```bash
pip install -e ".[dev]"
pytest -q
```

## Desenvolvimento futuro

Como adicionar recursos/tools e confirmar endpoints: [docs/DESENVOLVIMENTO.md](docs/DESENVOLVIMENTO.md).

## Licença

MIT.
