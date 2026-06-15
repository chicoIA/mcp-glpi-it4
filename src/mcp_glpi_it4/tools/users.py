"""Tools de Administração de Usuários — /Administration/User.

Cria, lista, consulta e remove usuários reutilizando a MESMA autenticação OAuth2
do servidor (nenhum App-Token/User-Token é pedido aqui: as credenciais já vêm das
variáveis de ambiente GLPI_*). Toda escrita é auditada e reversível via glpi_reverter.

Vínculo de perfil: a HL API v2.3 não expõe um endpoint Profile_User separado, então
o perfil/entidade são enviados como campos especiais do GLPI (`_profiles_id`,
`_entities_id`, `_is_recursive`) no próprio POST de criação do usuário — mecanismo
que o GLPI usa para criar o Profile_User automaticamente em User::post_addItem().
"""
from __future__ import annotations

from . import build_rsql, guard
from ..glpi.core import GLPIClient

# Perfis padrão do GLPI (referência — confirme em Administração > Perfis ou via
# glpi_listar_perfis, pois os IDs podem variar por instância):
#   1=Self-Service (CLIENTE) · 2=Observer · 3=Admin · 4=Super-Admin
#   5=Hotliner · 6=Technician · 7=Supervisor · 8=Read-Only
PERFIL_CLIENTE_PADRAO = 1


def register(mcp, client: GLPIClient) -> None:

    @mcp.tool()
    @guard
    async def glpi_listar_usuarios(busca: str | None = None, entities_id: int | None = None,
                                   is_active: int | None = None,
                                   limite: int = 20, offset: int = 0) -> dict:
        """Lista usuários do GLPI. 'busca' aplica RSQL =like= sobre o login (name).
        is_active: 1=ativos, 0=inativos."""
        equals = build_rsql({"entities_id": entities_id, "is_active": is_active})
        parts = [equals] if equals else []
        if busca:
            parts.append(f"name=like={busca}")
        rsql = ";".join(parts) if parts else None
        data = await client.list_items("User", rsql=rsql,
                                       start=offset, limit=limite, sort="id:desc")
        items = data if isinstance(data, list) else data.get("items", data)
        return {"status": "ok", "count": len(items) if isinstance(items, list) else None,
                "items": items}

    @mcp.tool()
    @guard
    async def glpi_consultar_usuario(id: int) -> dict:
        """Detalha um usuário pelo ID."""
        return {"status": "ok", "user": await client.get_item("User", id)}

    @mcp.tool()
    @guard
    async def glpi_listar_perfis(limite: int = 50) -> dict:
        """Lista os perfis disponíveis (para confirmar o ID do perfil 'cliente')."""
        data = await client.list_items("Profile", start=0, limit=limite)
        return {"status": "ok", "items": data}

    @mcp.tool()
    @guard
    async def glpi_criar_usuario(name: str, firstname: str | None = None,
                                 realname: str | None = None, password: str | None = None,
                                 email: str | None = None,
                                 profiles_id: int | None = PERFIL_CLIENTE_PADRAO,
                                 entities_id: int | None = 0,
                                 is_active: bool = True,
                                 extra: dict | None = None) -> dict:
        """Cria um usuário no GLPI definindo perfil/entidade padrão (1=Self-Service/cliente).

        IMPORTANTE: na HL API v2.3 o campo de login é 'username' (mapeado a partir de
        'name' aqui) e perfil/entidade vão em 'default_profile'/'default_entity'.
        'name' é o login de acesso. Se 'password' for omitido, o usuário é criado sem
        senha (defina depois). 'email' é opcional. 'entities_id' 0=Root, 1=NorthIT.
        'extra' permite sobrescrever/adicionar campos crus do payload (ajuste de schema).
        Reversível: a criação é auditada e pode ser desfeita com glpi_reverter.
        Em dry_run, retorna o payload sem criar nada.
        """
        if not name or not str(name).strip():
            return {"status": "error", "detail": "Informe 'name' (login) do usuário."}

        payload: dict = {
            "username": name,          # HL API v2.3: o login fica em 'username'
            "is_active": bool(is_active),
        }
        if firstname is not None:
            payload["firstname"] = firstname
        if realname is not None:
            payload["realname"] = realname
        if password:
            payload["password"] = password
            payload["password2"] = password
        if email:
            payload["emails"] = [email]
        if profiles_id is not None:
            payload["default_profile"] = profiles_id   # perfil padrão (cliente=1)
        if entities_id is not None:
            payload["default_entity"] = entities_id
        if extra:
            payload.update(extra)

        return await client.create_item("User", payload, name_key="username")

    @mcp.tool()
    @guard
    async def glpi_excluir_usuario(id: int) -> dict:
        """Move o usuário para a lixeira (soft-delete, reversível via glpi_reverter)."""
        return await client.delete_item("User", id, soft=True)
