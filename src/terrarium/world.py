from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path
from typing import Any

from .apps import CalendarApp, ChatApp, CrmApp, EmailApp, FilesApp
from .models import TraceEvent

STATE_TABLES = (
    "email_messages",
    "calendar_events",
    "files",
    "chat_messages",
    "crm_contacts",
    "ledger_entries",
)

SCHEMA = """
CREATE TABLE email_messages(
  id INTEGER PRIMARY KEY, folder TEXT NOT NULL, sender TEXT NOT NULL,
  recipients TEXT NOT NULL, subject TEXT NOT NULL, body TEXT NOT NULL,
  read INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE calendar_events(
  id INTEGER PRIMARY KEY, title TEXT NOT NULL, start TEXT NOT NULL,
  end TEXT NOT NULL, status TEXT NOT NULL
);
CREATE TABLE files(
  path TEXT PRIMARY KEY, content TEXT NOT NULL, readable INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE chat_messages(
  id INTEGER PRIMARY KEY, channel TEXT NOT NULL, sender TEXT NOT NULL, body TEXT NOT NULL
);
CREATE TABLE crm_contacts(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL,
  status TEXT NOT NULL, note TEXT NOT NULL
);
CREATE TABLE ledger_entries(
  id INTEGER PRIMARY KEY, contact_id INTEGER NOT NULL, amount REAL NOT NULL,
  status TEXT NOT NULL
);
CREATE TABLE trace(
  seq INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, app TEXT NOT NULL,
  operation TEXT NOT NULL, payload_json TEXT NOT NULL
);
"""


def create_snapshot(fixture: dict[str, list[dict]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.executescript(SCHEMA)
        for table in STATE_TABLES:
            for row in fixture.get(table, []):
                columns = list(row)
                placeholders = ",".join("?" for _ in columns)
                connection.execute(
                    f"INSERT INTO {table}({','.join(columns)}) VALUES({placeholders})",
                    tuple(row[column] for column in columns),
                )
        connection.commit()
    finally:
        connection.close()
    return path


def reset_snapshot(snapshot: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(snapshot, destination)
    return destination


class World:
    def __init__(self, database: Path) -> None:
        self.database = database
        self.connection = sqlite3.connect(database)
        self.connection.row_factory = sqlite3.Row
        self.apps = {
            "email": EmailApp(self),
            "calendar": CalendarApp(self),
            "files": FilesApp(self),
            "chat": ChatApp(self),
            "crm": CrmApp(self),
        }

    def close(self) -> None:
        self.connection.commit()
        self.connection.close()

    def __enter__(self) -> "World":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def execute(self, sql: str, values: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        cursor = self.connection.execute(sql, values)
        self.connection.commit()
        return cursor

    def query(self, sql: str, values: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        return [dict(row) for row in self.connection.execute(sql, values).fetchall()]

    def log(
        self, kind: str, app: str, operation: str, payload: dict[str, Any]
    ) -> None:
        self.connection.execute(
            "INSERT INTO trace(kind,app,operation,payload_json) VALUES(?,?,?,?)",
            (kind, app, operation, json.dumps(payload, sort_keys=True)),
        )
        self.connection.commit()

    def trace(self) -> list[TraceEvent]:
        rows = self.query("SELECT * FROM trace ORDER BY seq")
        return [
            TraceEvent(
                seq=row["seq"],
                kind=row["kind"],
                app=row["app"],
                operation=row["operation"],
                payload=json.loads(row["payload_json"]),
            )
            for row in rows
        ]

    def state(self) -> dict[str, list[dict[str, Any]]]:
        return {
            table: self.query(f"SELECT * FROM {table} ORDER BY 1")
            for table in STATE_TABLES
        }

    def call(self, tool: str, arguments: dict[str, Any]) -> Any:
        if "." not in tool:
            raise ValueError(f"invalid tool name: {tool}")
        app_name, operation = tool.split(".", 1)
        if app_name == "ledger":
            app_name = "crm"
            operation = f"ledger_{operation}"
        app = self.apps.get(app_name)
        if app is None or operation.startswith("_") or not hasattr(app, operation):
            self.log("error", app_name, operation, {"error": "unknown tool"})
            raise KeyError(tool)
        self.log("tool", app_name, operation, {"arguments": arguments})
        try:
            return getattr(app, operation)(**arguments)
        except Exception as exc:
            self.log("error", app_name, operation, {"error": str(exc)})
            raise

    def list_tools(self) -> list[str]:
        return [
            "email.search",
            "email.send",
            "email.mark_read",
            "calendar.list",
            "calendar.create",
            "calendar.cancel",
            "files.search",
            "files.read",
            "files.write",
            "chat.search",
            "chat.send",
            "crm.get_contact",
            "crm.update_contact",
            "ledger.query",
            "ledger.update",
        ]


def state_diff(
    before: dict[str, list[dict[str, Any]]],
    after: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    diff: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for table in STATE_TABLES:
        before_rows = before.get(table, [])
        after_rows = after.get(table, [])
        added = [row for row in after_rows if row not in before_rows]
        removed = [row for row in before_rows if row not in after_rows]
        if added or removed:
            diff[table] = {"added": added, "removed": removed}
    return diff

