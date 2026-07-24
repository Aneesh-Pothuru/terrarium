from __future__ import annotations

from .base import AppModule


class ChatApp(AppModule):
    name = "chat"

    def search(self, query: str, channel: str | None = None) -> list[dict]:
        if channel:
            rows = self.world.query(
                "SELECT * FROM chat_messages WHERE channel=? AND body LIKE ? ORDER BY id",
                (channel, f"%{query}%"),
            )
        else:
            rows = self.world.query(
                "SELECT * FROM chat_messages WHERE body LIKE ? ORDER BY id",
                (f"%{query}%",),
            )
        self.log_read("search", {"query": query, "channel": channel, "count": len(rows)})
        return rows

    def send(self, channel: str, body: str) -> dict:
        cursor = self.world.execute(
            "INSERT INTO chat_messages(channel,sender,body) VALUES(?,'agent',?)",
            (channel, body),
        )
        result = {"id": cursor.lastrowid, "channel": channel, "body": body}
        self.log_write("send", result)
        return result
