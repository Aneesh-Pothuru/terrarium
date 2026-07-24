from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TaskSpec:
    raw: dict[str, Any]
    source: Path

    @property
    def id(self) -> str:
        return str(self.raw["id"])

    @property
    def seed(self) -> int:
        return int(self.raw.get("seed", 0))

    @property
    def content_hash(self) -> str:
        canonical = json.dumps(self.raw, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @property
    def world_hash(self) -> str:
        return hashlib.sha256(self.fixture_path.read_bytes()).hexdigest()

    @property
    def grader_hash(self) -> str:
        canonical = json.dumps(
            self.evaluations, sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @property
    def fixture_path(self) -> Path:
        relative = self.raw["world"]["fixture"]
        return (self.source.parent / relative).resolve()

    @property
    def evaluations(self) -> list[dict[str, Any]]:
        return list(self.raw.get("evals", []))

    @property
    def oracle(self) -> list[dict[str, Any]]:
        return list(self.raw.get("oracle", []))

    @property
    def mutations(self) -> dict[str, list[dict[str, Any]]]:
        return dict(self.raw.get("mutations", {}))

    @classmethod
    def load(cls, path: str | Path) -> "TaskSpec":
        source = Path(path).resolve()
        try:
            raw = json.loads(source.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Task files use the zero-dependency JSON subset of YAML 1.2"
            ) from exc
        required = {"id", "world", "instruction", "evals", "oracle", "mutations"}
        missing = sorted(required - set(raw))
        if missing:
            raise ValueError(f"task missing required keys: {', '.join(missing)}")
        ids = [item["id"] for item in raw["evals"]]
        if len(ids) != len(set(ids)):
            raise ValueError("criterion ids must be unique")
        if set(ids) != set(raw["mutations"]):
            raise ValueError("each criterion must have exactly one mutation plan")
        return cls(raw=raw, source=source)


def load_fixture(path: Path) -> dict[str, list[dict[str, Any]]]:
    return json.loads(path.read_text(encoding="utf-8"))
