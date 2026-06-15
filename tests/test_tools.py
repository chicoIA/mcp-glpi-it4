import httpx
import respx

from conftest import API, TOKEN_URL, FakeMCP
from mcp_glpi_it4.config import Settings
from mcp_glpi_it4.tools import tickets, config_tools


def _settings(tmp_path, write_mode):
    return Settings(base_url="https://glpi.test", api_version="v2.3",
                    client_id="c", client_secret="s", username="u", password="p",
                    scope="api", write_mode=write_mode, timeout=5,
                    max_retries=1, audit_dir=str(tmp_path))


@respx.mock
async def test_tool_create_ticket_dry_run(client_factory):
    c = client_factory(write_mode="dry_run")
    mcp = FakeMCP()
    tickets.register(mcp, c)
    res = await mcp.tools["glpi_criar_chamado"](name="Impressora", content="Sem toner")
    assert res["status"] == "dry_run"
    assert res["would_send"]["type"] == 1
    await c.aclose()


@respx.mock
async def test_tool_assign_invalid_role(client_factory):
    c = client_factory(write_mode="live")
    mcp = FakeMCP()
    tickets.register(mcp, c)
    res = await mcp.tools["glpi_atribuir_chamado"](ticket_id=1, role="boss", users_id=2)
    assert res["status"] == "error"
    assert "role" in res["detail"]
    await c.aclose()


@respx.mock
async def test_tool_assign_body_itemtype_e_role_na_colecao(client_factory):
    # HL API v2.3: POST na coleção /TeamMember; role no corpo + {itemtype, items_id}.
    _t = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "abc", "expires_in": 3600}))
    route = respx.post(f"{API}/Assistance/Ticket/9/TeamMember").mock(
        return_value=httpx.Response(201, json={"id": 1}))
    c = client_factory(write_mode="live")
    mcp = FakeMCP()
    tickets.register(mcp, c)
    res = await mcp.tools["glpi_atribuir_chamado"](ticket_id=9, role="requester", users_id=12)
    assert res["status"] == "ok"
    import json as _json
    body = _json.loads(route.calls.last.request.content)
    assert body == {"role": "requester", "itemtype": "User", "items_id": 12}
    await c.aclose()


@respx.mock
async def test_tool_assign_alias_assign_to_assigned(client_factory):
    _t = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "abc", "expires_in": 3600}))
    route = respx.post(f"{API}/Assistance/Ticket/9/TeamMember").mock(
        return_value=httpx.Response(201, json={"id": 2}))
    c = client_factory(write_mode="live")
    mcp = FakeMCP()
    tickets.register(mcp, c)
    res = await mcp.tools["glpi_atribuir_chamado"](ticket_id=9, role="assign", groups_id=5)
    assert res["status"] == "ok" and route.called
    import json as _json
    body = _json.loads(route.calls.last.request.content)
    assert body["role"] == "assigned" and body["itemtype"] == "Group"
    await c.aclose()


@respx.mock
async def test_tool_config_update_blocked(client_factory):
    c = client_factory(write_mode="live")
    mcp = FakeMCP()
    config_tools.register(mcp, c)
    res = await mcp.tools["glpi_atualizar_config"](context="core", name="url_base", value="x")
    assert res["status"] == "error"
    assert res["code"] == 403
    await c.aclose()


@respx.mock
async def test_tool_guard_catches_http_error(client_factory):
    _t = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "abc", "expires_in": 3600}))
    respx.get(f"{API}/Assistance/Ticket/5").mock(return_value=httpx.Response(403, text="denied"))
    c = client_factory(write_mode="live")
    mcp = FakeMCP()
    tickets.register(mcp, c)
    res = await mcp.tools["glpi_consultar_chamado"](id=5)
    assert res["status"] == "error"
    assert res["code"] == 403
    await c.aclose()
