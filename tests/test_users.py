import httpx
import respx

from conftest import API, TOKEN_URL, FakeMCP
from mcp_glpi_it4.tools import users


def _token():
    return respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "abc", "expires_in": 3600}))


# ── criação em dry_run não escreve e inclui o perfil de cliente por padrão ─────
@respx.mock
async def test_criar_usuario_dry_run_default_perfil_cliente(client_factory):
    c = client_factory(write_mode="dry_run")
    mcp = FakeMCP()
    users.register(mcp, c)
    res = await mcp.tools["glpi_criar_usuario"](
        name="rwoiciechowski", firstname="Ricardo", realname="Woiciechowski")
    assert res["status"] == "dry_run"
    sent = res["would_send"]
    assert sent["username"] == "rwoiciechowski"   # HL API v2.3: login = username
    assert sent["default_profile"] == 1           # Self-Service = cliente (default)
    assert sent["default_entity"] == 0
    assert sent["is_active"] is True
    assert c.audit.load() == []                   # nada registrado em dry_run
    await c.aclose()


# ── senha e email só entram no payload quando informados ──────────────────────
@respx.mock
async def test_criar_usuario_payload_opcionais(client_factory):
    c = client_factory(write_mode="dry_run")
    mcp = FakeMCP()
    users.register(mcp, c)
    res = await mcp.tools["glpi_criar_usuario"](
        name="ricardo", password="S3nh@", email="ricardo@motatelecom.com.br",
        profiles_id=1, entities_id=1)
    sent = res["would_send"]
    assert sent["password"] == "S3nh@" and sent["password2"] == "S3nh@"
    assert sent["emails"] == ["ricardo@motatelecom.com.br"]
    assert sent["default_entity"] == 1
    # sem firstname/realname → não devem aparecer
    assert "firstname" not in sent and "realname" not in sent
    await c.aclose()


# ── name vazio é rejeitado com erro claro ─────────────────────────────────────
async def test_criar_usuario_sem_name(client_factory):
    c = client_factory(write_mode="live")
    mcp = FakeMCP()
    users.register(mcp, c)
    res = await mcp.tools["glpi_criar_usuario"](name="   ")
    assert res["status"] == "error"
    assert "login" in res["detail"].lower()
    await c.aclose()


# ── criação live + auditoria + reversão (delete) ──────────────────────────────
@respx.mock
async def test_criar_usuario_live_e_revert(client_factory):
    _token()
    respx.post(f"{API}/Administration/User").mock(
        return_value=httpx.Response(201, json={"id": 77}))
    delete = respx.delete(f"{API}/Administration/User/77").mock(
        return_value=httpx.Response(204))
    c = client_factory(write_mode="live")
    mcp = FakeMCP()
    users.register(mcp, c)

    res = await mcp.tools["glpi_criar_usuario"](name="ricardo.woiciechowski")
    assert res["status"] == "ok" and res["id"] == 77
    assert len(c.audit.pending()) == 1

    rev = await c.revert()
    assert rev["reverted"] == 1
    assert delete.called
    assert c.audit.pending() == []
    await c.aclose()


# ── soft-delete do usuário é reversível ───────────────────────────────────────
@respx.mock
async def test_excluir_usuario_soft_delete(client_factory):
    _token()
    patch = respx.patch(f"{API}/Administration/User/77").mock(
        return_value=httpx.Response(200, json={"id": 77, "is_deleted": 1}))
    c = client_factory(write_mode="live")
    mcp = FakeMCP()
    users.register(mcp, c)

    res = await mcp.tools["glpi_excluir_usuario"](id=77)
    assert res["status"] == "ok" and res["soft"] is True
    assert patch.called
    assert c.audit.pending()[0]["op"] == "delete"
    await c.aclose()


# ── listagem aplica RSQL de busca e devolve itens ─────────────────────────────
@respx.mock
async def test_listar_usuarios_busca(client_factory):
    _token()
    route = respx.get(f"{API}/Administration/User").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "ricardo"}]))
    c = client_factory(write_mode="live")
    mcp = FakeMCP()
    users.register(mcp, c)

    res = await mcp.tools["glpi_listar_usuarios"](busca="ricardo", is_active=1)
    assert res["status"] == "ok" and res["count"] == 1
    q = dict(route.calls.last.request.url.params)
    assert "is_active==1" in q["filter"] and "name=like=ricardo" in q["filter"]
    await c.aclose()


# ── listagem de perfis usa o path Administration/Profile ──────────────────────
@respx.mock
async def test_listar_perfis(client_factory):
    _token()
    route = respx.get(f"{API}/Administration/Profile").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "Self-Service"}]))
    c = client_factory(write_mode="live")
    mcp = FakeMCP()
    users.register(mcp, c)

    res = await mcp.tools["glpi_listar_perfis"]()
    assert res["status"] == "ok"
    assert route.called
    await c.aclose()
