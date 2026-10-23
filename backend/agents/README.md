# RecallScope agents

Phase 5 uses a small explicit state machine rather than adding LangGraph. Each
run selects one provider and uses that same provider/model for every reasoning
role. If a provider becomes unavailable, all partial reasoning is discarded and
the complete run restarts on the next configured provider.

Priority order:

1. Groq — `openai/gpt-oss-120b`
2. Gemini — `gemini-3.8-flash` by default, configurable
3. OpenRouter — `deepseek/deepseek-v4-flash-0731:free`
4. deterministic mock — always labeled in run provenance

Configure provider-specific keys without committing an `.env` file:

```bash
export GROQ_API_KEY=...
export GEMINI_API_KEY=...
export OPENROUTER_API_KEY=...
```

Model IDs can be overridden with `GROQ_MODEL`, `GEMINI_MODEL`, and
`OPENROUTER_MODEL`. The generic `LLM_PROVIDER`, `LLM_MODEL`, and `LLM_API_KEY`
variables are also supported when explicitly forcing one primary provider.
Set `LLM_PROVIDER=mock` for deterministic offline operation.

The Reviewer request is constructed from an immutable incident and raw trace
snapshot through a separate code path. It never receives Investigator output.
Only after both assessments commit does the Arbiter receive them. A requested
Investigator correction can occur once; the Reviewer remains committed.

`PersonBTraceAdapter` matches the deterministic trace-tool surface without
importing or modifying Person B-owned modules. `FakeTraceTools` keeps all three
scenarios runnable until their manifests are merged.

Run the Phase 5 tests from the repository root:

```bash
python3 -m pip install -r backend/agents/requirements.txt
python3 -m unittest discover -s backend/agents/tests -v
```
