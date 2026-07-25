# TERRARIUM local service API

The installed service exposes the real deterministic `World.call()` and
evaluation path over HTTP. It is a local integration surface, not a hosted
multi-tenant control plane.

## Start

```bash
terrarium service \
  --task examples/tasks/inbox-triage.yaml \
  --data-dir work/service
```

The default bind is `127.0.0.1:8700`. A non-loopback bind is refused unless
`--allow-remote` is present. The server has no built-in authentication or TLS;
put it behind an authenticated gateway before exposing it to a network.

Environment equivalents are available for `TERRARIUM_HOST`,
`TERRARIUM_PORT`, `TERRARIUM_DATA_DIR`, `TERRARIUM_MAX_BODY_BYTES`,
`TERRARIUM_MAX_ACTIONS`, `TERRARIUM_MAX_SESSIONS`, and
`TERRARIUM_CORS_ORIGIN`.

## Contract

Every JSON response includes `request_id`; callers may supply a safe
`X-Request-ID`. Errors use:

```json
{
  "request_id": "01J...",
  "error": {
    "code": "action_failed",
    "message": "'missing.tool'",
    "details": {
      "index": 1,
      "completed": 1,
      "partial_side_effects": true
    }
  }
}
```

Batch actions are deliberately not transactional. Each app operation commits
and is traced as it occurs, matching a real tool-using agent. If action 2
fails after action 1 succeeds, the response says that partial side effects
exist and the timeline retains both the completed call and the error.

### Operations

| Method | Route | Result |
|---|---|---|
| `GET` | `/healthz` | Process liveness |
| `GET` | `/readyz` | Writable store, readable snapshot, valid task |
| `GET` | `/v1/task` | Instruction, hashes, and cached validity result |
| `POST` | `/v1/task/validate` | Oracle/null/mutation validity evidence |
| `GET` | `/v1/tools` | Tool definitions and input schemas |
| `POST` | `/v1/sessions` | Create an exact world copy |
| `GET` | `/v1/sessions` | List restart-safe sessions |
| `GET` | `/v1/sessions/{id}` | Session provenance and trace count |
| `POST` | `/v1/sessions/{id}/reset` | Replace the world with the exact base snapshot |
| `POST` | `/v1/sessions/{id}/tools/call` | Invoke one simulated app tool |
| `POST` | `/v1/sessions/{id}/actions` | Invoke a bounded action sequence |
| `GET` | `/v1/sessions/{id}/state` | Current tables |
| `GET` | `/v1/sessions/{id}/timeline` | Append-only tool/read/write/error events |
| `POST` | `/v1/sessions/{id}/grade` | Deterministic verdict, criteria, and world diff |
| `GET` | `/v1/sessions/{id}/evidence` | Complete serializable `RunRecord` |
| `POST` | `/v1/runs` | Create, execute, and return one run in one request |

Create and execute the bundled oracle-shaped example:

```bash
session_id="$(
  curl -fsS -X POST http://127.0.0.1:8700/v1/sessions \
    -H 'content-type: application/json' \
    -d '{"model":"my-agent"}' |
  python -c 'import json,sys; print(json.load(sys.stdin)["data"]["id"])'
)"

curl -fsS -X POST \
  "http://127.0.0.1:8700/v1/sessions/${session_id}/actions" \
  -H 'content-type: application/json' \
  --data-binary @- <<'JSON'
{"actions":[
  {"tool":"email.search","arguments":{"query":"Refund request R-104"}},
  {"tool":"files.read","arguments":{"path":"policies/refunds.txt"}},
  {"tool":"crm.update_contact","arguments":{"contact_id":1,"status":"triaged","note":"Policy checked; refund is under $500."}},
  {"tool":"email.send","arguments":{"to":"maya@example.test","subject":"Refund R-104 triaged","body":"Your request is within the support policy and has been triaged."}}
]}
JSON

curl -fsS -X POST \
  "http://127.0.0.1:8700/v1/sessions/${session_id}/grade"
```

## Persistence and containment

- The task fixture becomes a content-addressed base SQLite snapshot.
- Each session receives its own exact copy and metadata file.
- Session state, trace, and provenance survive process restarts.
- Reset replaces only that session database with the pristine snapshot.
- Request bodies default to 64 KiB; action batches default to 100 and stored
  sessions to 1,000. These are operational bounds, not tenant quotas.
- The service makes no provider or model calls. An external agent drives the
  tools and is responsible for model credentials, token budgets, and retries.

## Container

```bash
docker compose up --build
curl -fsS http://127.0.0.1:8700/readyz
```

Compose publishes only on loopback, persists `/data`, drops Linux
capabilities, uses a read-only root filesystem, and runs as a non-root user.
