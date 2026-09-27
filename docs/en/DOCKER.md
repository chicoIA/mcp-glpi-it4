# Running in Docker

🌍 [Português](../pt-BR/DOCKER.md)

Two ways to run, same image.

| | `stdio` | `streamable-http` |
|---|---|---|
| Who starts it | the MCP client, one container per session | you (`docker compose up -d`), long-running |
| Good for | Claude Desktop / Claude Code on one machine | several apps/clients, remote hosts, mixed stacks |
| Endpoint | stdin/stdout | `http://localhost:8000/mcp` |

## Build

```bash
cp .env.example .env     # fill in GLPI_BASE_URL + OAuth credentials
docker build -t mcp-glpi-it4 .
```

## A. stdio — one container per client session

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
               "--env-file", "/absolute/path/to/.env",
               "-v", "glpi_audit:/data",
               "mcp-glpi-it4"]
    }
  }
}
```

`-i` is mandatory (stdin stays open). `--env-file` takes an absolute path.

## B. streamable-http — one server, many clients

```bash
docker compose up -d
docker compose logs -f
```

The server listens on `http://127.0.0.1:8000/mcp`. Point any MCP client that speaks
streamable HTTP at that URL — e.g. in Claude Code:

```bash
claude mcp add --transport http glpi http://localhost:8000/mcp
```

To run it without compose:

```bash
docker run -d --name mcp-glpi --env-file .env \
  -e MCP_TRANSPORT=streamable-http \
  -p 127.0.0.1:8000:8000 -v glpi_audit:/data mcp-glpi-it4
```

## The /data volume is not optional

The image sets `GLPI_AUDIT_DIR=/data`. That is where `rollback_log.json` and `error_log.json`
live — the record that makes every `live` write revertible. **Without a volume mounted there,
the log is destroyed with the container and writes become unrevertible.** Both recipes above
mount `glpi_audit:/data`; keep it.

Inspect it:

```bash
docker run --rm -v glpi_audit:/data alpine cat /data/rollback_log.json
```

## Security notes

- The compose file binds to `127.0.0.1` on purpose. The HTTP transport has **no authentication
  of its own** — anyone who reaches the port can drive your GLPI with the container's credentials.
  To expose it beyond localhost, put a reverse proxy with TLS and auth in front of it.
- `.env` holds an OAuth secret and a service-account password. It is in `.gitignore` and
  `.dockerignore`; keep it out of the image and out of image layers.
- The container runs as an unprivileged user (uid 10001).
- `GLPI_WRITE_MODE=dry_run` is the image default. Set `live` in `.env` only when you mean it.

## Rollback of the deployment itself

| To undo | Command |
|---|---|
| Stop the HTTP server | `docker compose down` (the volume survives) |
| Remove container + image | `docker compose down --rmi local` |
| Discard the audit log too | `docker volume rm glpi_audit` — **irreversible**, do this only after verifying there is nothing pending in `glpi_listar_reversiveis` |
| Go back to running without Docker | `pip install -e .` and `mcp-glpi-it4`; nothing in the code is Docker-specific |
