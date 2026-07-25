# TERRARIUM user journeys

These journeys connect the product site to the deterministic observatory. They
describe what a user needs to understand, which controls they use, and what a
credible success or failure state looks like.

## 1. First-time evaluator

**Goal:** understand why a sealed world produces more trustworthy agent
evidence than a live-service test or a final-answer score.

**Landing path**

1. Read **Problem** to see the five-app live exposure surface.
2. Read **Thesis** to understand reset → observe → score.
3. Review the actual three-run **Evidence** before launching the demo.
4. Use **Enter the lab** or **Launch the observatory**.

**Demo actions**

1. Leave `Policy-grounded triage · compact path` selected.
2. Press **Start culture**.
3. Watch the agent move between email, files, CRM, and email.
4. Confirm the world specimen changes from policy `unread` to `read`, CRM
   `open` to `triaged`, and reply `unsent` to `sent`.
5. Expand the matching specimen sheet to inspect criteria, behavior culture,
   and World diff.

**Success state:** the culture finishes `PASS`; all three live criteria resolve
to PASS and the trace explains each state transition.

**Failure or abstention state:** select the containment drill. The reply is
sent, but policy remains unread and CRM remains open. Two criteria resolve to
FAIL. Any future `UNDETERMINED` criterion must remain explicitly labeled
rather than being counted as a pass or silently dropped.

## 2. Benchmark author

**Goal:** decide whether the task and graders create a controlled, violable,
and inspectable benchmark.

**Landing path**

1. Read **Thesis** for the environmental-control contract.
2. Inspect **Architecture** to locate TaskSpec, the SQLite copy, app dispatch,
   and evaluation.
3. Read **Scope** to understand v0.1 boundaries.
4. Follow **Build brief** and the repository from the footer for task and
   fixture details.

**Demo actions**

1. Use **Step** rather than Start.
2. At each event, compare the activity payload with the world specimen.
3. Run all three cultures and confirm the initial world resets identically.
4. Expand **Scored criteria** and **World diff** for every specimen.

**Success state:** the same task hash and seed appear on every specimen; the
oracle path passes, the deliberate mutation path violates individual criteria,
and every claim is backed by trace or state.

**Failure or abstention state:** differing hashes make the report warn that the
comparison is uncontrolled. A criterion that cannot be established should be
`UNDETERMINED`, with its evidence retained for task revision.

## 3. Model researcher comparing runs

**Goal:** identify behavioral differences that aggregate pass rates hide.

**Landing path**

1. Use the **Evidence** chart to establish the outcome difference.
2. Read the trace-lineage explanation for the policy → CRM → reply path.
3. Launch the observatory.

**Demo actions**

1. Replay `compact path`, then **Reset**.
2. Select `alternate order` and replay it.
3. Compare when the reply and CRM updates occur.
4. Select the failure drill and step through the skipped policy and CRM work.
5. Compare latency, trace length, criteria, and state mutations in the specimen
   rack.

**Success state:** both passing cultures reach the same desired state through
different tool orders, and those ordering differences remain inspectable.

**Failure or abstention state:** the failure culture produces a superficially
plausible customer reply but exposes missing grounding and state work. An
abstention remains a first-class outcome for follow-up rather than being
ranked as a model failure without evidence.

## 4. Infrastructure engineer inspecting validity and provenance

**Goal:** verify that the comparison is reproducible, keyless, and isolated
from deployed dependencies.

**Landing path**

1. Confirm the hero proof: deterministic replay, zero API keys, Python standard
   library.
2. Inspect the facts strip and **Architecture**.
3. Review the exact quick-start command.
4. Read **Scope**, the build brief, and source.

**Demo actions**

1. Verify the validity envelope reports exact world copy, sealed network, and
   deterministic grader.
2. Switch cultures and confirm seed, latency, and run identity update.
3. Use **Pause**, **Step**, and **Reset** to test replay control.
4. Inspect the append-only observation sequence and raw payloads.
5. Expand the specimen World diffs and compare them with visible world-state
   changes.

**Success state:** the demo runs from static vendored data, contacts no live
service, starts each culture from the same task/world/grader hash, and exposes
enough provenance to reproduce the report with `make demo`.

**Failure or abstention state:** a hash mismatch produces an explicit
uncontrolled-comparison warning. Missing evidence yields `UNDETERMINED`; it
must never be converted to PASS by UI presentation or aggregation.
