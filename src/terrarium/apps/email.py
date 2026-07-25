from __future__ import annotations

from .base import AppModule


class EmailApp(AppModule):
    name = "email"

    def search(self, query: str, limit: int = 20) -> list[dict]:
        rows = self.world.query(
            """
            SELECT * FROM email_messages
            WHERE subject LIKE ? OR body LIKE ? OR sender LIKE ?
            ORDER BY id LIMIT ?
            """,
            (f"%{query}%", f"%{query}%", f"%{query}%", limit),
        )
        self.log_read("search", {"query": query, "limit": limit, "count": len(rows)})
        return rows

    def send(self, to: str, subject: str, body: str) -> dict:
        cursor = self.world.execute(
            """
            INSERT INTO email_messages(folder, sender, recipients, subject, body, read)
            VALUES('sent', 'agent@terrarium.local', ?, ?, ?, 1)
            """,
            (to, subject, body),
        )
        result = {"id": cursor.lastrowid, "to": to, "subject": subject}
        self.log_write("send", result)
        return result

    def mark_read(self, message_id: int) -> dict:
        cursor = self.world.execute(
            "UPDATE email_messages SET read=1 WHERE id=?", (message_id,)
        )
        if cursor.rowcount != 1:
            raise KeyError(message_id)
        result = {"id": message_id, "read": True}
        self.log_write("mark_read", result)
        return result
