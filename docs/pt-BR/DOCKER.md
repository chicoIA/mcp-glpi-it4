# Rodando em Docker

🌍 [English](../en/DOCKER.md)

Duas formas de rodar, a mesma imagem.

| | `stdio` | `streamable-http` |
|---|---|---|
| Quem sobe | o cliente MCP, um container por sessão | você (`docker compose up -d`), longa duração |
| Bom para | Claude Desktop / Claude Code numa máquina | vários apps/clientes, hosts remotos, stacks mistas |
| Endpoint | stdin/stdout | `http://localhost:8000/mcp` |

## Build

```bash
cp .env.example .env     # preencha GLPI_BASE_URL + credenciais OAuth
docker build -t mcp-glpi-it4 .
```

## A. stdio — um container por sessão do cliente

```bash
docker run -i --rm --env-file .env -v glpi_audit:/data mcp-glpi-it4
```

`claude_desktop_config.json` (macOS: `~/Library/Application Support/Claude/`,
Windows: `%APPDATA%\Claude\`):

```json
{
  "mcpServers": {
    "glpi": {
      "command": "docker",
      "args": ["run", "-i", "--rm",
               "--env-file", "/caminho/absoluto/para/.env",
               "-v", "glpi_audit:/data",
               "mcp-glpi-it4"]
    }
  }
}
```

O `-i` é obrigatório (mantém o stdin aberto). `--env-file` exige caminho absoluto.

## B. streamable-http — um servidor, vários clientes

```bash
docker compose up -d
docker compose logs -f
```

O servidor escuta em `http://127.0.0.1:8000/mcp`. Aponte qualquer cliente MCP que fale
streamable HTTP para essa URL — no Claude Code, por exemplo:

```bash
claude mcp add --transport http glpi http://localhost:8000/mcp
```

Sem compose:

```bash
docker run -d --name mcp-glpi --env-file .env \
  -e MCP_TRANSPORT=streamable-http \
  -p 127.0.0.1:8000:8000 -v glpi_audit:/data mcp-glpi-it4
```

## O volume /data não é opcional

A imagem define `GLPI_AUDIT_DIR=/data`. É ali que ficam `rollback_log.json` e `error_log.json` —
o registro que torna reversível toda escrita em `live`. **Sem um volume montado, o log morre
junto com o container e as escritas ficam irreversíveis.** As duas receitas acima montam
`glpi_audit:/data`; mantenha.

Para inspecionar:

```bash
docker run --rm -v glpi_audit:/data alpine cat /data/rollback_log.json
```

## Segurança

- O compose publica em `127.0.0.1` de propósito. O transporte HTTP **não tem autenticação
  própria** — quem alcança a porta opera o seu GLPI com as credenciais do container. Para expor
  além do localhost, coloque um proxy reverso com TLS e autenticação na frente.
- O `.env` guarda o segredo OAuth e a senha do usuário de serviço. Está no `.gitignore` e no
  `.dockerignore`; não deixe entrar na imagem nem nas camadas.
- O container roda com usuário sem privilégio (uid 10001).
- `GLPI_WRITE_MODE=dry_run` é o padrão da imagem. Só mude para `live` conscientemente.

## Reversão do próprio deploy

| Para desfazer | Comando |
|---|---|
| Parar o servidor HTTP | `docker compose down` (o volume sobrevive) |
| Remover container + imagem | `docker compose down --rmi local` |
| Descartar também o log de auditoria | `docker volume rm glpi_audit` — **irreversível**, só depois de conferir que não há nada pendente em `glpi_listar_reversiveis` |
| Voltar a rodar sem Docker | `pip install -e .` e `mcp-glpi-it4`; nada no código é específico de Docker |
