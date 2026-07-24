from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import TextIO

from .task import TaskSpec, load_fixture
from .world import World, create_snapshot, reset_snapshot


def serve(task: TaskSpec, input_stream: TextIO = sys.stdin, output_stream: TextIO = sys.stdout) -> None:
    with tempfile.TemporaryDirectory(prefix="terrarium-stdio-") as directory:
        root = Path(directory)
        snapshot = create_snapshot(load_fixture(task.fixture_path), root / "base.sqlite")
        database = reset_snapshot(snapshot, root / "session.sqlite")
        with World(database) as world:
            for line in input_stream:
                if not line.strip():
                    continue
                request = json.loads(line)
                request_id = request.get("id")
                try:
                    if request.get("method") == "tools/list":
                        result = {
                            "tools": [
                                {"name": name, "description": "simulated app operation"}
                                for name in world.list_tools()
                            ]
                        }
                    elif request.get("method") == "tools/call":
                        params = request.get("params", {})
                        result = world.call(
                            params["name"], dict(params.get("arguments", {}))
                        )
                    else:
                        raise ValueError("supported methods: tools/list, tools/call")
                    response = {"jsonrpc": "2.0", "id": request_id, "result": result}
                except Exception as exc:
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32000, "message": str(exc)},
                    }
                output_stream.write(json.dumps(response, sort_keys=True) + "\n")
                output_stream.flush()

