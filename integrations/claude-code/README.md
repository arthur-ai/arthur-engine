# Claude Code → Arthur GenAI Engine

Run Claude Code through a LiteLLM proxy that sends traces to Arthur GenAI Engine.

## Setup

Copy `.env.template` to `.env` and set:

| Variable | Purpose |
|----------|---------|
| `GENAI_ENGINE_API_KEY` | Arthur GenAI Engine API key |
| `GENAI_ENGINE_TRACE_ENDPOINT` | e.g. `http://localhost:3030/api/v1/traces` |
| `GENAI_ENGINE_TASK_ID` | Arthur GenAI Engine Task ID |
| `ANTHROPIC_API_KEY` | Claude API access (Only needed for when OAuth passthrough is not available) |

## Run

```bash
docker compose up -d
./occ
```
