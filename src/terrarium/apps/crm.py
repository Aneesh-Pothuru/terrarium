from __future__ import annotations

from .base import AppModule


class CrmApp(AppModule):
    """CRM-lite and its attached ledger are one P0 app boundary."""

    name = "crm"

    def get_contact(self, contact_id: int) -> dict:
        rows = self.world.query("SELECT * FROM crm_contacts WHERE id=?", (contact_id,))
        self.log_read("get_contact", {"id": contact_id, "found": bool(rows)})
        if not rows:
            raise KeyError(contact_id)
        return rows[0]

    def update_contact(
        self, contact_id: int, status: str | None = None, note: str | None = None
    ) -> dict:
        current = self.get_contact(contact_id)
        next_status = status if status is not None else current["status"]
        next_note = note if note is not None else current["note"]
        self.world.execute(
            "UPDATE crm_contacts SET status=?,note=? WHERE id=?",
            (next_status, next_note, contact_id),
        )
        result = {"id": contact_id, "status": next_status, "note": next_note}
        self.log_write("update_contact", result)
        return result

    def ledger_query(self, contact_id: int | None = None) -> list[dict]:
        if contact_id is None:
            rows = self.world.query("SELECT * FROM ledger_entries ORDER BY id")
        else:
            rows = self.world.query(
                "SELECT * FROM ledger_entries WHERE contact_id=? ORDER BY id",
                (contact_id,),
            )
        self.log_read("ledger_query", {"contact_id": contact_id, "count": len(rows)})
        return rows

    def ledger_update(self, entry_id: int, status: str) -> dict:
        self.world.execute(
            "UPDATE ledger_entries SET status=? WHERE id=?", (status, entry_id)
        )
        result = {"id": entry_id, "status": status}
        self.log_write("ledger_update", result)
        return result
