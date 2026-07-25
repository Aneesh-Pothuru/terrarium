from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http import HTTPStatus
from pathlib import Path

from terrarium.service import (
    ServiceConfig,
    SessionStore,
    TerrariumHTTPServer,
)
from terrarium.task import TaskSpec

ROOT = Path(__file__).resolve().parents[1]
TASK_PATH = ROOT / "examples" / "tasks" / "inbox-triage.yaml"


class SessionStoreTests(unittest.TestCase):
    def test_session_actions_grade_reset_and_restart(self) -> None:
        task = TaskSpec.load(TASK_PATH)
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(task, directory)
            session = store.create(model="integration-test")
            result = store.actions(session["id"], task.oracle)
            self.assertEqual(result["completed"], len(task.oracle))
            grade = store.grade(session["id"])
            self.assertEqual(grade["verdict"], "PASS")
            self.assertTrue(grade["world_diff"])

            restarted = SessionStore(task, directory)
            evidence = restarted.evidence(session["id"])
            self.assertEqual(evidence.verdict, "PASS")
            self.assertEqual(evidence.model, "integration-test")
            self.assertGreater(len(evidence.trace), 0)

            reset = restarted.reset(session["id"])
            self.assertEqual(reset["reset_count"], 1)
            self.assertEqual(restarted.grade(session["id"])["verdict"], "FAIL")
            self.assertEqual(restarted.timeline(session["id"]), [])

    def test_bad_action_reports_partial_side_effects(self) -> None:
        task = TaskSpec.load(TASK_PATH)
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(task, directory)
            session = store.create()
            with self.assertRaisesRegex(Exception, "missing.tool") as raised:
                store.actions(
                    session["id"],
                    [
                        task.oracle[0],
                        {"tool": "missing.tool", "arguments": {}},
                    ],
                )
            self.assertEqual(raised.exception.details["completed"], 1)
            self.assertTrue(raised.exception.details["partial_side_effects"])
            self.assertGreater(len(store.timeline(session["id"])), 0)

    def test_invalid_one_shot_run_does_not_allocate_session(self) -> None:
        task = TaskSpec.load(TASK_PATH)
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(task, directory)
            with self.assertRaisesRegex(Exception, "non-empty array"):
                store.run([])
            self.assertEqual(store.list(), [])


class HTTPServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        task = TaskSpec.load(TASK_PATH)
        store = SessionStore(task, self.temporary.name)
        config = ServiceConfig(port=0, max_body_bytes=4096)
        self.server = TerrariumHTTPServer(("127.0.0.1", 0), store, config)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        request_id: str = "test-request-1",
    ) -> tuple[int, dict, object]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            self.base + path,
            data=data,
            method=method,
            headers={
                "Content-Type": "application/json",
                "X-Request-ID": request_id,
            },
        )
        try:
            response = urllib.request.urlopen(request, timeout=3)
        except urllib.error.HTTPError as error:
            response = error
        payload = json.loads(response.read())
        status, headers = response.status, response.headers
        response.close()
        return status, payload, headers

    def test_end_to_end_http_journey(self) -> None:
        status, health, headers = self.request("GET", "/healthz")
        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(health["data"]["status"], "ok")
        self.assertEqual(headers["X-Request-ID"], "test-request-1")

        status, task, _ = self.request("GET", "/v1/task")
        self.assertEqual(status, HTTPStatus.OK)
        self.assertTrue(task["data"]["validity"]["valid"])

        status, created, _ = self.request(
            "POST", "/v1/sessions", {"model": "http-integration"}
        )
        self.assertEqual(status, HTTPStatus.CREATED)
        session_id = created["data"]["id"]

        actions = TaskSpec.load(TASK_PATH).oracle
        status, executed, _ = self.request(
            "POST",
            f"/v1/sessions/{session_id}/actions",
            {"actions": actions},
        )
        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(executed["data"]["completed"], len(actions))

        status, grade, _ = self.request(
            "POST", f"/v1/sessions/{session_id}/grade", {}
        )
        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(grade["data"]["verdict"], "PASS")

        status, evidence, _ = self.request(
            "GET", f"/v1/sessions/{session_id}/evidence"
        )
        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(evidence["data"]["verdict"], "PASS")
        self.assertTrue(evidence["data"]["world_diff"])

    def test_bounded_and_honest_errors(self) -> None:
        status, missing, _ = self.request("GET", "/v1/sessions/not-a-session")
        self.assertEqual(status, HTTPStatus.NOT_FOUND)
        self.assertEqual(missing["error"]["code"], "session_not_found")
        self.assertNotIn("Traceback", json.dumps(missing))

        request = urllib.request.Request(
            self.base + "/v1/sessions",
            data=b"{" + (b"x" * 5000) + b"}",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(urllib.error.HTTPError) as raised:
            urllib.request.urlopen(request, timeout=3)
        self.assertEqual(raised.exception.code, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        raised.exception.close()


if __name__ == "__main__":
    unittest.main()
