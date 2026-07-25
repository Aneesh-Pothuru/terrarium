"""Persistent local HTTP service over TERRARIUM's deterministic engine.

The service deliberately uses only Python's standard library. It is intended
for a trusted workstation or a container behind an authenticated gateway; the
default bind address is loopback and remote binding requires an explicit flag.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import shutil
import sys
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .evals import aggregate, evaluate
from .models import RunRecord
from .task import TaskSpec, load_fixture
from .validity import validate_task
from .world import World, create_snapshot, state_diff

SESSION_ID = re.compile(r"^[0-9a-f]{32}$")
REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
DEFAULT_MAX_BODY_BYTES = 64 * 1024
DEFAULT_MAX_PATH_BYTES = 2048
DEFAULT_MAX_ACTIONS = 100
DEFAULT_MAX_SESSIONS = 1000


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


class ServiceError(Exception):
    def __init__(
        self, status: HTTPStatus, code: str, message: str, details: Any = None
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details


@dataclass(frozen=True)
class ServiceConfig:
    host: str = "127.0.0.1"
    port: int = 8700
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES
    max_path_bytes: int = DEFAULT_MAX_PATH_BYTES
    max_actions: int = DEFAULT_MAX_ACTIONS
    max_sessions: int = DEFAULT_MAX_SESSIONS
    cors_origin: str | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.port <= 65535:
            raise ValueError("port must be between 0 and 65535")
        for name in (
            "max_body_bytes",
            "max_path_bytes",
            "max_actions",
            "max_sessions",
        ):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")


class SessionStore:
    """Owns restart-safe task snapshots and per-session SQLite worlds."""

    def __init__(
        self,
        task: TaskSpec,
        data_dir: str | Path,
        max_actions: int = DEFAULT_MAX_ACTIONS,
        max_sessions: int = DEFAULT_MAX_SESSIONS,
    ) -> None:
        self.task = task
        self.data_dir = Path(data_dir).expanduser().resolve()
        self.sessions_dir = self.data_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.base_database = self.data_dir / f"base-{task.content_hash}.sqlite"
        self.max_actions = max_actions
        self.max_sessions = max_sessions
        self._locks_guard = threading.Lock()
        self._create_lock = threading.Lock()
        self._locks: dict[str, threading.RLock] = {}
        if not self.base_database.exists():
            create_snapshot(load_fixture(task.fixture_path), self.base_database)
        self.validity = validate_task(task)
        if not self.validity["valid"]:
            raise ValueError(
                f"task {task.id!r} failed its validity gate: "
                f"{self.validity['verdict']}"
            )

    def _lock(self, session_id: str) -> threading.RLock:
        with self._locks_guard:
            return self._locks.setdefault(session_id, threading.RLock())

    def _session_dir(self, session_id: str) -> Path:
        if not SESSION_ID.fullmatch(session_id):
            raise ServiceError(
                HTTPStatus.NOT_FOUND, "session_not_found", "session was not found"
            )
        path = self.sessions_dir / session_id
        if not path.is_dir():
            raise ServiceError(
                HTTPStatus.NOT_FOUND, "session_not_found", "session was not found"
            )
        return path

    def _metadata(self, session_id: str) -> dict[str, Any]:
        path = self._session_dir(session_id) / "session.json"
        try:
            metadata = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ServiceError(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "session_corrupt",
                "session metadata could not be read",
            ) from exc
        if metadata.get("task_hash") != self.task.content_hash:
            raise ServiceError(
                HTTPStatus.CONFLICT,
                "task_version_mismatch",
                "session belongs to a different task version",
            )
        return metadata

    def _write_metadata(self, session_id: str, metadata: dict[str, Any]) -> None:
        _atomic_json(self._session_dir(session_id) / "session.json", metadata)

    def _database(self, session_id: str) -> Path:
        database = self._session_dir(session_id) / "world.sqlite"
        if not database.is_file():
            raise ServiceError(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "session_corrupt",
                "session world could not be read",
            )
        return database

    def create(self, model: str = "external-agent") -> dict[str, Any]:
        with self._create_lock:
            session_count = sum(
                1 for path in self.sessions_dir.iterdir() if path.is_dir()
            )
            if session_count >= self.max_sessions:
                raise ServiceError(
                    HTTPStatus.CONFLICT,
                    "session_limit",
                    "configured session limit has been reached",
                )
            session_id = uuid.uuid4().hex
            session_dir = self.sessions_dir / session_id
            session_dir.mkdir()
            shutil.copy2(self.base_database, session_dir / "world.sqlite")
            created_at = _now()
            metadata = {
                "id": session_id,
                "task_id": self.task.id,
                "task_hash": self.task.content_hash,
                "world_hash": self.task.world_hash,
                "grader_hash": self.task.grader_hash,
                "model": model,
                "created_at": created_at,
                "updated_at": created_at,
                "reset_count": 0,
            }
            _atomic_json(session_dir / "session.json", metadata)
            return metadata

    def list(self) -> list[dict[str, Any]]:
        sessions: list[dict[str, Any]] = []
        for path in self.sessions_dir.iterdir():
            if path.is_dir() and SESSION_ID.fullmatch(path.name):
                try:
                    sessions.append(self._metadata(path.name))
                except ServiceError:
                    continue
        return sorted(sessions, key=lambda item: item["created_at"], reverse=True)

    def summary(self, session_id: str) -> dict[str, Any]:
        with self._lock(session_id):
            metadata = self._metadata(session_id)
            with World(self._database(session_id)) as world:
                trace_count = len(world.trace())
            return {**metadata, "trace_events": trace_count}

    def reset(self, session_id: str) -> dict[str, Any]:
        with self._lock(session_id):
            metadata = self._metadata(session_id)
            shutil.copy2(self.base_database, self._database(session_id))
            metadata["reset_count"] = int(metadata.get("reset_count", 0)) + 1
            metadata["updated_at"] = _now()
            self._write_metadata(session_id, metadata)
            return {**metadata, "trace_events": 0}

    def state(self, session_id: str) -> dict[str, list[dict[str, Any]]]:
        with self._lock(session_id):
            with World(self._database(session_id)) as world:
                return world.state()

    def timeline(self, session_id: str) -> list[dict[str, Any]]:
        with self._lock(session_id):
            with World(self._database(session_id)) as world:
                return [asdict(event) for event in world.trace()]

    def call(
        self, session_id: str, name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        if not isinstance(name, str) or not isinstance(arguments, dict):
            raise ServiceError(
                HTTPStatus.BAD_REQUEST,
                "invalid_request",
                "name must be a string and arguments must be an object",
            )
        with self._lock(session_id):
            metadata = self._metadata(session_id)
            try:
                with World(self._database(session_id)) as world:
                    result = world.call(name, arguments)
                    trace_events = len(world.trace())
            except KeyError as exc:
                raise ServiceError(
                    HTTPStatus.UNPROCESSABLE_ENTITY,
                    "tool_not_found_or_resource_missing",
                    str(exc),
                ) from exc
            except (TypeError, ValueError, PermissionError, FileNotFoundError) as exc:
                raise ServiceError(
                    HTTPStatus.UNPROCESSABLE_ENTITY,
                    "tool_call_failed",
                    str(exc),
                ) from exc
            metadata["updated_at"] = _now()
            self._write_metadata(session_id, metadata)
            return {"result": result, "trace_events": trace_events}

    def actions(
        self,
        session_id: str,
        actions: list[dict[str, Any]],
        model: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(actions, list) or not actions:
            raise ServiceError(
                HTTPStatus.BAD_REQUEST,
                "invalid_actions",
                "actions must be a non-empty array",
            )
        if len(actions) > self.max_actions:
            raise ServiceError(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                "too_many_actions",
                f"at most {self.max_actions} actions are accepted per request",
            )
        with self._lock(session_id):
            metadata = self._metadata(session_id)
            results = []
            with World(self._database(session_id)) as world:
                for index, action in enumerate(actions):
                    if not isinstance(action, dict):
                        raise ServiceError(
                            HTTPStatus.BAD_REQUEST,
                            "invalid_action",
                            "each action must be an object",
                            {"index": index, "completed": len(results)},
                        )
                    name = action.get("tool")
                    arguments = action.get("arguments", {})
                    if not isinstance(name, str) or not isinstance(arguments, dict):
                        raise ServiceError(
                            HTTPStatus.BAD_REQUEST,
                            "invalid_action",
                            "each action requires tool:string and arguments:object",
                            {"index": index, "completed": len(results)},
                        )
                    try:
                        results.append(world.call(name, arguments))
                    except Exception as exc:
                        raise ServiceError(
                            HTTPStatus.UNPROCESSABLE_ENTITY,
                            "action_failed",
                            str(exc),
                            {
                                "index": index,
                                "tool": name,
                                "completed": len(results),
                                "partial_side_effects": bool(results),
                            },
                        ) from exc
                trace_events = len(world.trace())
            if model is not None:
                metadata["model"] = model
            metadata["updated_at"] = _now()
            self._write_metadata(session_id, metadata)
            return {
                "results": results,
                "completed": len(results),
                "trace_events": trace_events,
            }

    def evidence(self, session_id: str) -> RunRecord:
        with self._lock(session_id):
            metadata = self._metadata(session_id)
            with World(self.base_database) as base:
                before = base.state()
            with World(self._database(session_id)) as world:
                after = world.state()
                trace = world.trace()
            evaluations = evaluate(self.task.evaluations, after, trace)
            return RunRecord(
                run_id=f"{self.task.id}-{session_id}",
                task_id=self.task.id,
                task_hash=self.task.content_hash,
                model=metadata["model"],
                provider_fingerprint="terrarium-local-service-v1",
                seed=self.task.seed,
                trace=trace,
                before=before,
                after=after,
                world_diff=state_diff(before, after),
                evaluations=evaluations,
                verdict=aggregate(evaluations),
                metadata={
                    "session_id": session_id,
                    "driver": "external actions via local HTTP service",
                    "task_version": self.task.content_hash,
                    "world_version": self.task.world_hash,
                    "grader_version": self.task.grader_hash,
                    "created_at": metadata["created_at"],
                    "updated_at": metadata["updated_at"],
                    "reset_count": metadata["reset_count"],
                },
            )

    def grade(self, session_id: str) -> dict[str, Any]:
        run = self.evidence(session_id)
        return {
            "session_id": session_id,
            "verdict": run.verdict,
            "evaluations": [asdict(result) for result in run.evaluations],
            "trace_events": len(run.trace),
            "world_diff": run.world_diff,
        }

    def run(
        self, actions: list[dict[str, Any]], model: str = "external-agent"
    ) -> dict[str, Any]:
        if not isinstance(actions, list) or not actions:
            raise ServiceError(
                HTTPStatus.BAD_REQUEST,
                "invalid_actions",
                "actions must be a non-empty array",
            )
        if len(actions) > self.max_actions:
            raise ServiceError(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                "too_many_actions",
                f"at most {self.max_actions} actions are accepted per request",
            )
        session = self.create(model=model)
        self.actions(session["id"], actions)
        return self.evidence(session["id"]).to_dict()

    def readiness(self) -> dict[str, Any]:
        probe = self.data_dir / ".write-probe"
        try:
            probe.write_text("ready", encoding="utf-8")
            probe.unlink()
            with World(self.base_database) as world:
                table_count = len(world.state())
        except (OSError, RuntimeError) as exc:
            return {"ready": False, "reason": str(exc)}
        return {
            "ready": table_count > 0 and bool(self.validity["valid"]),
            "task_id": self.task.id,
            "task_hash": self.task.content_hash,
            "task_valid": bool(self.validity["valid"]),
        }


class TerrariumHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self, address: tuple[str, int], store: SessionStore, config: ServiceConfig
    ) -> None:
        self.store = store
        self.config = config
        super().__init__(address, TerrariumHandler)


class TerrariumHandler(BaseHTTPRequestHandler):
    server: TerrariumHTTPServer
    server_version = "Terrarium/0.1"
    sys_version = ""

    def _request_id(self) -> str:
        supplied = self.headers.get("X-Request-ID", "")
        return supplied if REQUEST_ID.fullmatch(supplied) else uuid.uuid4().hex

    def _headers(
        self, status: HTTPStatus, request_id: str, content_length: int = 0
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(content_length))
        self.send_header("X-Request-ID", request_id)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        origin = self.server.config.cors_origin
        if origin and self.headers.get("Origin") == origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()

    def _json(self, status: HTTPStatus, request_id: str, data: Any) -> None:
        body = json.dumps(
            {"request_id": request_id, "data": data},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self._headers(status, request_id, len(body))
        if self.command != "HEAD":
            self.wfile.write(body)

    def _error(self, request_id: str, error: ServiceError) -> None:
        payload: dict[str, Any] = {
            "request_id": request_id,
            "error": {"code": error.code, "message": error.message},
        }
        if error.details is not None:
            payload["error"]["details"] = error.details
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        self._headers(error.status, request_id, len(body))
        if self.command != "HEAD":
            self.wfile.write(body)

    def _path(self) -> str:
        target = self.path.encode("utf-8")
        if len(target) > self.server.config.max_path_bytes:
            raise ServiceError(
                HTTPStatus.REQUEST_URI_TOO_LONG,
                "path_too_long",
                "request target exceeds the configured limit",
            )
        return urlsplit(self.path).path.rstrip("/") or "/"

    def _body(self) -> dict[str, Any]:
        if self.headers.get("Transfer-Encoding"):
            raise ServiceError(
                HTTPStatus.LENGTH_REQUIRED,
                "content_length_required",
                "chunked request bodies are not supported",
            )
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise ServiceError(
                HTTPStatus.BAD_REQUEST,
                "invalid_content_length",
                "Content-Length must be an integer",
            ) from exc
        if length < 0:
            raise ServiceError(
                HTTPStatus.BAD_REQUEST,
                "invalid_content_length",
                "Content-Length cannot be negative",
            )
        if length > self.server.config.max_body_bytes:
            raise ServiceError(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                "body_too_large",
                "request body exceeds the configured limit",
            )
        if length == 0:
            return {}
        media_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip()
        if media_type != "application/json":
            raise ServiceError(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                "json_required",
                "Content-Type must be application/json",
            )
        try:
            payload = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ServiceError(
                HTTPStatus.BAD_REQUEST, "invalid_json", "request body is not valid JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise ServiceError(
                HTTPStatus.BAD_REQUEST,
                "object_required",
                "request body must be a JSON object",
            )
        return payload

    def _session_route(self, path: str) -> tuple[str, str] | None:
        parts = path.strip("/").split("/")
        if len(parts) >= 3 and parts[:2] == ["v1", "sessions"]:
            session_id = parts[2]
            suffix = "/".join(parts[3:])
            return session_id, suffix
        return None

    def _dispatch_get(self, path: str) -> tuple[HTTPStatus, Any]:
        store = self.server.store
        if path == "/healthz":
            return HTTPStatus.OK, {"status": "ok", "service": "terrarium"}
        if path == "/readyz":
            readiness = store.readiness()
            return (
                HTTPStatus.OK
                if readiness["ready"]
                else HTTPStatus.SERVICE_UNAVAILABLE,
                readiness,
            )
        if path == "/v1/task":
            return HTTPStatus.OK, {
                "id": store.task.id,
                "instruction": store.task.raw["instruction"],
                "seed": store.task.seed,
                "task_hash": store.task.content_hash,
                "world_hash": store.task.world_hash,
                "grader_hash": store.task.grader_hash,
                "validity": store.validity,
            }
        if path == "/v1/tools":
            with World(store.base_database) as world:
                return HTTPStatus.OK, {"tools": world.tool_definitions()}
        if path == "/v1/sessions":
            return HTTPStatus.OK, {"sessions": store.list()}
        route = self._session_route(path)
        if route:
            session_id, suffix = route
            if not suffix:
                return HTTPStatus.OK, store.summary(session_id)
            if suffix == "state":
                return HTTPStatus.OK, store.state(session_id)
            if suffix == "timeline":
                return HTTPStatus.OK, {"events": store.timeline(session_id)}
            if suffix == "evidence":
                return HTTPStatus.OK, store.evidence(session_id).to_dict()
        raise ServiceError(HTTPStatus.NOT_FOUND, "not_found", "route was not found")

    def _dispatch_post(
        self, path: str, body: dict[str, Any]
    ) -> tuple[HTTPStatus, Any]:
        store = self.server.store
        if path == "/v1/task/validate":
            return HTTPStatus.OK, store.validity
        if path == "/v1/sessions":
            model = body.get("model", "external-agent")
            if not isinstance(model, str) or not model.strip():
                raise ServiceError(
                    HTTPStatus.BAD_REQUEST,
                    "invalid_model",
                    "model must be a non-empty string",
                )
            return HTTPStatus.CREATED, store.create(model=model)
        if path == "/v1/runs":
            actions = body.get("actions")
            model = body.get("model", "external-agent")
            if not isinstance(model, str) or not model.strip():
                raise ServiceError(
                    HTTPStatus.BAD_REQUEST,
                    "invalid_model",
                    "model must be a non-empty string",
                )
            return HTTPStatus.CREATED, store.run(actions, model)
        route = self._session_route(path)
        if route:
            session_id, suffix = route
            if suffix == "reset":
                return HTTPStatus.OK, store.reset(session_id)
            if suffix == "tools/call":
                return HTTPStatus.OK, store.call(
                    session_id, body.get("name"), body.get("arguments", {})
                )
            if suffix == "actions":
                model = body.get("model")
                if model is not None and not isinstance(model, str):
                    raise ServiceError(
                        HTTPStatus.BAD_REQUEST,
                        "invalid_model",
                        "model must be a string",
                    )
                return HTTPStatus.OK, store.actions(
                    session_id, body.get("actions"), model
                )
            if suffix == "grade":
                return HTTPStatus.OK, store.grade(session_id)
        raise ServiceError(HTTPStatus.NOT_FOUND, "not_found", "route was not found")

    def _handle(self) -> None:
        request_id = self._request_id()
        try:
            path = self._path()
            if self.command in {"GET", "HEAD"}:
                status, data = self._dispatch_get(path)
            elif self.command == "POST":
                status, data = self._dispatch_post(path, self._body())
            else:
                raise ServiceError(
                    HTTPStatus.METHOD_NOT_ALLOWED,
                    "method_not_allowed",
                    "method is not allowed",
                )
            self._json(status, request_id, data)
        except ServiceError as error:
            self._error(request_id, error)
        except Exception:
            self._error(
                request_id,
                ServiceError(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    "internal_error",
                    "an unexpected error occurred",
                ),
            )

    def do_GET(self) -> None:
        self._handle()

    def do_HEAD(self) -> None:
        self._handle()

    def do_POST(self) -> None:
        self._handle()

    def do_OPTIONS(self) -> None:
        request_id = self._request_id()
        origin = self.server.config.cors_origin
        if not origin or self.headers.get("Origin") != origin:
            self._error(
                request_id,
                ServiceError(
                    HTTPStatus.FORBIDDEN,
                    "origin_not_allowed",
                    "origin is not allowed",
                ),
            )
            return
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Content-Length", "0")
        self.send_header("X-Request-ID", request_id)
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Request-ID")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, POST, OPTIONS")
        self.send_header("Vary", "Origin")
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        sys.stderr.write(
            json.dumps(
                {
                    "time": _now(),
                    "remote": self.client_address[0],
                    "request": self.requestline,
                    "message": format % args,
                },
                sort_keys=True,
            )
            + "\n"
        )


def _loopback(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def serve_http(
    task: TaskSpec,
    data_dir: str | Path,
    config: ServiceConfig | None = None,
    allow_remote: bool = False,
) -> None:
    config = config or ServiceConfig()
    if not _loopback(config.host) and not allow_remote:
        raise ValueError(
            "refusing a non-loopback bind without the explicit --allow-remote flag"
        )
    store = SessionStore(
        task,
        data_dir,
        max_actions=config.max_actions,
        max_sessions=config.max_sessions,
    )
    server = TerrariumHTTPServer((config.host, config.port), store, config)
    print(
        f"TERRARIUM service ready: http://{config.host}:{server.server_port} "
        f"· task {task.id} · data {store.data_dir}",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    return default if value is None else int(value)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="terrarium-service")
    default_task = os.environ.get("TERRARIUM_TASK")
    root.add_argument(
        "--task",
        default=default_task,
        required=default_task is None,
    )
    root.add_argument(
        "--data-dir",
        default=os.environ.get("TERRARIUM_DATA_DIR", "work/service"),
    )
    root.add_argument("--host", default=os.environ.get("TERRARIUM_HOST", "127.0.0.1"))
    root.add_argument(
        "--port", type=int, default=_env_int("TERRARIUM_PORT", 8700)
    )
    root.add_argument(
        "--max-body-bytes",
        type=int,
        default=_env_int("TERRARIUM_MAX_BODY_BYTES", DEFAULT_MAX_BODY_BYTES),
    )
    root.add_argument(
        "--max-actions",
        type=int,
        default=_env_int("TERRARIUM_MAX_ACTIONS", DEFAULT_MAX_ACTIONS),
    )
    root.add_argument(
        "--max-sessions",
        type=int,
        default=_env_int("TERRARIUM_MAX_SESSIONS", DEFAULT_MAX_SESSIONS),
    )
    root.add_argument("--cors-origin", default=os.environ.get("TERRARIUM_CORS_ORIGIN"))
    root.add_argument("--allow-remote", action="store_true")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if not (0 <= args.port <= 65535):
        raise SystemExit("--port must be between 0 and 65535")
    for name in ("max_body_bytes", "max_actions", "max_sessions"):
        if getattr(args, name) <= 0:
            raise SystemExit(f"--{name.replace('_', '-')} must be positive")
    config = ServiceConfig(
        host=args.host,
        port=args.port,
        max_body_bytes=args.max_body_bytes,
        max_actions=args.max_actions,
        max_sessions=args.max_sessions,
        cors_origin=args.cors_origin,
    )
    serve_http(
        TaskSpec.load(args.task),
        args.data_dir,
        config=config,
        allow_remote=args.allow_remote,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
