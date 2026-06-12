import httpx
import pytest

from mcp_glpi_it4.config import Settings
from mcp_glpi_it4.glpi.audit import Auditor
from mcp_glpi_it4.glpi.core import GLPIClient

TOKEN_URL = "https://glpi.test/api.php/token"
API = "https://glpi.test/api.php/v2.3"


def make_settings(tmp_path, write_mode="live", max_retries=2):
    return Settings(
        base_url="https://glpi.test", api_version="v2.3",
        client_id="cid", client_secret="sec", username="u", password="p",
        scope="api", write_mode=write_mode, timeout=5,
        max_retries=max_retries, audit_dir=str(tmp_path),
    )


@pytest.fixture
def client_factory(tmp_path):
    created = []

    def _make(write_mode="live", max_retries=2):
        # trust_env=False evita o proxy SOCKS injetado no ambiente de teste.
        http = httpx.AsyncClient(timeout=5, trust_env=False)
        c = GLPIClient(make_settings(tmp_path, write_mode, max_retries),
                       auditor=Auditor(str(tmp_path)), http=http)
        created.append(c)
        return c

    yield _make


class FakeMCP:
    """Captura as tools registradas para invocá-las nos testes."""
    def __init__(self):
        self.tools = {}

    def tool(self):
        def deco(fn):
            self.tools[fn.__name__] = fn
            return fn
        return deco
