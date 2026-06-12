"""Tools de Inventário de Computadores — /Assets/Computer."""
from __future__ import annotations

from . import build_rsql, compact, guard
from ..glpi.core import GLPIClient


def register(mcp, client: GLPIClient) -> None:

    @mcp.tool()
    @guard
    async def glpi_listar_computadores(busca: str | None = None, entities_id: int | None = None,
                                       states_id: int | None = None,
                                       limite: int = 20, offset: int = 0) -> dict:
        """Lista computadores do inventário. 'busca' aplica RSQL =like= sobre o nome."""
        equals = build_rsql({"entities_id": entities_id, "states_id": states_id})
        parts = [equals] if equals else []
        if busca:
            parts.append(f"name=like={busca}")
        rsql = ";".join(parts) if parts else None
        data = await client.list_items("Computer", rsql=rsql,
                                       range_=f"{offset}-{offset + limite - 1}", sort="id:desc")
        items = data if isinstance(data, list) else data.get("items", data)
        return {"status": "ok", "count": len(items) if isinstance(items, list) else None,
                "items": items}

    @mcp.tool()
    @guard
    async def glpi_consultar_ativo(id: int, incluir_softwares: bool = False) -> dict:
        """Detalha um computador. Se incluir_softwares, agrega os softwares instalados."""
        comp = await client.get_item("Computer", id)
        result = {"status": "ok", "computer": comp}
        if incluir_softwares:
            result["software"] = await client.get_item("Computer", id, sub="SoftwareInstallation")
        return result

    @mcp.tool()
    @guard
    async def glpi_criar_computador(name: str, serial: str | None = None,
                                    entities_id: int | None = None, states_id: int | None = None,
                                    manufacturers_id: int | None = None,
                                    comment: str | None = None) -> dict:
        """Cadastra um computador no inventário. Em dry_run, retorna o payload sem criar."""
        payload = compact({"name": name, "serial": serial, "entities_id": entities_id,
                           "states_id": states_id, "manufacturers_id": manufacturers_id,
                           "comment": comment})
        return await client.create_item("Computer", payload)

    @mcp.tool()
    @guard
    async def glpi_atualizar_computador(id: int, name: str | None = None,
                                        serial: str | None = None, states_id: int | None = None,
                                        comment: str | None = None) -> dict:
        """Atualiza um computador. Guarda o estado anterior para reversão."""
        payload = compact({"name": name, "serial": serial, "states_id": states_id,
                           "comment": comment})
        if not payload:
            return {"status": "error", "detail": "Nenhum campo informado para atualização."}
        return await client.update_item("Computer", id, payload)

    @mcp.tool()
    @guard
    async def glpi_excluir_computador(id: int) -> dict:
        """Move o computador para a lixeira (soft-delete, reversível via glpi_reverter)."""
        return await client.delete_item("Computer", id, soft=True)
