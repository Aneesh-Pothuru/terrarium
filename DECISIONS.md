# Decisions

## 2026-07-24 — Standard-library, keyless core

The implementation uses Python's standard library so clone-to-demo does not
depend on package indexes. Live model clients remain an explicit boundary.

## 2026-07-24 — JSON-compatible YAML

Task files use the JSON subset of YAML 1.2. This keeps parsing deterministic
and safe without PyYAML while preserving the specified `.yaml` artifact.

## 2026-07-24 — Five app modules in v0.1

The brief's milestone table deferred calendar/chat while its P0 table required
all five apps. P0 wins: email, calendar, files, chat, and CRM-lite with ledger
all ship here. Their operation sets are compact rather than the aspirational
8–15 operations per app; the shortfall is declared in LIMITS.

## 2026-07-24 — Honest MCP-shaped boundary

The stdio service uses MCP's `tools/list` and `tools/call` shapes through the
same dispatcher as the in-process driver. It is labeled MCP-shaped until it
passes conformance testing against the official SDK and two external clients.

## 2026-07-24 — Three, six, and twelve task counts

Journey 0 means three recorded runs. Six tasks are the broader v0.1 milestone
target and twelve are the launch suite target. This compact implementation
ships the exact three-run Journey 0 and one fully validated task; it does not
claim the six- or twelve-task milestones.

