# TERRARIUM product and UX research

Reviewed 2026-07-24 against agent observability tools, scientific data
explorers, laboratory systems, and accessible interaction guidance. The goal
was not to imitate a competitor. It was to find the right interaction model
for a sealed, resettable world.

## Primary-source review

| Product or guidance | Relevant pattern | What TERRARIUM adopts |
| --- | --- | --- |
| [NASA Eyes](https://science.nasa.gov/eyes/) | Immersive real-data worlds make complex systems explorable instead of reducing them to a table. Time can be advanced or rewound while the system remains the primary visual object. | The world is a glass habitat, not dashboard chrome. Replay progress visibly changes the habitat. |
| [CZ CELLxGENE Explorer](https://cellxgene.cziscience.com/docs/04__Analyze%20Public%20Data/4_1__Hosted%20Tutorials) | A scientific specimen occupies the center; metadata and features flank it. Users select and subset cells while retaining the overall context. | The live chamber stays central, with evolving world state and criteria beside it. Recorded cultures are selectable without losing the controlled-world context. |
| [napari layers](https://napari.org/stable/howtos/layers/index.html) | Different scientific data types become distinct viewable layers with controls appropriate to each layer. | Environment, agent, app activity, world mutation, and evaluation are visually distinct evidence layers. |
| [Benchling Registry](https://www.benchling.com/registry) | Structured entities retain lineage, linked experimental context, and uniqueness rules. | A run is presented as a specimen with identity, seed, cost, latency, criteria, trace lineage, and state mutation—not an anonymous score. |
| [Benchling Inventory](https://www.benchling.com/inventory) | The interface creates a digital window into a physical lab and preserves sample history and location. | Containment, reset provenance, and world identity appear before performance metrics. |
| [Browserbase Observability](https://docs.browserbase.com/platform/browser/observability/observability) | Session replay, events, metadata, logs, and detailed payloads stay in one debugging context. | The observatory links start/pause/step/reset controls to the current tool event, state changes, criteria, and full payload trace. |
| [Observable Plot marks](https://observablehq.com/plot/features/marks) and [facets](https://observablehq.com/plot/features/facets) | Layered marks encode data in a documented visual vocabulary; small multiples make controlled comparison direct. | The landing evidence uses explicitly labeled marks, while the specimen rack repeats one evidence structure across all three runs. |
| [W3C: Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color) | Status must not rely on color alone. | Pass, fail, pending, and containment states always include text and distinct symbols in addition to color. |

## Competitive conclusion

Conventional agent-observability products are optimized around run lists,
waterfalls, dark panels, and metric cards. Those patterns are useful for
operations, but they make TERRARIUM visually interchangeable with a tracing
tool and hide its most important product idea: the environment itself is the
controlled experimental object.

TERRARIUM therefore uses a **living containment laboratory**:

- warm daylight paper and botanical color instead of a generic dark console;
- a central glass world populated by five app “species”;
- run selection framed as choosing a recorded behavior culture;
- start, pause, step, and reset controls that replay actual vendored events;
- visible agent movement, active app pulses, growth/progress, state mutations,
  live criteria, and an append-only observation sequence;
- specimen sheets that retain full criteria, trace, payload, and world diff;
- editorial scientific typography and sample-lineage labels rather than KPI
  tiles.

## Information architecture

The GitHub Pages site follows the evaluator's reasoning order:

1. **Landing / risk:** why live-service evaluation is unsafe.
2. **Thesis:** reset habitat, observe phenotype, score state.
3. **Evidence:** actual three-run result and trace lineage.
4. **Architecture:** task → exact copy → shared dispatch → evaluation.
5. **Interactive observatory:** replay each deterministic behavior culture.
6. **Specimen rack:** inspect the complete evidence for all runs.
7. **Scope:** separate what the alpha ships from what it does not claim.

The result is deliberately unlike the sibling projects: it is a glass-world
scientific instrument, not a dashboard with a green theme.
