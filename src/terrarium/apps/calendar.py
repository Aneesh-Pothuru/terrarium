from __future__ import annotations

from .base import AppModule


class CalendarApp(AppModule):
    name = "calendar"

    def list(self, status: str = "active") -> list[dict]:
        rows = self.world.query(
            "SELECT * FROM calendar_events WHERE status=? ORDER BY start", (status,)
        )
        self.log_read("list", {"status": status, "count": len(rows)})
        return rows

    def create(self, title: str, start: str, end: str) -> dict:
        cursor = self.world.execute(
            "INSERT INTO calendar_events(title,start,end,status) VALUES(?,?,?,'active')",
            (title, start, end),
        )
        result = {"id": cursor.lastrowid, "title": title, "start": start, "end": end}
        self.log_write("create", result)
        return result

    def cancel(self, event_id: int) -> dict:
        self.world.execute(
            "UPDATE calendar_events SET status='cancelled' WHERE id=?", (event_id,)
        )
        result = {"id": event_id, "status": "cancelled"}
        self.log_write("cancel", result)
        return result
