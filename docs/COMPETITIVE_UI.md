# Competitive UI review

Reviewed 2026-07-24 against the closest production interfaces, focusing on
interaction patterns rather than visual imitation.

| Product | Relevant surface | What works |
| --- | --- | --- |
| [LangSmith](https://www.langchain.com/langsmith/observability) | agent traces and evaluation | A run-first information hierarchy, nested execution detail, and cost/latency beside quality signals. |
| [Browserbase](https://docs.browserbase.com/platform/browser/observability/observability) | session inspector and replay | The replay is the primary object; logs, live state, and recordings remain in one debugging context. |
| [Braintrust](https://www.braintrust.dev/learn/ai-agent-evaluation/v0) | agent evaluation | Comparison leads to the exact failing step instead of stopping at an aggregate score. |
| [Arize Phoenix](https://arize.com/docs/phoenix/) | traces, datasets, and experiments | One consistent path from overview metrics to a selected trace and its evidence. |

## Direction adopted

- Make the controlled world and comparison validity visible before any score.
- Use a three-column run comparison with a persistent trace/evidence hierarchy.
- Treat hashes, seed, cost, latency, and abstention as first-class provenance.
- Use emerald only for verified evidence; failures and undetermined results have
  separate, accessible semantic colors.
- Preserve the full deterministic payload instead of replacing it with a
  decorative chart.

The result is a sealed-world inspector, not a generic analytics dashboard.
