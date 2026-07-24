# TERRARIUM v0.1 limits

- The five apps are API-level simulations with a deliberately compact
  operation set. They do not reproduce pixels, browser behavior, OAuth,
  provider rate limits, or every failure mode of real services.
- The bundled "model" runs are recorded labels over deterministic scripted
  actions. They demonstrate replay and comparison, not live model quality.
- The reference driver executes an explicit action plan. A live LiteLLM
  client and Gemini/Groq/Ollama/Claude framework integrations remain external
  work because they require dependencies, credentials, and provider testing.
- The stdio server is MCP-shaped (`tools/list`, `tools/call`) but does not
  implement the complete MCP initialization/capability/transport protocol.
- The task file is JSON syntax saved as `.yaml`. JSON is a valid YAML 1.2
  subset, allowing a zero-dependency safe loader; general YAML syntax is not
  accepted.
- LLM-judge criteria always return `UNDETERMINED` in keyless mode and are
  never silently mixed into deterministic pass counts. The bundled demo has
  no judge criteria, so its abstention rate is 0%; the engine reports the
  rate for every run.
- Provider-level temp-0 trajectory stability, a 12-task/four-live-model
  comparison, two external MCP framework integrations, and the HF Space
  gallery have not been measured or launched. The static Pages-ready report
  is the hosted-demo artifact available locally.
- This sandbox is a staging signal, not evidence that an agent is safe on
  real accounts.

