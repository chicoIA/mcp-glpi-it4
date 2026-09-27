"""Settings.from_env() e a escolha de transporte (usado pelo Docker)."""
import pytest

from mcp_glpi_it4 import server
from mcp_glpi_it4.config import Settings

BASE = {
    "GLPI_BASE_URL": "https://glpi.test/",
    "GLPI_CLIENT_ID": "cid", "GLPI_CLIENT_SECRET": "sec",
    "GLPI_USERNAME": "u", "GLPI_PASSWORD": "p",
}


def _env(monkeypatch, **extra):
    for k in list(BASE) + ["GLPI_WRITE_MODE", "MCP_TRANSPORT", "GLPI_AUDIT_DIR",
                           "FASTMCP_HOST", "FASTMCP_PORT"]:
        monkeypatch.delenv(k, raising=False)
    for k, v in {**BASE, **extra}.items():
        monkeypatch.setenv(k, v)


def test_from_env_strips_trailing_slash(monkeypatch):
    _env(monkeypatch)
    s = Settings.from_env()
    assert s.base_url == "https://glpi.test"
    assert s.api_url == "https://glpi.test/api.php/v2.3"
    assert s.dry_run is True          # padrão seguro


def test_base_url_is_required(monkeypatch):
    _env(monkeypatch)
    monkeypatch.delenv("GLPI_BASE_URL")
    with pytest.raises(RuntimeError, match="GLPI_BASE_URL"):
        Settings.from_env()


@pytest.mark.parametrize("env, expected", [(None, "stdio"),
                                           ("streamable-http", "streamable-http")])
def test_main_uses_mcp_transport(monkeypatch, env, expected):
    _env(monkeypatch)
    if env:
        monkeypatch.setenv("MCP_TRANSPORT", env)
    used = {}
    monkeypatch.setattr(server, "build_server",
                        lambda: type("M", (), {"run": lambda _s, transport: used.update(t=transport)})())
    server.main()
    assert used["t"] == expected


def test_http_bind_comes_from_env(monkeypatch):
    """Sem isto o container escuta em 127.0.0.1 e o -p do Docker não alcança nada."""
    _env(monkeypatch)
    monkeypatch.setenv("FASTMCP_HOST", "0.0.0.0")
    monkeypatch.setenv("FASTMCP_PORT", "9001")
    mcp = server.build_server()
    assert (mcp.settings.host, mcp.settings.port) == ("0.0.0.0", 9001)
