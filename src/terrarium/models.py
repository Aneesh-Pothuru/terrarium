"""Vendored loopkit-compatible Python records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class TraceEvent:
    seq: int
    kind: str
    app: str
    operation: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class EvalResult:
    criterion_id: str
    family: str
    verdict: str
    detail: str


@dataclass
class RunRecord:
    run_id: str
    task_id: str
    task_hash: str
    model: str
    provider_fingerprint: str
    seed: int
    trace: list[TraceEvent]
    before: dict[str, Any]
    after: dict[str, Any]
    world_diff: dict[str, Any]
    evaluations: list[EvalResult]
    verdict: str
    tokens: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunRecord":
        payload = dict(data)
        payload["trace"] = [TraceEvent(**item) for item in data.get("trace", [])]
        payload["evaluations"] = [
            EvalResult(**item) for item in data.get("evaluations", [])
        ]
        return cls(**payload)

