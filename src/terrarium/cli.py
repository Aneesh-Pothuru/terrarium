from __future__ import annotations

import argparse
import json
from pathlib import Path

from .report import render_report
from .runner import load_run, run_task, save_run
from .stdio import serve
from .task import TaskSpec
from .validity import validate_task

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = Path(__file__).resolve().parent


def _demo(args: argparse.Namespace) -> int:
    source = ROOT / "examples" / "recorded"
    if not source.exists():
        source = PACKAGE_ROOT / "data" / "recorded"
    paths = sorted(source.glob("inbox-triage-*.json"))
    runs = [load_run(path) for path in paths]
    output = render_report(runs, args.output, "Inbox triage · three-run replay")
    if args.json_output:
        destination = Path(args.json_output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps([run.to_dict() for run in runs], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(f"TERRARIUM demo: replayed {len(runs)} bundled runs")
    print(f"report: {output}")
    return 0


def _run(args: argparse.Namespace) -> int:
    task = TaskSpec.load(args.task)
    run = run_task(task, model=args.model)
    save_run(run, args.output)
    print(f"{run.verdict} {run.task_id} · {len(run.trace)} trace events · {args.output}")
    return 0 if run.verdict != "FAIL" else 1


def _replay(args: argparse.Namespace) -> int:
    run = load_run(args.run)
    render_report([run], args.output, f"Replay · {run.run_id}")
    print(f"replayed {run.run_id}: {args.output}")
    return 0


def _diff(args: argparse.Namespace) -> int:
    left, right = load_run(args.left), load_run(args.right)
    render_report([left, right], args.output, f"Diff · {left.model} vs {right.model}")
    print(f"diff: {args.output}")
    return 0


def _validate(args: argparse.Namespace) -> int:
    result = validate_task(TaskSpec.load(args.task))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


def _serve(args: argparse.Namespace) -> int:
    if not args.stdio:
        raise SystemExit("only the explicit --stdio transport ships in v0.1")
    serve(TaskSpec.load(args.task))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="terrarium")
    commands = root.add_subparsers(dest="command", required=True)

    demo = commands.add_parser("demo")
    demo.add_argument("--output", default="docs/demo/index.html")
    demo.add_argument("--json-output")
    demo.set_defaults(handler=_demo)

    run = commands.add_parser("run")
    run.add_argument("--task", required=True)
    run.add_argument("--model", default="reference-scripted")
    run.add_argument("--output", default="work/run.json")
    run.set_defaults(handler=_run)

    replay = commands.add_parser("replay")
    replay.add_argument("run")
    replay.add_argument("--output", default="work/replay.html")
    replay.set_defaults(handler=_replay)

    diff = commands.add_parser("diff")
    diff.add_argument("left")
    diff.add_argument("right")
    diff.add_argument("--output", default="work/diff.html")
    diff.set_defaults(handler=_diff)

    task = commands.add_parser("task")
    task_commands = task.add_subparsers(dest="task_command", required=True)
    validate = task_commands.add_parser("validate")
    validate.add_argument("task")
    validate.set_defaults(handler=_validate)

    stdio = commands.add_parser("serve")
    stdio.add_argument("--task", required=True)
    stdio.add_argument("--stdio", action="store_true")
    stdio.set_defaults(handler=_serve)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    return int(args.handler(args))
