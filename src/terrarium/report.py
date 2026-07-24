from __future__ import annotations

import html
import json
from pathlib import Path

from .models import RunRecord


STYLE = """
body{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;background:#07130f;color:#dff7e9;margin:0}
main{max-width:1180px;margin:auto;padding:32px}.hero{border:1px solid #2a6b50;background:#0c2018;padding:24px}
h1,h2{color:#8ff0bd}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}
.card{border:1px solid #24503f;background:#0a1a14;padding:16px}.PASS{color:#76e6a7}.FAIL{color:#ff8f8f}
.UNDETERMINED{color:#ffd36e}table{border-collapse:collapse;width:100%;font-size:13px}td,th{border:1px solid #24503f;padding:7px;text-align:left;vertical-align:top}
pre{white-space:pre-wrap;overflow-wrap:anywhere;color:#b9d8c7}.muted{color:#8eac9c}.metric{font-size:28px;color:#fff}
"""


def _run_card(run: RunRecord) -> str:
    eval_rows = "".join(
        "<tr>"
        f"<td>{html.escape(item.criterion_id)}</td>"
        f"<td>{html.escape(item.family)}</td>"
        f"<td class='{item.verdict}'>{item.verdict}</td>"
        f"<td>{html.escape(item.detail)}</td>"
        "</tr>"
        for item in run.evaluations
    )
    timeline = "\n".join(
        f"{event.seq:02d} {event.kind:5} {event.app}.{event.operation} "
        f"{json.dumps(event.payload, sort_keys=True)}"
        for event in run.trace
    )
    diff = json.dumps(run.world_diff, indent=2, sort_keys=True)
    return f"""
    <section class="card">
      <h2>{html.escape(run.model)}</h2>
      <p><span class="metric {run.verdict}">{run.verdict}</span><br>
      <span class="muted">{html.escape(run.run_id)} · seed {run.seed} ·
      ${run.cost_usd:.2f} · {run.latency_ms} ms</span></p>
      <h3>Criteria</h3>
      <table><tr><th>ID</th><th>family</th><th>verdict</th><th>evidence</th></tr>{eval_rows}</table>
      <h3>Timeline</h3><pre>{html.escape(timeline)}</pre>
      <h3>World diff</h3><pre>{html.escape(diff)}</pre>
    </section>
    """


def render_report(runs: list[RunRecord], output: str | Path, title: str) -> Path:
    if not runs:
        raise ValueError("at least one run is required")
    task_hashes = {run.task_hash for run in runs}
    comparison_note = (
        "Identical task/world/grader hash across all runs."
        if len(task_hashes) == 1
        else "Warning: run hashes differ; this is not a controlled comparison."
    )
    abstentions = sum(
        item.verdict == "UNDETERMINED"
        for run in runs
        for item in run.evaluations
    )
    criteria_count = sum(len(run.evaluations) for run in runs)
    rate = abstentions / criteria_count if criteria_count else 0.0
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{html.escape(title)}</title><style>{STYLE}</style></head>
<body><main><section class="hero"><p class="muted">TERRARIUM · SEALED WORLD REPORT</p>
<h1>{html.escape(title)}</h1>
<p>{html.escape(comparison_note)} Replay is keyless and network-free.</p>
<p>Runs <strong>{len(runs)}</strong> · abstention rate <strong>{rate:.1%}</strong></p>
</section><div class="grid">{''.join(_run_card(run) for run in runs)}</div>
<p class="muted">Generated deterministically from vendored run bundles.</p>
</main></body></html>"""
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(document, encoding="utf-8")
    return destination

