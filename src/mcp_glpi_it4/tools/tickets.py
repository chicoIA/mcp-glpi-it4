"""Tools de Chamados (Tickets) — /Assistance/Ticket."""
from __future__ import annotations

from . import build_rsql, compact, guard
from ..glpi import maps
from ..glpi.core import GLPIClient


def register(mcp, client: GLPIClient) -> None:

    @mcp.tool()
    @guard
    async def glpi_listar_chamados(status: int | None = None, tipo: int | None = None,
                                   prioridade: int | None = None, tecnico_id: int | None = None,
                                   limite: int = 20, offset: int = 0) -> dict:
        """Lista chamados do GLPI com filtros opcionais e paginação.
        status: 1=Novo,2=Atribuído,3=Planejado,4=Pendente,5=Solucionado,6=Fechado.
        tipo: 1=Incidente,2=Requisição. prioridade: 1..6."""
        rsql = build_rsql({"status": status, "type": tipo,
                           "priority": prioridade, "users_id_tech": tecnico_id})
        data = await client.list_items("Ticket", rsql=rsql,
                                       start=offset, limit=limite,
                                       sort="id:desc")
        items = data if isinstance(data, list) else data.get("items", data)
        return {"status": "ok", "count": len(items) if isinstance(items, list) else None,
                "items": items}

    @mcp.tool()
    @guard
    async def glpi_consultar_chamado(id: int, incluir_timeline: bool = True) -> dict:
        """Detalha um chamado. Se incluir_timeline, agrega follow-ups, tarefas e solução."""
        ticket = await client.get_item("Ticket", id)
        result = {"status": "ok", "ticket": ticket,
                  "status_label": maps.label(maps.TICKET_STATUS, ticket.get("status"))}
        if incluir_timeline:
            result["timeline"] = await client.get_item("Ticket", id, sub="Timeline")
        return result

    @mcp.tool()
    @guard
    async def glpi_criar_chamado(name: str, content: str, type: int = 1, urgency: int = 3,
                                 itilcategories_id: int | None = None,
                                 entities_id: int | None = None,
                                 requester_id: int | None = None) -> dict:
        """Abre um novo chamado. type: 1=Incidente, 2=Requisição. urgency: 1..5.
        Em modo dry_run, retorna o payload sem criar."""
        payload = compact({
            "name": name, "content": content, "type": type, "urgency": urgency,
            "itilcategories_id": itilcategories_id, "entities_id": entities_id,
            "_users_id_requester": requester_id,
        })
        return await client.create_item("Ticket", payload)

    @mcp.tool()
    @guard
    async def glpi_atualizar_chamado(id: int, name: str | None = None,
                                     content: str | None = None, status: int | None = None,
                                     urgency: int | None = None,
                                     itilcategories_id: int | None = None) -> dict:
        """Atualiza campos de um chamado. Guarda o estado anterior para reversão."""
        payload = compact({"name": name, "content": content, "status": status,
                           "urgency": urgency, "itilcategories_id": itilcategories_id})
        if not payload:
            return {"status": "error", "detail": "Nenhum campo informado para atualização."}
        return await client.update_item("Ticket", id, payload)

    @mcp.tool()
    @guard
    async def glpi_adicionar_acompanhamento(ticket_id: int, content: str,
                                            is_private: bool = False) -> dict:
        """Adiciona um acompanhamento (follow-up) ao chamado."""
        return await client.create_sub("Ticket", ticket_id, maps.TICKET_TIMELINE["followup"],
                                       {"content": content, "is_private": int(is_private)})

    @mcp.tool()
    @guard
    async def glpi_adicionar_tarefa(ticket_id: int, content: str,
                                    actiontime: int | None = None,
                                    state: int | None = None) -> dict:
        """Adiciona uma tarefa ao chamado. actiontime em segundos; state: 1=A fazer,2=Feito."""
        payload = compact({"content": content, "actiontime": actiontime, "state": state})
        return await client.create_sub("Ticket", ticket_id, maps.TICKET_TIMELINE["task"], payload)

    @mcp.tool()
    @guard
    async def glpi_adicionar_solucao(ticket_id: int, content: str,
                                     solutiontypes_id: int | None = None) -> dict:
        """Registra a solução do chamado (pode encerrá-lo conforme a config do GLPI)."""
        payload = compact({"content": content, "solutiontypes_id": solutiontypes_id})
        return await client.create_sub("Ticket", ticket_id, maps.TICKET_TIMELINE["solution"], payload)

    @mcp.tool()
    @guard
    async def glpi_atribuir_chamado(ticket_id: int, role: str = "assign",
                                    users_id: int | None = None,
                                    groups_id: int | None = None) -> dict:
        """Define um ator no chamado. role: requester | observer | assign."""
        if role not in maps.TICKET_ACTOR_ROLES:
            return {"status": "error",
                    "detail": f"role inválido. Use um de: {sorted(maps.TICKET_ACTOR_ROLES)}"}
        payload = compact({"users_id": users_id, "groups_id": groups_id})
        if not payload:
            return {"status": "error", "detail": "Informe users_id ou groups_id."}
        return await client.create_sub("Ticket", ticket_id, f"TeamMember/{role}", payload)

    @mcp.tool()
    @guard
    async def glpi_excluir_chamado(id: int) -> dict:
        """Move o chamado para a lixeira (soft-delete, reversível via glpi_reverter)."""
        return await client.delete_item("Ticket", id, soft=True)
