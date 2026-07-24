from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from .evals import aggregate, evaluate
from .models import RunRecord
from .task import TaskSpec, load_fixture
from .world import World, create_snapshot, reset_snapshot, state_diff


def execute_actions(world: World, actions: list[dict[str, Any]]) -> list[Any]:
    return [
        world.call(action["tool"], dict(action.get("arguments", {})))
        for action in actions
    ]


def run_task(
    task: TaskSpec,
    actions: list[dict[str, Any]] | None = None,
    model: str = "reference-scripted",
    provider_fingerprint: str = "local-deterministic-v1",
) -> RunRecord:
    plan = task.oracle if actions is None else actions
    with tempfile.TemporaryDirectory(prefix="terrarium-run-") as directory:
        root = Path(directory)
        snapshot = create_snapshot(load_fixture(task.fixture_path), root / "base.sqlite")
        database = reset_snapshot(snapshot, root / "run.sqlite")
        with World(database) as world:
            before = world.state()
            execute_actions(world, plan)
            after = world.state()
            trace = world.trace()
            evaluations = evaluate(task.evaluations, after, trace)
        run_id = f"{task.id}-{task.content_hash[:10]}-{model.replace('/', '-')}"
        return RunRecord(
            run_id=run_id,
            task_id=task.id,
            task_hash=task.content_hash,
            model=model,
            provider_fingerprint=provider_fingerprint,
            seed=task.seed,
            trace=trace,
            before=before,
            after=after,
            world_diff=state_diff(before, after),
            evaluations=evaluations,
            verdict=aggregate(evaluations),
            metadata={
                "driver": "explicit action plan",
                "task_version": task.content_hash,
                "world_version": task.world_hash,
                "grader_version": task.grader_hash,
            },
        )


def save_run(run: RunRecord, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(run.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return destination


def load_run(path: str | Path) -> RunRecord:
    return RunRecord.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
