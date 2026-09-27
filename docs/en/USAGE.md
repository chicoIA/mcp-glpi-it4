# Usage Guide

🌍 [Português](../pt-BR/USO.md)

## 1. GLPI prerequisites

1. **API v2.3 enabled** (default in GLPI 11).
2. An **OAuth client** created under `Setup > OAuth Clients` → note `client_id` and `client_secret`.
3. A **service account** with a suitable profile (technician for tickets/inventory; super-admin for configuration).

## 2. Environment variables

Copy `.env.example` to `.env` and fill it in. Minimum required:

```
GLPI_BASE_URL=https://glpi.example.com
GLPI_CLIENT_ID=...
GLPI_CLIENT_SECRET=...
GLPI_USERNAME=...
GLPI_PASSWORD=...
GLPI_WRITE_MODE=dry_run
```

> Always start with `GLPI_WRITE_MODE=dry_run`. Switch to `live` only after you have reviewed the payloads.

## 3. Validate the connection

Ask Claude: *"Use glpi_status_sessao to validate the GLPI connection."*
Expected: `{"status":"ok","autenticado":true,...,"write_mode":"dry_run"}`.

> Tool names and arguments are in Portuguese by design (`glpi_listar_chamados`, `limite`, `offset`).
> They are stable API surface — renaming them would break existing prompts. Prompt in any language;
> the model maps your wording to the tool.

## 4. Example prompts

**Tickets**
- "List the 10 most recent tickets with status New (1)."
- "Open an incident: title 'Printer out of toner', description 'Finance dept', high urgency."
- "Add a follow-up to ticket 4521 saying it is under analysis."
- "Assign ticket 4521 to technician id 12."
- "Record the solution for ticket 4102: 'Restarting the service fixed it'."

**Inventory**
- "List computers whose name contains 'NB-'."
- "Show computer 87 with its installed software."
- "Register computer 'NB-Finance-03', serial 'ABC123', in entity 0."

**Configuration**
- "List the parameters of the 'core' context."
- "What is the value of core/default_requesttypes_id?"
- "Set core/default_requesttypes_id to 1." (requires `live`)

**Safety / rollback**
- "Am I in dry_run or live?" → `glpi_modo_escrita`
- "List what can still be reverted." → `glpi_listar_reversiveis`
- "Revert the last operation." → `glpi_reverter`

## 5. dry_run vs live

In `dry_run`, every create/update/delete returns:
```json
{"status":"dry_run","op":"create","path":"Assistance/Ticket","would_send":{...}}
```
Nothing is changed in GLPI. Review `would_send`, then run with `GLPI_WRITE_MODE=live`.

## 6. Useful codes

- **Ticket status:** 1 New · 2 Assigned · 3 Planned · 4 Pending · 5 Solved · 6 Closed
- **Type:** 1 Incident · 2 Request
- **Urgency/Priority:** 1 Very low … 5 Very high (6 Major)
- **Actor roles:** `requester`, `observer`, `assigned`
