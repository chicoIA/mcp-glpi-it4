# Guia de Uso

## 1. Pré-requisitos no GLPI

1. **API v2.3 ativa** (padrão no GLPI 11).
2. **Cliente OAuth** criado em `Setup > OAuth Clients` → anote `client_id` e `client_secret`.
3. Um **usuário de serviço** com o perfil adequado (técnico para chamados/inventário; super-admin para configuração).

## 2. Variáveis de ambiente

Copie `.env.example` para `.env` e preencha. Mínimo obrigatório:

```
GLPI_CLIENT_ID=...
GLPI_CLIENT_SECRET=...
GLPI_USERNAME=...
GLPI_PASSWORD=...
GLPI_WRITE_MODE=dry_run
```

> Comece sempre com `GLPI_WRITE_MODE=dry_run`. Só mude para `live` quando validar os payloads.

## 3. Validar a conexão

Peça ao Claude: *"Use glpi_status_sessao para validar a conexão com o GLPI."*
Resposta esperada: `{"status":"ok","autenticado":true,...,"write_mode":"dry_run"}`.

## 4. Exemplos de prompts

**Chamados**
- "Liste os 10 chamados mais recentes com status Novo (1)."
- "Abra um incidente: título 'Impressora sem toner', descrição 'Setor financeiro', urgência alta."
- "Adicione um acompanhamento ao chamado 4521 avisando que está em análise."
- "Atribua o chamado 4521 ao técnico de id 12."
- "Registre a solução do chamado 4102: 'Reinício do serviço resolveu'."

**Inventário**
- "Liste computadores cujo nome contém 'NB-'."
- "Mostre o computador 87 com os softwares instalados."
- "Cadastre o computador 'NB-Financeiro-03', serial 'ABC123', na entidade 0."

**Configuração**
- "Liste os parâmetros do contexto 'core'."
- "Qual o valor do parâmetro core/default_requesttypes_id?"
- "Altere core/default_requesttypes_id para 1." (exige `live`)

**Segurança / reversão**
- "Estou em dry_run ou live?" → `glpi_modo_escrita`
- "Liste o que ainda pode ser revertido." → `glpi_listar_reversiveis`
- "Reverta a última operação." → `glpi_reverter`

## 5. Modo dry_run vs live

Em `dry_run`, toda criação/atualização/exclusão devolve:
```json
{"status":"dry_run","op":"create","path":"Assistance/Ticket","would_send":{...}}
```
Nenhuma alteração é feita no GLPI. Revise o `would_send`, depois rode com `GLPI_WRITE_MODE=live`.

## 6. Códigos úteis

- **Status do chamado:** 1 Novo · 2 Atribuído · 3 Planejado · 4 Pendente · 5 Solucionado · 6 Fechado
- **Tipo:** 1 Incidente · 2 Requisição
- **Urgência/Prioridade:** 1 Muito baixa … 5 Muito alta (6 Maior)
- **Papéis de ator:** `requester`, `observer`, `assign`
