(() => {
  "use strict";

  const source = document.querySelector("#run-data");
  const select = document.querySelector("#scenario-select");
  if (!source || !select) return;

  const runs = JSON.parse(source.textContent);
  const names = {
    "inbox-triage-flash": "Policy-grounded triage · compact path",
    "inbox-triage-oss": "Policy-grounded triage · alternate order",
    "inbox-triage-failure": "Containment drill · skipped safeguards",
  };
  const descriptions = {
    "inbox-triage-flash": "reads policy → updates CRM → sends reply",
    "inbox-triage-oss": "reads policy → sends reply → updates CRM",
    "inbox-triage-failure": "searches email → sends reply without grounding",
  };
  const state = { index: 0, cursor: 0, timer: null };
  const elements = {
    start: document.querySelector("#start-run"),
    pause: document.querySelector("#pause-run"),
    step: document.querySelector("#step-run"),
    reset: document.querySelector("#reset-run"),
    model: document.querySelector("#sim-model"),
    details: document.querySelector("#sim-details"),
    verdict: document.querySelector("#sim-verdict"),
    chamber: document.querySelector("#simulation-chamber"),
    agent: document.querySelector("#sim-agent"),
    readout: document.querySelector("#event-readout"),
    progress: document.querySelector("#event-progress"),
    count: document.querySelector("#event-count"),
    track: document.querySelector("#event-track"),
    log: document.querySelector("#activity-log"),
  };

  function currentRun() {
    return runs[state.index];
  }

  function setState(name, value, observed = false) {
    const row = document.querySelector(`[data-state="${name}"]`);
    if (!row) return;
    row.querySelector("dd").textContent = value;
    row.classList.toggle("observed", observed);
  }

  function setCriterion(id, value, kind = "waiting") {
    const row = document.querySelector(`[data-criterion="${id}"]`);
    if (!row) return;
    const indicator = row.querySelector(".criterion-state");
    indicator.textContent = value;
    indicator.className = `criterion-state ${kind}`;
  }

  function pause() {
    if (state.timer !== null) {
      window.clearInterval(state.timer);
      state.timer = null;
    }
    elements.start.disabled = state.cursor >= currentRun().trace.length;
    elements.pause.disabled = true;
    elements.step.disabled = state.cursor >= currentRun().trace.length;
  }

  function buildTrack(length) {
    elements.track.replaceChildren();
    for (let index = 0; index < length; index += 1) {
      const marker = document.createElement("span");
      marker.className = "track-mark";
      elements.track.append(marker);
    }
  }

  function reset() {
    pause();
    state.cursor = 0;
    const run = currentRun();
    elements.model.textContent = run.model;
    elements.details.textContent =
      `${descriptions[run.run_id] || "recorded deterministic behavior"} · ` +
      `seed ${run.seed} · ${run.latency_ms} ms`;
    elements.verdict.textContent = "READY";
    elements.verdict.className = "sim-verdict";
    elements.progress.max = Math.max(1, run.trace.length);
    elements.progress.value = 0;
    elements.count.textContent = `0 / ${run.trace.length}`;
    elements.chamber.style.setProperty("--growth", "0");
    elements.agent.className = "sim-agent";
    document.querySelectorAll(".sim-app").forEach((node) => {
      node.classList.remove("active");
    });
    setState("ticket", "present");
    setState("policy", "unread");
    setState("crm", "open");
    setState("reply", "unsent");
    setCriterion("reply-sent", "waiting");
    setCriterion("crm-triaged", "waiting");
    setCriterion("policy-read", "waiting");
    elements.readout.textContent =
      "Chamber reset. Start or step to introduce the agent.";
    elements.readout.classList.add("idle");
    elements.log.replaceChildren();
    const empty = document.createElement("li");
    empty.className = "empty";
    empty.textContent = "No activity observed yet.";
    elements.log.append(empty);
    buildTrack(run.trace.length);
    elements.start.disabled = false;
    elements.pause.disabled = true;
    elements.step.disabled = false;
  }

  function applyObservation(event) {
    if (
      event.kind === "read" &&
      event.app === "email" &&
      event.operation === "search"
    ) {
      setState("ticket", "located", true);
    }
    if (
      event.kind === "read" &&
      event.app === "files" &&
      event.operation === "read"
    ) {
      setState("policy", "read", true);
      setCriterion("policy-read", "observed", "pass");
    }
    if (
      event.kind === "write" &&
      event.app === "crm" &&
      event.operation === "update_contact"
    ) {
      setState("crm", "triaged", true);
      setCriterion("crm-triaged", "observed", "pass");
    }
    if (
      event.kind === "write" &&
      event.app === "email" &&
      event.operation === "send"
    ) {
      setState("reply", "sent", true);
      setCriterion("reply-sent", "observed", "pass");
    }
  }

  function appendActivity(event) {
    elements.log.querySelector(".empty")?.remove();
    const item = document.createElement("li");
    const number = document.createElement("span");
    const kind = document.createElement("strong");
    const payload = document.createElement("code");
    number.textContent = String(event.seq).padStart(2, "0");
    kind.textContent = event.kind;
    payload.textContent =
      `${event.app}.${event.operation} · ${JSON.stringify(event.payload)}`;
    item.append(number, kind, payload);
    elements.log.append(item);
    item.scrollIntoView({ block: "nearest" });
  }

  function finish() {
    pause();
    const run = currentRun();
    elements.verdict.textContent = run.verdict;
    elements.verdict.className =
      `sim-verdict status ${run.verdict.toLowerCase()}`;
    run.evaluations.forEach((evaluation) => {
      const kind = evaluation.verdict.toLowerCase();
      setCriterion(
        evaluation.criterion_id,
        evaluation.verdict,
        kind,
      );
    });
    elements.readout.textContent =
      `${run.verdict} · culture complete · ${run.evaluations.length} criteria scored`;
    elements.readout.classList.remove("idle");
  }

  function step() {
    const run = currentRun();
    if (state.cursor >= run.trace.length) {
      finish();
      return;
    }
    const event = run.trace[state.cursor];
    document.querySelectorAll(".sim-app").forEach((node) => {
      node.classList.toggle("active", node.dataset.app === event.app);
    });
    elements.agent.className = `sim-agent at-${event.app}`;
    applyObservation(event);
    appendActivity(event);
    elements.readout.textContent =
      `${String(event.seq).padStart(2, "0")} · ${event.kind.toUpperCase()} · ` +
      `${event.app}.${event.operation}`;
    elements.readout.classList.remove("idle");
    state.cursor += 1;
    const percent = Math.round((state.cursor / run.trace.length) * 100);
    elements.progress.value = state.cursor;
    elements.count.textContent = `${state.cursor} / ${run.trace.length}`;
    elements.chamber.style.setProperty("--growth", String(percent / 100));
    [...elements.track.children].forEach((marker, index) => {
      marker.classList.toggle("complete", index < state.cursor);
      marker.classList.toggle("current", index === state.cursor);
    });
    if (state.cursor >= run.trace.length) finish();
  }

  function start() {
    if (state.cursor >= currentRun().trace.length) reset();
    if (state.timer !== null) return;
    step();
    if (state.cursor < currentRun().trace.length) {
      state.timer = window.setInterval(step, 820);
      elements.start.disabled = true;
      elements.pause.disabled = false;
      elements.step.disabled = true;
    }
  }

  select.replaceChildren();
  runs.forEach((run, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = names[run.run_id] || run.model;
    select.append(option);
  });
  select.addEventListener("change", () => {
    state.index = Number(select.value);
    reset();
  });
  elements.start.addEventListener("click", start);
  elements.pause.addEventListener("click", pause);
  elements.step.addEventListener("click", step);
  elements.reset.addEventListener("click", reset);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) pause();
  });
  reset();
})();
