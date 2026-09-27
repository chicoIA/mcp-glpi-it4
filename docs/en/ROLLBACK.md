# Reverting Changes

Project mandate: **every change made through the API has a path back.** Two layers of protection.

## 1. dry_run (prevention)

`GLPI_WRITE_MODE=dry_run` (default) makes create/update/delete **change nothing** — they only return the payload that would be sent. Use it to validate before executing.

## 2. Audit + rollback (correction)

In `live`, every write is recorded in `rollback_log.json` with what is needed to undo it:

| Operation | What is stored | How it reverts |
|---|---|---|
| create | resource, path, `id` | `DELETE` the item |
| update | `before` (previous values of the changed fields) | re-applies `before` |
| delete | soft-delete (`is_deleted=1`) | restores (`is_deleted=0`) |

Each record gets an `audit_id`.

## How to revert

**From the assistant (tools):**
- `glpi_listar_reversiveis` → pending operations with their `audit_id`.
- `glpi_reverter` (no argument) → reverts **all** pending operations in reverse order.
- `glpi_reverter audit_id="abc123"` → reverts **one** specific operation.

## Files

- `rollback_log.json` — revertible operations (not versioned; it is in `.gitignore`).
- `error_log.json` — API failures, for diagnosis.

Both live in `GLPI_AUDIT_DIR` (default `~/.mcp-glpi-it4`).

> **In Docker this matters:** the image sets `GLPI_AUDIT_DIR=/data` and declares a volume there.
> Run with `-v glpi_audit:/data` (or the compose file, which does it for you). Without a volume,
> the rollback log dies with the container and writes made in `live` become unrevertible.

After an item is reverted it is flagged `reverted: true` (it stays in the log, keeping the history).

## Limits

- **Permanent** deletion (purge) is not automatic — soft-delete leaves the item recoverable in the GLPI trash.
- Reverting an `update` restores only the fields the tool changed (minimal snapshot), not the whole item.
- If a third party modified the item after the operation, reverting overwrites it with the recorded `before` — check `glpi_listar_reversiveis` first.
