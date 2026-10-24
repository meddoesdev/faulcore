# RecallScope agents

Phase 5 uses a small explicit state machine rather than adding LangGraph. Each
run selects one provider and uses that same provider/model for every reasoning
role. If a provider becomes unavailable, all partial reasoning is discarded and
the complete run restarts on the next configured provider.

Priority order:

1. Groq — `openai/gpt-oss-120b`
2. Gemini — `gemini-3.8-flash` by default, configurable
3. OpenRouter — `xingchen-agi/xing4.0-29b-a4b:free`
4. deterministic mock — always labeled in run provenance

Copy the root template to a local ignored file, then add the three keys there:

```bash
cp .env.example .env
```

The backend loads the root `.env` without overriding variables already set by
the process. Never commit `.env` or paste keys into run requests or logs.

Model IDs can be overridden with `GROQ_MODEL`, `GEMINI_MODEL`, and
`OPENROUTER_MODEL`. The generic `LLM_PROVIDER`, `LLM_MODEL`, and `LLM_API_KEY`
variables are also supported when explicitly forcing one primary provider.
Set `LLM_PROVIDER=mock` for deterministic offline operation.

The originally selected `deepseek/deepseek-v4-flash-0731:free` endpoint was
withdrawn by OpenRouter. The default now uses a fixed, currently free model
with advertised structured-output support, preserving the same-model-per-run
rule. Override `OPENROUTER_MODEL` when a better free endpoint becomes available.

Validate every configured credential with a minimal structured-output request:

```bash
python -m backend.agents.smoke_providers
```

This prints provider names, model IDs, and pass/fail status only. It never
prints keys or response content.

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
