# mcp-glpi-it4 — MCP Server for GLPI (High-level API v2.3 / OAuth2)
# stdio:  docker run -i --rm --env-file .env -v glpi_audit:/data ghcr.io/chicoia/mcp-glpi-it4
# http:   docker compose up -d      (streamable-http on :8000/mcp)
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    # Logs de rollback/erro fora do container: monte um volume em /data.
    GLPI_AUDIT_DIR=/data \
    # dry_run por padrão — nenhuma escrita real sem opt-in explícito.
    GLPI_WRITE_MODE=dry_run \
    MCP_TRANSPORT=stdio \
    FASTMCP_HOST=0.0.0.0 \
    FASTMCP_PORT=8000

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . \
 && useradd --uid 10001 --create-home app \
 && install -d -o app -g app /data

USER app
VOLUME ["/data"]
EXPOSE 8000
ENTRYPOINT ["mcp-glpi-it4"]
