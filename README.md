# TERRARIUM

TERRARIUM is a sealed, resettable, fully observable workspace for testing
tool-using agents before they touch real email, calendars, files, chat, CRM,
or payments. This compact v0.1 implements the deterministic and keyless core
with Python's standard library.

## Journey 0

```bash
git clone https://github.com/Aneesh-Pothuru/terrarium
cd terrarium
make demo
```

The command replays three bundled `inbox-triage` runs—two recorded model
labels and one deliberate failure—and writes `docs/demo/index.html`. The
single static page shows tool timelines, before/after state diffs, criterion
results, and a side-by-side comparison. It performs no network calls and
requires no API key.

For an installed checkout, the equivalent command is:

```bash
python -m pip install .
terrarium demo
```

## Other flows

```bash
# Validate oracle/null/per-criterion mutation evidence.
PYTHONPATH=src python -m terrarium task validate examples/tasks/inbox-triage.yaml

# Run the deterministic reference driver and serialize a Run bundle.
PYTHONPATH=src python -m terrarium run \
  --task examples/tasks/inbox-triage.yaml --output work/run.json

# Render or compare recorded bundles without model access.
PYTHONPATH=src python -m terrarium replay work/run.json --output work/replay.html
PYTHONPATH=src python -m terrarium diff \
  examples/recorded/inbox-triage-flash.json \
  examples/recorded/inbox-triage-oss.json --output work/diff.html

# Start the intentionally small MCP-shaped JSON-lines stdio surface.
PYTHONPATH=src python -m terrarium serve \
  --task examples/tasks/inbox-triage.yaml --stdio
```

The stdio surface implements `tools/list` and `tools/call` request shapes. It
is a transparent compatibility seam, not a claim of full MCP protocol
conformance; see [LIMITS.md](LIMITS.md).

## Architecture

```text
TaskSpec + fixture -> content hash -> SQLite snapshot -> exact copied reset
                                             |
                  email/calendar/files/chat/crm+ledger app modules
                                             |
              logged tool calls + reads + writes -> Run/trace bundle
                                             |
          state/trajectory evals -> validity gate -> static replay/diff
```

The app modules and the stdio surface use the same `World.call()` dispatch
path. `schemas/` contains the vendored loopkit contracts; the project never
depends on another deployed service.

## Reproducibility

- `make reproduce-model-comparison` regenerates the Journey-0 HTML and JSON.
- `make reproduce-replay` regenerates a single-run replay.
- `make test` covers snapshot reset, app logging, task hashing, evaluation,
  validity gating, run serialization, replay, diff, and stdio dispatch.
- `make lint` performs dependency-free AST, whitespace, and JSON checks.

The authoritative build brief is copied to [docs/BRIEF.md](docs/BRIEF.md).

