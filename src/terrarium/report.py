from __future__ import annotations

import html
import json
from pathlib import Path

from .models import RunRecord


STYLE = """
:root{
  --bg:#06100d;--panel:#0a1713;--panel-2:#0d1e19;--line:#1d3930;
  --line-strong:#2c5a49;--text:#f3fbf7;--muted:#88a79a;--faint:#597468;
  --mint:#63f5ad;--mint-soft:#173e2d;--coral:#ff817c;--amber:#f5c66c;
  --cyan:#68d9e8;--shadow:0 24px 70px rgba(0,0,0,.36)
}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:
radial-gradient(circle at 78% -10%,rgba(54,164,113,.16),transparent 34rem),
linear-gradient(rgba(99,245,173,.025) 1px,transparent 1px),
linear-gradient(90deg,rgba(99,245,173,.025) 1px,transparent 1px),var(--bg);
background-size:auto,32px 32px,32px 32px;color:var(--text);
font:14px/1.55 Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
a{color:inherit}.topbar{height:58px;border-bottom:1px solid var(--line);display:flex;
align-items:center;justify-content:space-between;padding:0 26px;position:sticky;top:0;
z-index:10;background:rgba(6,16,13,.86);backdrop-filter:blur(16px)}
.brand{display:flex;align-items:center;gap:11px;font-weight:760;letter-spacing:.02em}
.brand-mark{width:26px;height:26px;border:1px solid var(--line-strong);border-radius:7px;
display:grid;place-items:center;color:var(--mint);box-shadow:inset 0 0 0 4px rgba(99,245,173,.04)}
.topmeta{display:flex;align-items:center;gap:10px;color:var(--muted);font:11px/1.2
ui-monospace,SFMono-Regular,Menlo,monospace;text-transform:uppercase;letter-spacing:.1em}
.live{display:flex;align-items:center;gap:7px;color:#b9e8d2}.live:before{content:"";
width:6px;height:6px;border-radius:50%;background:var(--mint);box-shadow:0 0 13px var(--mint)}
main{max-width:1440px;margin:auto;padding:30px 26px 64px}.hero{border:1px solid var(--line);
border-radius:18px;background:linear-gradient(135deg,rgba(16,39,31,.97),rgba(8,23,18,.93));
box-shadow:var(--shadow);overflow:hidden}.hero-main{display:grid;grid-template-columns:minmax(0,1.5fr)
minmax(270px,.7fr);gap:34px;padding:34px}.eyebrow,.section-label{margin:0 0 13px;
color:var(--mint);font:700 11px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace;
letter-spacing:.16em;text-transform:uppercase}.eyebrow:before{content:"";display:inline-block;
width:24px;height:1px;background:currentColor;vertical-align:middle;margin-right:9px}
h1{margin:0;font-size:clamp(34px,5vw,62px);line-height:1;letter-spacing:-.045em;
max-width:820px}h2{font-size:20px;letter-spacing:-.015em}h3{margin:22px 0 9px;
font-size:12px;text-transform:uppercase;letter-spacing:.1em;color:#b9d2c7}
.lede{font-size:16px;color:#b6cdc3;max-width:760px;margin:19px 0 0}.hero-aside{
border-left:1px solid var(--line);padding-left:28px;display:flex;flex-direction:column;
justify-content:space-between}.hash-note{color:var(--muted);font-size:13px}.signal{display:flex;
align-items:center;justify-content:space-between;padding:11px 0;border-bottom:1px solid var(--line)}
.signal strong{font:650 12px ui-monospace,SFMono-Regular,Menlo,monospace}
.signal span{color:var(--muted);font-size:12px}.world-strip{display:flex;gap:8px;flex-wrap:wrap;
padding:15px 34px;border-top:1px solid var(--line);background:rgba(2,10,8,.28)}
.world-chip{border:1px solid var(--line);background:#091511;border-radius:999px;padding:6px 10px;
font:600 10px ui-monospace,SFMono-Regular,Menlo,monospace;color:#9fb9ae;
text-transform:uppercase;letter-spacing:.08em}.summary{display:grid;
grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:18px 0 28px}
.summary-card{background:rgba(10,23,19,.85);border:1px solid var(--line);border-radius:13px;
padding:17px}.summary-card strong{display:block;font-size:25px;line-height:1.2}
.summary-card span{display:block;color:var(--muted);font-size:11px;margin-top:6px;
text-transform:uppercase;letter-spacing:.1em}.comparison-head{display:flex;align-items:end;
justify-content:space-between;gap:20px;margin:0 0 13px}.comparison-head p{margin:0;color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.run-card{
min-width:0;border:1px solid var(--line);border-radius:16px;background:linear-gradient(180deg,
rgba(13,30,25,.98),rgba(8,20,16,.98));overflow:hidden;box-shadow:0 16px 40px rgba(0,0,0,.22)}
.run-head{padding:18px 18px 15px;border-bottom:1px solid var(--line)}.run-title{
display:flex;align-items:center;justify-content:space-between;gap:12px}.run-title h2{margin:0;
font-size:18px}.status{display:inline-flex;align-items:center;gap:6px;border-radius:999px;
padding:5px 8px;font:750 10px ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.08em}
.status:before{content:"";width:5px;height:5px;border-radius:50%;background:currentColor}
.pass{color:var(--mint);background:var(--mint-soft)}.fail{color:var(--coral);
background:#3c1c1d}.undetermined{color:var(--amber);background:#3b2f15}.run-meta{
display:grid;grid-template-columns:1fr 1fr;gap:6px 14px;margin-top:14px;color:var(--muted);
font:11px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace}.run-body{padding:0 18px 18px}
.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:10px}table{
border-collapse:collapse;width:100%;font-size:12px}td,th{border-bottom:1px solid var(--line);
padding:9px 10px;text-align:left;vertical-align:top}tr:last-child td{border-bottom:0}
th{color:var(--faint);font:700 9px ui-monospace,SFMono-Regular,Menlo,monospace;
text-transform:uppercase;letter-spacing:.1em;background:rgba(5,14,11,.72)}
.timeline{list-style:none;margin:0;padding:0;border:1px solid var(--line);border-radius:10px;
overflow:hidden}.timeline li{display:grid;grid-template-columns:28px 62px minmax(0,1fr);gap:8px;
padding:8px 10px;border-bottom:1px solid var(--line);font:11px/1.45
ui-monospace,SFMono-Regular,Menlo,monospace}.timeline li:last-child{border-bottom:0}
.seq{color:var(--faint)}.event-kind{color:var(--cyan)}.event-payload{color:#a9c2b7;
white-space:pre-wrap;overflow-wrap:anywhere}.codebox{margin:0;padding:12px;border:1px solid var(--line);
border-radius:10px;background:#050d0a;color:#a9c2b7;white-space:pre-wrap;overflow-wrap:anywhere;
font:11px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace;max-height:260px;overflow:auto}
.footer{display:flex;justify-content:space-between;gap:20px;border-top:1px solid var(--line);
margin-top:28px;padding-top:18px;color:var(--muted);font-size:12px}.footer strong{color:#b8d1c6}
@media(max-width:1050px){.grid{grid-template-columns:1fr}.hero-main{grid-template-columns:1fr}
.hero-aside{border-left:0;border-top:1px solid var(--line);padding:24px 0 0}}
@media(max-width:720px){.topbar{padding:0 15px}.topmeta span:not(.live){display:none}
main{padding:18px 14px 44px}.hero-main{padding:24px 20px}.world-strip{padding:14px 20px}
.summary{grid-template-columns:1fr 1fr}.comparison-head{align-items:start;flex-direction:column}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
"""


def _run_card(run: RunRecord) -> str:
    eval_rows = "".join(
        "<tr>"
        f"<td>{html.escape(item.criterion_id)}</td>"
        f"<td>{html.escape(item.family)}</td>"
        f"<td><span class='status {item.verdict.lower()}'>{item.verdict}</span></td>"
        f"<td>{html.escape(item.detail)}</td>"
        "</tr>"
        for item in run.evaluations
    )
    timeline = "".join(
        "<li>"
        f"<span class='seq'>{event.seq:02d}</span>"
        f"<span class='event-kind'>{html.escape(event.kind)}</span>"
        f"<span class='event-payload'>{html.escape(event.app)}."
        f"{html.escape(event.operation)} · "
        f"{html.escape(json.dumps(event.payload, sort_keys=True))}</span>"
        "</li>"
        for event in run.trace
    )
    diff = json.dumps(run.world_diff, indent=2, sort_keys=True)
    return f"""
    <article class="run-card">
      <header class="run-head">
        <div class="run-title"><h2>{html.escape(run.model)}</h2>
        <span class="status {run.verdict.lower()}">{run.verdict}</span></div>
        <div class="run-meta">
          <span>run · {html.escape(run.run_id)}</span><span>seed · {run.seed}</span>
          <span>cost · ${run.cost_usd:.2f}</span><span>latency · {run.latency_ms} ms</span>
        </div>
      </header>
      <div class="run-body">
      <h3>Criteria</h3>
      <div class="table-wrap"><table><thead><tr><th>ID</th><th>family</th>
      <th>verdict</th><th>evidence</th></tr></thead><tbody>{eval_rows}</tbody></table></div>
      <h3>Tool trace</h3><ol class="timeline">{timeline}</ol>
      <h3>World diff</h3><pre class="codebox">{html.escape(diff)}</pre>
      </div>
    </article>
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
    pass_count = sum(run.verdict == "PASS" for run in runs)
    fail_count = sum(run.verdict == "FAIL" for run in runs)
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{html.escape(title)}</title><style>{STYLE}</style></head>
<body><header class="topbar"><div class="brand"><span class="brand-mark">T</span>
TERRARIUM</div><div class="topmeta"><span>sealed workspace</span>
<span class="live">replay verified</span></div></header><main>
<section class="hero"><div class="hero-main"><div>
<p class="eyebrow">Controlled agent evaluation</p><h1>{html.escape(title)}</h1>
<p class="lede">{html.escape(comparison_note)} Every tool call, criterion, and
state transition below comes from a deterministic, keyless replay.</p></div>
<aside class="hero-aside"><div><p class="section-label">Validity envelope</p>
<div class="signal"><span>World reset</span><strong>EXACT COPY</strong></div>
<div class="signal"><span>Network</span><strong>SEALED</strong></div>
<div class="signal"><span>Grader</span><strong>DETERMINISTIC</strong></div></div>
<p class="hash-note">All comparable runs pin one task, world, and grader hash.</p>
</aside></div><div class="world-strip">
<span class="world-chip">email</span><span class="world-chip">calendar</span>
<span class="world-chip">files</span><span class="world-chip">chat</span>
<span class="world-chip">crm + ledger</span></div></section>
<section class="summary" aria-label="Comparison summary">
<div class="summary-card"><strong>{len(runs)}</strong><span>controlled runs</span></div>
<div class="summary-card"><strong>{pass_count}</strong><span>passing agents</span></div>
<div class="summary-card"><strong>{fail_count}</strong><span>failed agents</span></div>
<div class="summary-card"><strong>{rate:.1%}</strong><span>abstention rate</span></div>
</section><div class="comparison-head"><div><p class="section-label">Run matrix</p>
<h2>Same world. Different behavior.</h2></div><p>Inspect criteria, trace, then state.</p></div>
<section class="grid">{''.join(_run_card(run) for run in runs)}</section>
<footer class="footer"><span><strong>Evidence source</strong> · vendored run bundles</span>
<span>Generated deterministically by <strong>make demo</strong></span></footer>
</main></body></html>"""
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(document, encoding="utf-8")
    return destination
