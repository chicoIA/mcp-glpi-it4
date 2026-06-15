import httpx
import pytest
import respx

from conftest import API, TOKEN_URL
from mcp_glpi_it4.glpi.core import GLPIError
from mcp_glpi_it4.tools import build_rsql, compact


def _token(times=10):
    return respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "abc", "expires_in": 3600}))


# ── helpers puros ─────────────────────────────────────────────────────────────
def test_build_rsql():
    assert build_rsql({"status": 1, "type": None}) == "status==1"
    assert build_rsql({"a": 1, "b": 2}) == "a==1;b==2"
    assert build_rsql({"x": None}) is None


def test_compact():
    assert compact({"a": 1, "b": None, "c": 0}) == {"a": 1, "c": 0}


# ── autenticação ──────────────────────────────────────────────────────────────
@respx.mock
async def test_authenticate(client_factory):
    _token()
    c = client_factory()
    await c.authenticate()
    assert c._token == "abc"
    await c.aclose()


@respx.mock
async def test_auth_failure_raises(client_factory):
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(400, json={"error": "invalid_client"}))
    c = client_factory()
    with pytest.raises(GLPIError) as e:
        await c.authenticate()
    assert e.value.status == 400
    await c.aclose()


# ── dry_run não escreve nada ──────────────────────────────────────────────────
@respx.mock
async def test_create_dry_run_no_write(client_factory):
    c = client_factory(write_mode="dry_run")
    res = await c.create_item("Ticket", {"name": "x", "content": "y"})
    assert res["status"] == "dry_run"
    assert res["would_send"]["name"] == "x"
    assert c.audit.load() == []        # nada registrado
    await c.aclose()


# ── create live + auditoria + revert ──────────────────────────────────────────
@respx.mock
async def test_create_live_and_revert(client_factory):
    _token()
    respx.post(f"{API}/Assistance/Ticket").mock(return_value=httpx.Response(201, json={"id": 42}))
    delete = respx.delete(f"{API}/Assistance/Ticket/42").mock(return_value=httpx.Response(204))
    c = client_factory(write_mode="live")

    res = await c.create_item("Ticket", {"name": "x", "content": "y"})
    assert res["id"] == 42
    assert len(c.audit.pending()) == 1

    rev = await c.revert()
    assert rev["reverted"] == 1
    assert delete.called
    assert c.audit.pending() == []     # marcado como revertido
    await c.aclose()


# ── update captura estado anterior ────────────────────────────────────────────
@respx.mock
async def test_update_captures_before(client_factory):
    _token()
    respx.get(f"{API}/Assistance/Ticket/7").mock(
        return_value=httpx.Response(200, json={"id": 7, "name": "old", "status": 1}))
    respx.patch(f"{API}/Assistance/Ticket/7").mock(return_value=httpx.Response(200, json={"id": 7}))
    c = client_factory(write_mode="live")

    res = await c.update_item("Ticket", 7, {"name": "new"})
    assert res["before"] == {"name": "old"}
    entry = c.audit.pending()[0]
    assert entry["op"] == "update"
    assert entry["before"] == {"name": "old"}
    await c.aclose()


# ── retry em 5xx para GET ─────────────────────────────────────────────────────
@respx.mock
async def test_retry_on_500_get(client_factory):
    _token()
    route = respx.get(f"{API}/Assets/Computer").mock(side_effect=[
        httpx.Response(500), httpx.Response(200, json=[]),
    ])
    c = client_factory(write_mode="live", max_retries=2)
    data = await c.list_items("Computer")
    assert data == []
    assert route.call_count == 2
    await c.aclose()


# ── 401 dispara re-autenticação e repete uma vez ──────────────────────────────
@respx.mock
async def test_401_triggers_reauth(client_factory):
    _token()
    route = respx.get(f"{API}/Assistance/Ticket/1").mock(side_effect=[
        httpx.Response(401), httpx.Response(200, json={"id": 1}),
    ])
    c = client_factory(write_mode="live")
    data = await c.get_item("Ticket", 1)
    assert data == {"id": 1}
    assert route.call_count == 2
    await c.aclose()


# ── erro 404 é mapeado com hint ───────────────────────────────────────────────
@respx.mock
async def test_get_sem_content_type_nem_corpo(client_factory):
    # Regressão: GET não pode levar Content-Type nem body (GLPI v2.3 → 400 Invalid JSON body).
    _token()
    route = respx.get(f"{API}/Administration/Entity").mock(
        return_value=httpx.Response(200, json=[]))
    c = client_factory(write_mode="live")
    await c.list_items("Entity")
    req = route.calls.last.request
    assert "content-type" not in {k.lower() for k in req.headers}
    assert req.content in (b"", None)
    await c.aclose()


@respx.mock
async def test_paginacao_usa_start_e_limit(client_factory):
    # Regressão: a HL API v2 pagina por 'start'/'limit' (não 'range').
    _token()
    route = respx.get(f"{API}/Dropdowns/ITILCategory").mock(
        return_value=httpx.Response(200, json=[]))
    c = client_factory(write_mode="live")
    await c.list_items("ITILCategory", start=0, limit=5)
    q = dict(route.calls.last.request.url.params)
    assert q.get("limit") == "5"
    assert q.get("start") == "0"
    assert "range" not in q
    await c.aclose()


@respx.mock
async def test_post_inclui_content_type(client_factory):
    _token()
    route = respx.post(f"{API}/Assistance/Ticket").mock(
        return_value=httpx.Response(201, json={"id": 1}))
    c = client_factory(write_mode="live")
    await c.create_item("Ticket", {"name": "x"})
    req = route.calls.last.request
    assert req.headers.get("content-type", "").startswith("application/json")
    await c.aclose()


@respx.mock
async def test_404_maps_hint(client_factory):
    _token()
    respx.get(f"{API}/Assistance/Ticket/999").mock(return_value=httpx.Response(404, text="not found"))
    c = client_factory(write_mode="live")
    with pytest.raises(GLPIError) as e:
        await c.get_item("Ticket", 999)
    assert e.value.status == 404
    assert "path" in e.value.hint.lower() or "inexistente" in e.value.hint.lower()
    await c.aclose()
