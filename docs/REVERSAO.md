# Reversão de Alterações

Mandato do projeto: **toda alteração feita via API tem caminho de reversão.** Há duas camadas de proteção.

## 1. dry_run (prevenção)

`GLPI_WRITE_MODE=dry_run` (padrão) faz com que criar/atualizar/excluir **não alterem nada** — apenas retornam o payload que seria enviado. Use para validar antes de executar.

## 2. Auditoria + rollback (correção)

Em `live`, cada escrita é registrada em `rollback_log.json` com o necessário para desfazer:

| Operação | O que é gravado | Como reverte |
|---|---|---|
| create | recurso, path, `id` | `DELETE` do item |
| update | `before` (valores anteriores dos campos alterados) | reaplica `before` |
| delete | soft-delete (`is_deleted=1`) | restaura (`is_deleted=0`) |

Cada registro recebe um `audit_id`.

## Como reverter

**Pelo Claude (tools):**
- `glpi_listar_reversiveis` → mostra operações pendentes com `audit_id`.
- `glpi_reverter` (sem argumento) → reverte **todas** as pendentes em ordem reversa.
- `glpi_reverter audit_id="abc123"` → reverte **uma** operação específica.

**Pela linha de comando (lote, reaproveitando o script original):**
```bash
cd ../scripts_glpi
python rollback.py --dry-run     # lista sem apagar
python rollback.py               # reverte tudo (com confirmação)
python rollback.py --type Ticket # reverte só um tipo
```

## Arquivos

- `rollback_log.json` — operações reversíveis (não versionar; está no `.gitignore`).
- `error_log.json` — falhas de API para diagnóstico.

Após reverter um item, ele é marcado `reverted: true` (não some do log, mantém histórico).

## Limites

- Exclusão **definitiva** (purge) não é automática — soft-delete deixa o item recuperável na lixeira do GLPI.
- Reversão de `update` restaura apenas os campos que a tool alterou (snapshot mínimo), não o item inteiro.
- Se o item já foi modificado por terceiros após a operação, a reversão sobrescreve com o `before` registrado — confira com `glpi_listar_reversiveis` antes.
