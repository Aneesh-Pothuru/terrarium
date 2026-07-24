from __future__ import annotations

from typing import Any

from .models import EvalResult, TraceEvent


def _matches(row: dict[str, Any], where: dict[str, Any]) -> bool:
    return all(row.get(key) == value for key, value in where.items())


def evaluate(
    criteria: list[dict[str, Any]],
    state: dict[str, list[dict[str, Any]]],
    trace: list[TraceEvent],
) -> list[EvalResult]:
    results: list[EvalResult] = []
    for criterion in criteria:
        family = criterion["family"]
        criterion_id = criterion["id"]
        if family == "state":
            rows = [
                row
                for row in state.get(criterion["table"], [])
                if _matches(row, criterion.get("where", {}))
            ]
            expected = int(criterion.get("count", 1))
            passed = len(rows) == expected
            results.append(
                EvalResult(
                    criterion_id,
                    family,
                    "PASS" if passed else "FAIL",
                    f"matched {len(rows)} row(s); expected {expected}",
                )
            )
        elif family == "trajectory":
            tool = criterion["tool"]
            app, operation = tool.split(".", 1)
            if app == "ledger":
                app, operation = "crm", f"ledger_{operation}"
            calls = [
                event
                for event in trace
                if event.kind == "tool"
                and event.app == app
                and event.operation == operation
            ]
            minimum = int(criterion.get("min_calls", 1))
            passed = len(calls) >= minimum
            results.append(
                EvalResult(
                    criterion_id,
                    family,
                    "PASS" if passed else "FAIL",
                    f"observed {len(calls)} call(s); required {minimum}",
                )
            )
        elif family == "llm_judge":
            results.append(
                EvalResult(
                    criterion_id,
                    family,
                    "UNDETERMINED",
                    "LLM judges are disabled in keyless deterministic mode",
                )
            )
        else:
            raise ValueError(f"unknown evaluation family: {family}")
    return results


def aggregate(results: list[EvalResult]) -> str:
    if any(result.verdict == "FAIL" for result in results):
        return "FAIL"
    if any(result.verdict == "UNDETERMINED" for result in results):
        return "UNDETERMINED"
    return "PASS"

