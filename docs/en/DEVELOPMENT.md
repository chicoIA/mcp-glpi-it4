# Development Guide

🌍 [Português](../pt-BR/DESENVOLVIMENTO.md)

## Architecture

```
server.py            FastMCP — builds Settings + GLPIClient and registers the tools
config.py            Settings.from_env() (no hardcoded credentials)
glpi/core.py         async GLPIClient: OAuth2 + refresh, retry, RSQL, dry_run, revert
glpi/audit.py        Auditor: rollback_log.json (snapshots) + error_log.json
glpi/maps.py         RESOURCE_PATHS (resource → v2.3 path) + status tables
tools/__init__.py    guard(), build_rsql(), compact()
tools/{tickets,assets,users,config_tools,support}.py   register(mcp, client)
```

Flow of a write tool:
`tool → GLPIClient.create_item/update_item/delete_item → (dry_run? return the plan) → request() → Auditor.record_*`

## Conventions

- Tool name: `glpi_<verb>_<resource>` in Portuguese (e.g. `glpi_criar_chamado`) — stable public surface, do not rename.
- Every tool is `async`, decorated with `@mcp.tool()` and `@guard` (turns `GLPIError` into a clean response).
- Optional fields: `tipo | None = None` + `compact()` to build partial payloads.
- List filters: `build_rsql({field: value})` (AND via `;`).

## Adding a resource (e.g. Printers)

1. **Confirm the path** in your instance's Swagger:
   ```bash
   curl -s -H "Accept: application/json" \
     "$GLPI_BASE_URL/api.php/doc.json" | jq '.paths | keys' | grep -i printer
   ```
2. **Register the path** in `glpi/maps.py` → `RESOURCE_PATHS["Printer"] = "Assets/Printer"`.
3. **Write the tools** in `tools/printers.py` with `register(mcp, client)`, reusing
   `client.list_items / get_item / create_item / update_item / delete_item`.
4. **Register the module** in `server.py`.
5. **Test** with respx (see `tests/`).

## Confirming the update verb (PATCH vs PUT)

v2.3 is assumed to use `PATCH` (`glpi/core.py: UPDATE_METHOD`). To confirm:
```bash
curl -s "$GLPI_BASE_URL/api.php/doc.json" | jq '.paths["/Assistance/Ticket/{id}"] | keys'
```
If your instance exposes `put` instead of `patch`, set `UPDATE_METHOD = "PUT"`.

## Tests

```bash
pip install -e ".[dev]"
pytest -q
```
Tests mock HTTP with `respx` (they never touch a real instance). They cover: auth, re-auth on 401,
retry on 5xx, dry_run, auditing, rollback, error mapping and blocking of sensitive config.

> Note: in environments with a SOCKS proxy in `env`, the tests build `httpx.AsyncClient(trust_env=False)`.

## Translations

Docs live in `docs/en/` and `docs/pt-BR/`, plus `README.md` (EN) and `README.pt-BR.md`.
A new language is a new `docs/<tag>/` folder and a `README.<tag>.md`, linked from the language
row at the top of each README. Code, tool names and code comments stay as they are.

## Roadmap

- Problems/Changes (`Assistance/Problem`, `Assistance/Change`) — paths already exist in v2.3.
- Knowledge base and statistics.
- `refresh_token` support (Authorization Code grant) alongside the Password grant.
- Published image on a public registry (GHCR) via CI.
