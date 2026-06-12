# Guia de Desenvolvimento

## Arquitetura

```
server.py            FastMCP — instancia Settings + GLPIClient e registra as tools
config.py            Settings.from_env() (sem credenciais hardcoded)
glpi/core.py         GLPIClient async: OAuth2 + refresh, retry, RSQL, dry_run, revert
glpi/audit.py        Auditor: rollback_log.json (snapshots) + error_log.json
glpi/maps.py         RESOURCE_PATHS (recurso → path v2.3) + tabelas de status
tools/__init__.py    guard(), build_rsql(), compact()
tools/{tickets,assets,config_tools,support}.py   register(mcp, client)
```

Fluxo de uma tool de escrita:
`tool → GLPIClient.create_item/update_item/delete_item → (dry_run? retorna plano) → request() → Auditor.record_*`

## Convenções

- Nome de tool: `glpi_<verbo>_<recurso>` (ex.: `glpi_criar_chamado`).
- Toda tool é `async`, decorada com `@mcp.tool()` e `@guard` (captura `GLPIError` → resposta limpa).
- Campos opcionais: `tipo | None = None` + `compact()` para montar payload parcial.
- Filtros de lista: `build_rsql({campo: valor})` (AND via `;`).

## Adicionar um novo recurso (ex.: Impressoras)

1. **Confirme o path** no Swagger da instância:
   ```bash
   curl -s -H "Accept: application/json" \
     "https://suporte.sys.it4solucao.com.br/api.php/doc.json" | jq '.paths | keys' | grep -i printer
   ```
   (ou reutilize `../scripts_glpi/dump_swagger_paths.py`).
2. **Registre o path** em `glpi/maps.py` → `RESOURCE_PATHS["Printer"] = "Assets/Printer"`.
3. **Crie as tools** num módulo `tools/printers.py` com `register(mcp, client)`, reusando
   `client.list_items / get_item / create_item / update_item / delete_item`.
4. **Registre o módulo** em `server.py`.
5. **Teste** com respx (ver `tests/`).

## Confirmar o verbo de atualização (PATCH vs PUT)

A v2.3 usa `PATCH` por hipótese (`glpi/core.py: UPDATE_METHOD`). Para confirmar:
```bash
curl -s "https://suporte.sys.it4solucao.com.br/api.php/doc.json" \
  | jq '.paths["/Assistance/Ticket/{id}"] | keys'
```
Se a instância expuser `put` em vez de `patch`, ajuste `UPDATE_METHOD = "PUT"`.

## Testes

```bash
pip install -e ".[dev]"
pytest -q
```
Os testes mockam o HTTP com `respx` (não tocam a instância real). Cobrem: auth, re-auth em 401,
retry em 5xx, dry_run, auditoria, reversão, mapeamento de erro e bloqueio de config sensível.

> Nota: em ambientes com proxy SOCKS no `env`, os testes instanciam `httpx.AsyncClient(trust_env=False)`.

## Roadmap sugerido

- Problemas/Mudanças (`Assistance/Problem`, `Assistance/Change`) — paths já existem na v2.3.
- Base de Conhecimento e estatísticas.
- Suporte a `refresh_token` (grant Authorization Code) além do Password Grant.
- Transporte HTTP/SSE além de stdio.
