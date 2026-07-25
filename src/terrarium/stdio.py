from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import TextIO

from .evals import aggregate, evaluate
from .task import TaskSpec, load_fixture
from .world import World, create_snapshot, reset_snapshot, state_diff


def _response(request_id: object, result: object) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: object, code: int, message: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def serve(
    task: TaskSpec,
    input_stream: TextIO = sys.stdin,
    output_stream: TextIO = sys.stdout,
) -> None:
    with tempfile.TemporaryDirectory(prefix="terrarium-stdio-") as directory:
        root = Path(directory)
        snapshot = create_snapshot(load_fixture(task.fixture_path), root / "base.sqlite")
        database = reset_snapshot(snapshot, root / "session.sqlite")
        world = World(database)
        before = world.state()
        try:
            for line in input_stream:
                if not line.strip():
                    continue
                try:
                    request = json.loads(line)
                except json.JSONDecodeError:
                    output_stream.write(
                        json.dumps(_error(None, -32700, "parse error"), sort_keys=True)
                        + "\n"
                    )
                    output_stream.flush()
                    continue
                if not isinstance(request, dict):
                    response = _error(None, -32600, "invalid request")
                    output_stream.write(json.dumps(response, sort_keys=True) + "\n")
                    output_stream.flush()
                    continue
                request_id = request.get("id")
                method = request.get("method")
                notification = "id" not in request
                try:
                    if request.get("jsonrpc") != "2.0" or not isinstance(method, str):
                        response = _error(request_id, -32600, "invalid request")
                    elif method == "initialize":
                        response = _response(
                            request_id,
                            {
                                "protocolVersion": "2025-06-18",
                                "capabilities": {"tools": {}},
                                "serverInfo": {
                                    "name": "terrarium",
                                    "version": "0.1.0",
                                },
                            },
                        )
                    elif method in {"notifications/initialized", "notifications/cancelled"}:
                        response = None
                    elif method == "ping":
                        response = _response(request_id, {})
                    elif method == "tools/list":
                        response = _response(
                            request_id, {"tools": world.tool_definitions()}
                        )
                    elif method == "tools/call":
                        params = request.get("params", {})
                        if not isinstance(params, dict):
                            raise TypeError("params must be an object")
                        name = params.get("name")
                        arguments = params.get("arguments", {})
                        if not isinstance(name, str) or not isinstance(arguments, dict):
                            raise TypeError(
                                "tools/call requires name:string and arguments:object"
                            )
                        try:
                            value = world.call(name, arguments)
                            result = {
                                "content": [
                                    {
                                        "type": "text",
                                        "text": json.dumps(value, sort_keys=True),
                                    }
                                ],
                                "structuredContent": {"result": value},
                                "isError": False,
                            }
                        except Exception as exc:
                            result = {
                                "content": [{"type": "text", "text": str(exc)}],
                                "isError": True,
                            }
                        response = _response(request_id, result)
                    elif method == "terrarium/state":
                        response = _response(request_id, {"state": world.state()})
                    elif method == "terrarium/grade":
                        evaluations = evaluate(
                            task.evaluations, world.state(), world.trace()
                        )
                        response = _response(
                            request_id,
                            {
                                "verdict": aggregate(evaluations),
                                "evaluations": [
                                    {
                                        "criterion_id": item.criterion_id,
                                        "family": item.family,
                                        "verdict": item.verdict,
                                        "detail": item.detail,
                                    }
                                    for item in evaluations
                                ],
                                "world_diff": state_diff(before, world.state()),
                            },
                        )
                    elif method == "terrarium/reset":
                        world.close()
                        shutil.copy2(snapshot, database)
                        world = World(database)
                        before = world.state()
                        response = _response(
                            request_id, {"reset": True, "task_id": task.id}
                        )
                    else:
                        response = _error(request_id, -32601, "method not found")
                except (KeyError, TypeError, ValueError) as exc:
                    response = _error(request_id, -32602, str(exc))
                except Exception:
                    response = _error(request_id, -32603, "internal error")
                if notification or response is None:
                    continue
                output_stream.write(json.dumps(response, sort_keys=True) + "\n")
                output_stream.flush()
        finally:
            world.close()
