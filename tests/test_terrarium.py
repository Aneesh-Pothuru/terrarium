from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

from terrarium.report import render_report
from terrarium.runner import load_run, run_task, save_run
from terrarium.stdio import serve
from terrarium.task import TaskSpec, load_fixture
from terrarium.validity import validate_task
from terrarium.world import World, create_snapshot, reset_snapshot

ROOT = Path(__file__).resolve().parents[1]
TASK = ROOT / "examples" / "tasks" / "inbox-triage.yaml"


class TerrariumTests(unittest.TestCase):
    def test_task_hash_is_stable_and_schema_complete(self) -> None:
        first, second = TaskSpec.load(TASK), TaskSpec.load(TASK)
        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(len(first.content_hash), 64)
        self.assertEqual(len(first.world_hash), 64)
        self.assertEqual(len(first.grader_hash), 64)
        self.assertEqual(len({first.content_hash, first.world_hash, first.grader_hash}), 3)
        self.assertEqual(set(first.mutations), {item["id"] for item in first.evaluations})

    def test_snapshot_reset_and_all_five_apps_log(self) -> None:
        task = TaskSpec.load(TASK)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = create_snapshot(load_fixture(task.fixture_path), root / "base.sqlite")
            run = reset_snapshot(base, root / "run.sqlite")
            with World(run) as world:
                world.call("email.search", {"query": "refund"})
                world.call("calendar.list", {})
                world.call("files.search", {"query": "policy"})
                world.call("chat.search", {"query": "policy"})
                world.call("crm.get_contact", {"contact_id": 1})
                kinds = {(event.app, event.kind) for event in world.trace()}
                for app in ("email", "calendar", "files", "chat", "crm"):
                    self.assertIn((app, "read"), kinds)
            with World(base) as pristine:
                self.assertEqual(pristine.query("SELECT COUNT(*) AS n FROM trace")[0]["n"], 0)

    def test_validity_gate_oracle_null_and_mutations(self) -> None:
        result = validate_task(TaskSpec.load(TASK))
        self.assertTrue(result["valid"])
        self.assertTrue(result["oracle_passes"])
        self.assertTrue(result["null_agent_scores_zero"])
        self.assertTrue(
            all(item["violable"] for item in result["criterion_mutations"].values())
        )

    def test_run_round_trip_and_report(self) -> None:
        run = run_task(TaskSpec.load(TASK))
        self.assertEqual(run.verdict, "PASS")
        self.assertTrue(any(event.kind == "write" for event in run.trace))
        with tempfile.TemporaryDirectory() as directory:
            path = save_run(run, Path(directory) / "run.json")
            loaded = load_run(path)
            self.assertEqual(loaded.to_dict(), run.to_dict())
            report = render_report([loaded], Path(directory) / "report.html", "test")
            report_text = report.read_text(encoding="utf-8")
            self.assertIn("World diff", report_text)
            self.assertIn('id="scenario-select"', report_text)
            self.assertIn('id="run-data"', report_text)
            self.assertIn("../assets/demo.js", report_text)
            self.assertIn(loaded.run_id, report_text)

    def test_three_bundled_recordings_compare_same_task(self) -> None:
        runs = [
            load_run(path)
            for path in sorted((ROOT / "examples" / "recorded").glob("*.json"))
        ]
        self.assertEqual(len(runs), 3)
        self.assertEqual(len({run.task_hash for run in runs}), 1)
        self.assertEqual({run.verdict for run in runs}, {"PASS", "FAIL"})

    def test_stdio_lists_and_calls_tools(self) -> None:
        requests = io.StringIO(
            '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{}}\n'
            '{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n'
            '{"jsonrpc":"2.0","id":2,"method":"tools/call",'
            '"params":{"name":"email.search","arguments":{"query":"refund"}}}\n'
            '{"jsonrpc":"2.0","id":3,"method":"terrarium/state"}\n'
        )
        responses = io.StringIO()
        serve(TaskSpec.load(TASK), requests, responses)
        payloads = [json.loads(line) for line in responses.getvalue().splitlines()]
        self.assertEqual(payloads[0]["result"]["serverInfo"]["name"], "terrarium")
        self.assertEqual(len(payloads[1]["result"]["tools"]), 15)
        self.assertEqual(
            len(payloads[2]["result"]["structuredContent"]["result"]), 1
        )
        self.assertIn("email_messages", payloads[3]["result"]["state"])


if __name__ == "__main__":
    unittest.main()
