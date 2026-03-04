# Arthur Observability SDK

Python SDK for sending traces and managing prompts with the
[Arthur GenAI Engine](https://arthur.ai).

---

## Installation

```bash
pip install arthur-observability-sdk
```

To instrument a specific framework, install its extra:

```bash
pip install "arthur-observability-sdk[openai]"
pip install "arthur-observability-sdk[langchain]"
pip install "arthur-observability-sdk[anthropic]"
```

---

## How-to guides

Full guides are in [`docs/`](docs/):

- **[Getting started](docs/getting-started.md)** — initialisation, session/user context, framework instrumentation, shutdown
- **[Prompt management](docs/prompt-management.md)** — fetching and rendering versioned prompts, PROMPT span attributes

### Quick start

```python
from arthur_observability_sdk import Arthur

arthur = Arthur(
    api_key="your-api-key",       # or set ARTHUR_API_KEY env var
    task_id="<your-task-uuid>",
    service_name="my-app",
)
arthur.instrument_openai()

# Tag all spans in this block with session and user
with arthur.attributes(session_id="sess-1", user_id="user-42"):
    response = openai_client.chat.completions.create(...)

arthur.shutdown()
```

### Prompt management

```python
# Fetch a saved prompt by name (defaults to "latest" version)
prompt = arthur.get_prompt("system-instructions")

# Render with variable substitution
rendered = arthur.render_prompt(
    "rag-answer",
    variables={"context": "...", "question": "..."},
)
messages = rendered["messages"]
```

---

## Supported instrumentors

Pass `--extras` to install any of these alongside the SDK.

| Extra | Framework | Method |
|-------|-----------|--------|
| `agent-framework` | Agent Framework | `instrument_agent_framework()` |
| `agentspec` | AgentSpec | `instrument_agentspec()` |
| `agno` | Agno | `instrument_agno()` |
| `anthropic` | Anthropic | `instrument_anthropic()` |
| `autogen` | AutoGen | `instrument_autogen()` |
| `autogen-agentchat` | AutoGen AgentChat | `instrument_autogen_agentchat()` |
| `bedrock` | AWS Bedrock | `instrument_bedrock()` |
| `beeai` | BeeAI | `instrument_beeai()` |
| `crewai` | CrewAI | `instrument_crewai()` |
| `dspy` | DSPy | `instrument_dspy()` |
| `google-adk` | Google ADK | `instrument_google_adk()` |
| `google-genai` | Google GenAI | `instrument_google_genai()` |
| `groq` | Groq | `instrument_groq()` |
| `guardrails` | Guardrails AI | `instrument_guardrails()` |
| `haystack` | Haystack | `instrument_haystack()` |
| `instructor` | Instructor | `instrument_instructor()` |
| `langchain` | LangChain | `instrument_langchain()` |
| `litellm` | LiteLLM | `instrument_litellm()` |
| `llama-index` | LlamaIndex | `instrument_llama_index()` |
| `mcp` | MCP | `instrument_mcp()` |
| `mistralai` | Mistral AI | `instrument_mistralai()` |
| `monkai-agent` | Monkai Agent | `instrument_monkai_agent()` |
| `openai` | OpenAI | `instrument_openai()` |
| `openai-agents` | OpenAI Agents | `instrument_openai_agents()` |
| `openlit` | OpenLIT | `instrument_openlit()` |
| `openllmetry` | OpenLLMetry | `instrument_openllmetry()` |
| `pipecat` | Pipecat | `instrument_pipecat()` |
| `portkey` | Portkey | `instrument_portkey()` |
| `pydantic-ai` | Pydantic AI | `instrument_pydantic_ai()` |
| `smolagents` | SmolAgents | `instrument_smolagents()` |
| `strands-agents` | Strands Agents | `instrument_strands_agents()` |
| `vertexai` | Vertex AI | `instrument_vertexai()` |
| `claude-agent-sdk` | Claude Agent SDK | `instrument_claude_agent_sdk()` |

Install all at once: `pip install "arthur-observability-sdk[all]"`

---

## Developer guide

### Setup

```bash
cd arthur-observability-sdk

# 1. Generate the API client (requires Node.js and Java)
./scripts/generate_openapi_client.sh generate python

# 2. Install dependencies (also registers the generated client in the venv)
./scripts/generate_openapi_client.sh install python
```

> **Note:** `src/arthur_genai_client/` is auto-generated and gitignored. You must run
> `./scripts/generate_openapi_client.sh generate python` after cloning, and again whenever the
> GenAI Engine API changes. See [Regenerating the API client](#regenerating-the-api-client).

### Running tests

```bash
# Unit tests only (fast, no network)
poetry run pytest tests -m "unit_tests" -v

# Integration/smoke tests (builds wheel, installs into a fresh venv)
poetry run pytest tests -m "integration_tests" -v

# All tests
poetry run pytest tests -v
```

### Linting

```bash
./scripts/lint.sh
```

Or individually:

```bash
poetry run black src tests
poetry run isort src tests --profile black
poetry run autoflake --remove-all-unused-imports --in-place --recursive src tests
poetry run mypy src/arthur_observability_sdk
```

### Regenerating the API client

`src/arthur_genai_client/` is auto-generated from the GenAI Engine OpenAPI spec
and is **not committed to the repository**. Regenerate it after cloning or whenever
the API changes:

```bash
./scripts/generate_openapi_client.sh generate python
```

Requires Node.js (any recent LTS) and Java 11+.

### Building the wheel

```bash
poetry build --format wheel
```
