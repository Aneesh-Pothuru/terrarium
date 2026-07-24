from __future__ import annotations

from .base import AppModule


class FilesApp(AppModule):
    name = "files"

    def search(self, query: str) -> list[dict]:
        rows = self.world.query(
            "SELECT path FROM files WHERE path LIKE ? ORDER BY path", (f"%{query}%",)
        )
        self.log_read("search", {"query": query, "count": len(rows)})
        return rows

    def read(self, path: str) -> dict:
        rows = self.world.query(
            "SELECT path,content,readable FROM files WHERE path=?", (path,)
        )
        if not rows:
            raise FileNotFoundError(path)
        if not rows[0]["readable"]:
            raise PermissionError(path)
        self.log_read("read", {"path": path})
        return rows[0]

    def write(self, path: str, content: str) -> dict:
        self.world.execute(
            """
            INSERT INTO files(path,content,readable) VALUES(?,?,1)
            ON CONFLICT(path) DO UPDATE SET content=excluded.content
            """,
            (path, content),
        )
        result = {"path": path, "bytes": len(content.encode("utf-8"))}
        self.log_write("write", result)
        return result
