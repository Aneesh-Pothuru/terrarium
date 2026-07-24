# 01 · TERRARIUM

**A sealed world of simulated apps, tools, and connectors. Drop in an
agent and a task; get back a graded report of everything it did. Swap the
model. Author your own tasks with their own eval criteria.**

`terrarium` · Python · MCP tool surface · SQLite worlds · any model

---

## Objective

Give anyone a **safe, resettable, fully observable copy of a real digital
workspace** — email, calendar, files, chat, a CRM, a payments ledger — so
they can answer the three questions that matter before trusting an agent
with real accounts:

1. **Can this agent do this task?** Deploy any agent (or any model behind
   the built-in agent loop) into the world with a task; TERRARIUM records
   every tool call and state change and returns a report with eval
   results.
2. **Which model does it best?** Re-run the identical task with the model
   swapped — same world state, same seed — and diff the runs side by side.
3. **Can I test *my* workflow?** Author a new task in one YAML file:
   the world setup (what's in the inbox, who's in the CRM), the
   instruction, and the eval criteria (what must be true of the world
   afterward). No benchmark team required.

One sentence: **a terrarium is a sealed glass world you can watch —
this one is for agents.**

---

## Why now

- **The pattern is validated but locked inside benchmarks.** AppWorld
  proved the design: 9 simulated apps, 457 APIs, a versioned ~101-table
  database with exact state resets per run — and found GPT-4 completing
  only **48.7%** of task goals and **21.0%** of full scenarios
  ([AppWorld](https://www.emergentmind.com/topics/appworld-benchmark-tasks)).
  τ-bench and τ²-bench did the same for tool-agent-user customer-service
  domains ([tau2-bench](https://github.com/sierra-research/tau2-bench));
  AppWorld-UL just extended it to 516 user-in-the-loop tasks
  ([AppWorld-UL](https://arxiv.org/abs/2607.20536)). But all of these are
  *fixed benchmarks for researchers* — you run their tasks, on their
  worlds, to produce a leaderboard number. Nobody has shipped the
  **authoring tool**: your tasks, your world contents, your eval criteria.
- **Everyone suddenly needs one.** Teams are wiring agents to real email,
  real calendars, real CRMs via MCP connectors. The gap between "demo
  worked once" and "trust it with the inbox" is exactly a sandbox with
  evals — and the current answer is testing in production.
- **Task quality is the known failure mode.** The Agentic Benchmark
  Checklist showed how badly this goes wrong even for professional
  benchmark authors: τ-bench counted empty responses as successes;
  grader defects shift measured performance by up to 100% relative
  ([ABC](https://arxiv.org/abs/2507.02825)). A task-authoring product must
  ship with task-validity checks built in — TERRARIUM does (and SIEVE
  deepens them).
- **MCP makes the tool surface universal.** Exposing the simulated apps
  over MCP means *any* agent — Claude Code, a LangGraph app, a bare
  ReAct loop — can be dropped into the world without adapters.

**The blog post this proves:** "RL Environments Are Products Now" — this
is the product form of that claim: an environment you author, version,
and hand to an agent like a staging server.

---

## Non-goals

- Not a benchmark or leaderboard. TERRARIUM ships *example* tasks, not a
  canonical suite; the product is the authoring and reporting loop.
- Not an agent framework. The built-in ReAct loop is a reference driver,
  deliberately simple; serious users connect their own agent via MCP.
- Not RL training infrastructure in v1. The OpenEnv-compatible
  `reset/step/state` surface exists so trainers *can* use it, but
  training is not the MVP.
- Not a browser/OS sandbox (no pixels, no VMs). Apps are API-level
  simulations — that's what keeps it free, fast, and deterministic.

---

## Personas

| Persona | Cares about |
|---|---|
| **Agent builder** | "Will my agent survive contact with a realistic inbox before I give it the real one?" |
| **Model chooser** | "Flash vs 8B vs Sonnet on *my* workflow — same task, same world, real diff." |
| **Workflow owner** (ops lead, support lead) | "Encode my process as tasks + checks, and test every agent/model against it." |

---

## User journeys

### Journey 0 — the demo (no API key, <10 minutes)

```bash
pipx install terrarium && terrarium demo
```

This replays three bundled recorded runs — `inbox-triage` on two
different models plus one deliberate failure — and opens the report:
a timeline of every tool call, a world-state diff (before/after), eval
results per criterion, and the side-by-side model comparison. No key, no
network. The visitor understands the entire product in one screen.

Hosted version: the same report viewer runs as a free Hugging Face Space
with a gallery of recorded runs — click any task, watch the replay.

### J1 — Deploy an agent on a task and read the report

Maya runs the built-in driver against a bundled task:

```bash
export GEMINI_API_KEY=...   # free tier, no card
terrarium run --task trip-refund --model gemini-2.5-flash
```

TERRARIUM boots a fresh world (SQLite snapshot: 4 apps, seeded inbox,
CRM, ledger), hands the agent the instruction and the MCP tool surface,
and records everything. Ninety seconds later:

```
TASK    trip-refund                     model gemini-2.5-flash
RESULT  3/5 criteria passed

  PASS  refund issued for the correct booking      ($482.10)
  PASS  customer notified by email
  PASS  no other ledger entries modified
  FAIL  CRM case closed with resolution code       (left open)
  FAIL  refund ≤ policy limit                      (policy was $400)

TRAJECTORY  22 tool calls · 2 apps never opened (policy_docs!) · report.html
```

The report shows *why*: the agent never opened the policy app. That's the
product — not a score, a legible account of behavior.

### J2 — Swap the model, diff the runs

```bash
terrarium run --task trip-refund --model llama-3.3-70b   # Groq, free
terrarium diff run_A run_B
```

Same world snapshot, same seed, same user-simulator script. The diff
report aligns the two trajectories: where they diverged (step 7: Flash
searched the inbox, Llama went straight to the ledger), per-criterion
outcomes, tokens, latency, and cost. This is J2 because it's the second
thing everyone does — and it's the whole model-selection story.

### J3 — Author a task with world setup and eval criteria

Maya encodes her team's real workflow:

```yaml
# tasks/vendor-dispute.yaml
world:
  preset: office-small           # email, files, chat, crm, ledger
  seed_data:
    email.inbox: fixtures/dispute_thread.json
    crm.contacts: fixtures/vendors.json
    ledger.entries: fixtures/q3_invoices.json
instruction: >
  A vendor claims invoice #4471 was underpaid. Investigate, decide,
  and take the correct follow-up actions per the payment policy.
user_sim:                        # optional scripted user for multi-turn
  persona: fixtures/vendor_persona.yaml
evals:
  - id: correct-determination
    check: ledger.entry(4471).status == "correctly_paid"
  - id: reply-sent
    check: email.sent.to("billing@vendorco.com").count >= 1
  - id: no-collateral-writes
    check: world.writes.outside(["email", "crm.case:4471"]) == 0
  - id: cites-policy
    check: trajectory.tool_called("files.read", path~"payment_policy*")
```

`terrarium task validate` runs the built-in validity gate before the task
enters her suite: an **oracle solution** she provides must pass (task is
solvable), a **null agent** must score 0 (task is failable — the exact
τ-bench bug), and each criterion must be violable by at least one seeded
mutation. Then `terrarium run --suite mine/` tests any model against her
whole workflow.

### J4 — Connect an external agent over MCP

Dev's team has their own LangGraph agent. Instead of the built-in driver:

```bash
terrarium serve --task vendor-dispute --transport mcp
# their agent connects to localhost:8700 and sees tools:
#   email.search, email.send, files.read, crm.update, ledger.query, ...
terrarium grade --session last
```

The world doesn't care who's driving. Any MCP client gets the same tools,
the same recording, the same report. This is what makes TERRARIUM a
staging environment rather than a benchmark harness.

### End-to-end journey (the product loop)

Author task → validate task (oracle passes, null fails, criteria
violable) → run agent(s) → read report → fix agent or tighten task →
re-run → freeze task+world+grader versions into a suite → run the suite
on every agent/model/prompt change → watch the trend line. The suite
becomes the team's regression harness for agent behavior — the same role
unit tests play for code.

---

## PRD

### P0 — the MVP is not real without these

| ID | Requirement |
|---|---|
| P0-1 | **World engine** — a world is a SQLite database + app modules over it. Boot from a snapshot, exact reset, deterministic given (snapshot, seed). Every read/write logged to the trace. |
| P0-2 | **Five core apps** — email, calendar, files, chat, CRM-lite w/ ledger. Each ~8–15 operations with realistic failure modes (pagination, permission errors, ambiguous search hits). Shared fixture format for seeding. |
| P0-3 | **MCP tool surface** — every app operation exposed as an MCP tool; one `terrarium serve` session per run; also importable in-process for the built-in driver. |
| P0-4 | **Built-in reference driver** — a plain agent loop over any OpenAI-compatible endpoint (LiteLLM): Gemini, Groq, Ollama, Claude. Model swap = flag. |
| P0-5 | **Task format** — YAML: world preset + seed fixtures, instruction, optional scripted user-simulator, eval criteria. Everything content-hashed; a run pins task+world+grader versions. |
| P0-6 | **Eval engine** — three check families: world-state assertions (declarative DSL over final DB), trajectory assertions (tool-call patterns), and optional LLM-judge checks (clearly marked as such in reports). |
| P0-7 | **Task validity gate** — `task validate`: oracle-passes, null-agent-fails, per-criterion violability via seeded mutations. Refuses to add an invalid task to a suite. |
| P0-8 | **Run report** — HTML: trajectory timeline, world diff, per-criterion results, cost/latency/tokens. Plus `diff` across two runs. Reports are static files, hostable on GitHub Pages. |
| P0-9 | **Record/replay** — every run fully serialized; `terrarium replay` renders any recorded run with no model access. This is Journey 0. |

### P1

| ID | Requirement |
|---|---|
| P1-1 | **User simulator** — scripted persona (LLM-driven, seeded) for multi-turn tasks, τ-bench style; its transcript is part of the trace. |
| P1-2 | **Suite runner + trend view** — run N tasks × M models, aggregate report, per-suite history (this is where teams live day-to-day). |
| P1-3 | **World preset library** — `office-small`, `support-desk`, `dev-team` presets plus a fixture generator (seeded synthetic inboxes/CRMs). |
| P1-4 | **App SDK** — a documented interface (`AppModule`: schema, operations, failure injectors) so users add their own simulated connectors. |
| P1-5 | **Chaos knobs** — per-app fault injection: latency, transient errors, stale reads. "Does your agent retry politely" is a real eval. |
| P1-6 | **HF Space demo** — hosted replay gallery + run-on-your-key mode. |

### P2

- OpenEnv-compatible `reset/step/state` wrapper for RL training on tasks.
- Multi-agent worlds: two agents, shared world, conflicting goals.
- Import adapters for AppWorld/τ²-bench tasks so existing suites run under TERRARIUM's reporting.
- Team server mode (shared suite history, auth) on Neon/Supabase.

### Success metrics

| Metric | Target |
|---|---|
| Time from clone to first replayed report | < 10 min, $0, no key |
| Time from clone to first *live* run | < 15 min on a free Gemini key |
| Full demo suite (12 tasks) on free-tier quota | fits in < 300 requests — well under Gemini's ~1,500/day |
| Task authoring: workflow → validated task | < 30 min for a non-author using docs |
| Determinism: identical (task, world, seed, model-with-temp-0) runs | identical trajectories ≥ 95% (report the number honestly — provider nondeterminism exists) |
| External-agent connection (MCP) working against ≥ 2 frameworks | Claude Code + one OSS framework, documented |
| Launch measurement | model-comparison report across ≥ 4 free-tier models on the 12-task demo suite, published with reproduction script |

### Launch-day definition

`terrarium demo` (replay, keyless), `terrarium run` on Gemini/Groq free
keys, `terrarium task validate` gate working, the 12-task demo suite with
published multi-model comparison, HF Space replay gallery live, LIMITS.md
stating what the simulation does not capture (no pixels, no real OAuth,
apps are approximations).

### Risks

| Risk | Mitigation |
|---|---|
| Simulated apps too shallow — agents pass here, fail on real APIs | Realistic failure modes are P0 not polish (pagination, ambiguity, permission errors); chaos knobs in P1; LIMITS.md is explicit that this is a staging tier, not a guarantee |
| Authored tasks are invalid (the ABC failure) | The validity gate is P0 and mandatory; deeper auditing is SIEVE's job (v0.3 integration) |
| LLM-judge checks smuggle unreliability back in | Judge checks are visually flagged in reports, never mixed silently into pass/fail counts, and come with a "verify with SIEVE" note |
| Provider nondeterminism breaks "same seed" claims | Pin temp 0, record provider fingerprints, measure and *publish* replay stability instead of claiming perfection |
| Scope creep toward a browser sandbox | API-level worlds only; a hard non-goal until v2 |

---

## System design

```
 task.yaml ──▶ ┌─────────────┐     ┌──────────────────────────────┐
               │ TASK LOADER │────▶│        WORLD ENGINE           │
 fixtures  ──▶ │ (hash, pin) │     │  SQLite snapshot per run      │
               └─────────────┘     │  ┌───────┐ ┌───────┐ ┌─────┐ │
                                   │  │ email │ │ files │ │ crm │…│
    ┌──────────────┐   MCP/tools   │  └───┬───┘ └───┬───┘ └──┬──┘ │
    │  YOUR AGENT  │◀─────────────▶│      └────┬────┴────────┘    │
    │  (any MCP    │               │      write-ahead trace       │
    │   client)    │               └──────────────┬───────────────┘
    └──────────────┘                              │
    ┌──────────────┐                              ▼
    │ REF DRIVER   │                    ┌──────────────────┐
    │ (LiteLLM ×   │                    │  RUN RECORDER    │──▶ run bundle
    │  any model)  │                    │  (loopkit Run +  │    (jsonl +
    └──────────────┘                    │   trace schema)  │     snapshot)
    ┌──────────────┐                    └────────┬─────────┘
    │ USER SIM     │  scripted persona           │
    └──────────────┘                             ▼
                                       ┌──────────────────┐
                     oracle / null /   │   EVAL ENGINE    │
                     mutation runs ───▶│  state · traj ·  │
                     (validity gate)   │  judge checks    │
                                       └────────┬─────────┘
                                                ▼
                                       ┌──────────────────┐
                                       │ REPORT / REPLAY  │──▶ report.html
                                       │ / DIFF renderer  │    (static)
                                       └──────────────────┘
```

**World = SQLite + app modules.** Each app is a thin, well-tested module
over shared tables (AppWorld validated this shape at ~101 tables/370K
rows; TERRARIUM's presets are 10–20 tables and honest about it). Exact
reset = copy the snapshot file. Full observability = SQLite is trivially
diffable. This choice is also the $0 story: no services, no cloud.

**One tool surface, three drivers.** The MCP server, the in-process
reference driver, and the user simulator all hit the same app-module API,
so a run is identical regardless of who drove it. The reference driver is
deliberately ~200 lines — it is a measurement instrument, not a
framework.

**Eval DSL stays small on purpose.** `app.query(...) == value`,
`trajectory.tool_called(...)`, counts, and ranges. Anything beyond that
is an escape hatch to a Python check function — versioned and hashed like
everything else. Resist a rich DSL; the ABC lesson is that clever graders
are wrong graders.

**Validity gate is the moat.** Solvable (oracle), failable (null agent),
violable (each criterion flips under its seeded mutation). Cheap,
mechanical, and it prevents the exact failure class that embarrassed
τ-bench. SIEVE (v0.3) adds the deep audit: grader FP/FN measurement
against deliberately-wrong trajectories.

### Interfaces

- **→ SIEVE** — TERRARIUM tasks/suites are SIEVE's primary audit target;
  shared verdict vocabulary (`TASK_UNSOLVABLE`, `GRADER_FP`, …).
- **→ ASSAY** — run bundles are scoreable by ASSAY; suite trends can be
  gated in CI.
- **→ BATON** — a BATON routine can run a TERRARIUM suite nightly (v0.3).
- **loopkit** — vendored `Run`/trace schemas from day one.

### Milestones

| | Scope |
|---|---|
| **v0.1** | World engine, email+files+crm apps, reference driver, task format, state+trajectory evals, validity gate, report + replay, 6 demo tasks. **Journey 0 works.** |
| **v0.2** | Calendar+chat apps, MCP serve mode, diff view, user simulator, 12-task suite, suite runner. |
| **v0.3** | App SDK, chaos knobs, HF Space, SIEVE integration, published multi-model comparison. **Launch.** |
| **v1.0** | Preset library, trend views, OpenEnv wrapper, import adapters. |

### Stack & free tier

Python 3.12 · SQLite worlds (no DB service) · MCP Python SDK · LiteLLM
(Gemini free 1,500 req/day → Groq → Ollama local) · Jinja static reports
· HF Space (free CPU) for the replay gallery · GitHub Pages for report
hosting · GitHub Actions (free) for the suite-in-CI recipe. Total
required spend: **$0**.
