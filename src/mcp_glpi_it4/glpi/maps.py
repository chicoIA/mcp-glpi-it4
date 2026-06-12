"""Mapeamentos: recursos lógicos → paths v2.3, e tabelas de códigos do GLPI."""
from __future__ import annotations

# Recurso lógico → path namespaced da High-level API v2.3.
# Confirmados via Swagger da instância (swagger_paths.txt / endpoint_map.json).
RESOURCE_PATHS: dict[str, str] = {
    # Assistance
    "Ticket": "Assistance/Ticket",
    "Problem": "Assistance/Problem",
    "Change": "Assistance/Change",
    # Assets
    "Computer": "Assets/Computer",
    # Administration
    "Entity": "Administration/Entity",
    "Group": "Administration/Group",
    "User": "Administration/User",
    # Dropdowns
    "ITILCategory": "Dropdowns/ITILCategory",
    # Setup
    "Config": "Setup/Config",
    "SLA": "Setup/SLA",
}

# Sub-recursos de timeline de um chamado.
TICKET_TIMELINE = {
    "followup": "Timeline/Followup",
    "task": "Timeline/Task",
    "solution": "Timeline/Solution",
    "validation": "Timeline/Validation",
    "document": "Timeline/Document",
}

# Papéis de ator em chamados (TeamMember/{role}).
TICKET_ACTOR_ROLES = {"requester", "observer", "assign"}

TICKET_STATUS = {
    1: "Novo", 2: "Em atendimento (atribuído)", 3: "Em atendimento (planejado)",
    4: "Pendente", 5: "Solucionado", 6: "Fechado",
}
TICKET_TYPE = {1: "Incidente", 2: "Requisição"}
PRIORITY = {1: "Muito baixa", 2: "Baixa", 3: "Média", 4: "Alta", 5: "Muito alta", 6: "Maior"}


def resource_path(resource: str) -> str:
    """Resolve um recurso lógico para o path da API. Aceita path literal como fallback."""
    return RESOURCE_PATHS.get(resource, resource)


def label(table: dict[int, str], code) -> str:
    try:
        return table.get(int(code), str(code))
    except (TypeError, ValueError):
        return str(code)
