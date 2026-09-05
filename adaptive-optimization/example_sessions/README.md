# Example sessions

Synthetic observability data for six agent archetypes, shaped exactly like what the
GenAI Engine stores after OTLP ingestion.

## Layout

```
example_sessions/
├── _generate.py              # regenerates everything (deterministic, seeded)
├── customer_support/         # session_01.json … session_05.json
├── knowledge_qa/
├── coding_agent/
├── financial_analyst/
├── clinical_documentation/
└── revenue_agent/
```

30 sessions · 54 traces · 223 spans.

## File format

Each `session_NN.json` is one session:

```jsonc
{
  "session_id": "sess_billing_01_a3f2",     // the OTel session.id on every span
  "user_id": "user-42",
  "task_id": "<uuid>",                       // Arthur task
  "agent_kind": "revenue_agent",
  "scenario": "one-line description of what makes this session interesting",
  "resource_attributes": { "service.name": "...", "arthur.task": "<uuid>" },
  "trace_count": 1,
  "span_count": 6,
  "traces": [
    { "trace_id": "<32 hex>", "root_span_id": "<16 hex>", "spans": [ /* … */ ] }
  ]
}
```

Every object in `spans` is a **normalized span** — byte-for-byte what lands in
`DatabaseSpan.raw_data`, including the `arthur_span_version: "arthur_span_v1"` marker
the ingestion service stamps on. Spans are a flat list per trace; rebuild the tree from
`parentSpanId` (the root span has none).

These are *not* OTLP protobuf payloads. To exercise the ingestion path itself, re-flatten
the attributes back into OTLP `KeyValue` form — `_generate.py` builds them that way
before normalizing, so the inverse is a small edit to that script.

## The six kinds

| Directory | Agent | Session = | Trace = | Notable spans |
|---|---|---|---|---|
| `customer_support` | Retail support bot | one chat thread | one turn | AGENT → LLM / TOOL / RETRIEVER |
| `knowledge_qa` | RAG over internal policy docs | a research sitting | one question | CHAIN → RETRIEVER → LLM |
| `coding_agent` | PR review + repair | a work block | one task (long) | AGENT → 7–13 TOOL/LLM spans |
| `financial_analyst` | Equity research copilot | the audit unit | one analysis | AGENT → RETRIEVER (filings) + TOOL (market data) |
| `clinical_documentation` | Ambient clinical scribe | a clinician's shift | one encounter | CHAIN → TOOL (EHR) → LLM |
| `revenue_agent` | Router in front of specialists | a deal/ticket | one turn | **CHAIN router as root** → AGENT specialist |

## What's deliberately varied

The sessions aren't uniform happy paths — they carry the failure modes worth detecting:

- **9 error spans** across tool timeouts, a 503 from a market-data provider, an EHR
  writeback rejection, a payment processor failure, and a coding agent that fails test
  collection three times and aborts.
- **Weak retrieval grounding** — `knowledge_qa/session_04.json` answers from documents
  scoring 0.38–0.41; `customer_support/session_04.json` from 0.58–0.64.
- **An unsupported claim** — the third trace of `knowledge_qa/session_02.json` states an
  international meal limit that appears in none of the retrieved excerpts.
- **A prompt-injection attempt** in `revenue_agent/session_03.json` (the agent refuses).
- **A misroute** in `revenue_agent/session_04.json` — the router sends a billing question
  to the onboarding agent at 0.52 confidence, which hands it back.
- **A tool-call loop** in `coding_agent/session_05.json` — `run_tests` three times, same error.
- **State-mutating tools** throughout `revenue_agent` (`issue_refund`, `apply_discount`,
  `update_tax_region`) — the spans you'd want a guardrail in front of.

Session shapes vary too: single-trace sessions sit next to four-turn threads, so
session-level rollups aren't uniform.

## Regenerating

Run from `genai-engine/` so the engine's venv and `src/` are importable — the script
pushes every span through the engine's real `SpanNormalizationService`, which is what
makes the output faithful rather than hand-written:

```bash
cd genai-engine
GENAI_ENGINE_SECRET_STORE_KEY=dummy uv run python \
    ../adaptive-optimization/example_sessions/_generate.py
```

Output is deterministic (seeded at `20260905`), so regenerating produces identical files
unless the scenarios or the engine's normalizer change.

## A note on the data

Everything is invented — names, MRNs, tickers, order numbers, dollar figures. The clinical
sessions contain synthetic PHI-shaped fields (`mrn`, patient initials, medications)
specifically so PII/PHI detection has something to find; none of it corresponds to a real
person. Same for the financial sessions: ACME and NBK are not real issuers.
