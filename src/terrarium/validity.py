from __future__ import annotations

from dataclasses import asdict

from .runner import run_task
from .task import TaskSpec


def validate_task(task: TaskSpec) -> dict:
    oracle = run_task(task, task.oracle, model="oracle")
    null = run_task(task, [], model="null")
    oracle_passes = oracle.verdict == "PASS"
    null_fails = all(result.verdict == "FAIL" for result in null.evaluations)

    mutation_results = {}
    for criterion in task.evaluations:
        criterion_id = criterion["id"]
        mutation_run = run_task(
            task, task.mutations[criterion_id], model=f"mutation-{criterion_id}"
        )
        by_id = {
            result.criterion_id: result.verdict
            for result in mutation_run.evaluations
        }
        mutation_results[criterion_id] = {
            "violable": by_id.get(criterion_id) == "FAIL",
            "evaluations": [asdict(result) for result in mutation_run.evaluations],
        }

    valid = (
        oracle_passes
        and null_fails
        and all(item["violable"] for item in mutation_results.values())
    )
    return {
        "task_id": task.id,
        "task_hash": task.content_hash,
        "valid": valid,
        "oracle_passes": oracle_passes,
        "null_agent_scores_zero": null_fails,
        "criterion_mutations": mutation_results,
        "verdict": "TASK_VALID" if valid else "TASK_INVALID",
    }

