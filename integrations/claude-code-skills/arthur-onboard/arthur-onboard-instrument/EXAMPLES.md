# Arthur Instrumentation Examples

Reference for `/arthur-onboard-instrument`. Two sections:
- [By Framework](#by-framework) — minimal working setup per library, with version callouts
- [By Span Pattern](#by-span-pattern) — copy-paste patterns for each OpenInference span kind

All Python examples use `arthur-observability-sdk`. All TypeScript examples use
`@opentelemetry` + `@arizeai/openinference-semantic-conventions` (or `@mastra/arthur`).

---

## By Framework

### Python — LangChain

#### v0.2+ (recommended — OpenInference auto-instrumentor)

```python
from arthur_observability_sdk import Arthur
import os

arthur = Arthur(
    task_id=os.environ["ARTHUR_TASK_ID"],
    service_name="my-langchain-app",
)
arthur.instrument_langchain()

# Wrap each request in arthur.attributes() for session grouping:
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

llm = ChatOpenAI(model="gpt-4o")

with arthur.attributes(session_id=session_id):
    response = llm.invoke([HumanMessage(content=user_input)])
```

#### v0.1.x (callback handler — use if stuck on 0.1)

LangChain 0.1 does not support the OpenInference auto-instrumentor.
Use the callback handler from `openinference-instrumentation-langchain` instead:

```python
from openinference.instrumentation.langchain import LangChainInstrumentor
# LangChainInstrumentor works for both 0.1 and 0.2 via callbacks
LangChainInstrumentor().instrument()
```

> **Note:** `arthur.instrument_langchain()` calls this under the hood for both versions.
> Prefer the arthur-sdk; only fall back to the direct instrumentor if the SDK is unavailable.

---

### Python — OpenAI

#### Chat Completions API

```python
from arthur_observability_sdk import Arthur
import openai, os

arthur = Arthur(task_id=os.environ["ARTHUR_TASK_ID"], service_name="my-openai-app")
arthur.instrument_openai()

client = openai.OpenAI()

with arthur.attributes(session_id=session_id, user_id=user_id):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": user_input}],
    )
```

#### Responses API (OpenAI v1.66+)

The Responses API uses a different call shape but is instrumented by the same
`instrument_openai()` call:

```python
arthur.instrument_openai()

with arthur.attributes(session_id=session_id):
    response = client.responses.create(
        model="gpt-4o",
        input=user_input,
    )
```

---

### Python — Anthropic

```python
from arthur_observability_sdk import Arthur
import anthropic, os

arthur = Arthur(task_id=os.environ["ARTHUR_TASK_ID"], service_name="my-anthropic-app")
arthur.instrument_anthropic()

client = anthropic.Anthropic()

with arthur.attributes(session_id=session_id):
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": user_input}],
    )
```

---

### Python — OpenAI Agents SDK

```python
from arthur_observability_sdk import Arthur
from agents import Agent, Runner
import os

arthur = Arthur(task_id=os.environ["ARTHUR_TASK_ID"], service_name="my-agents-app")
arthur.instrument_openai_agents()

agent = Agent(name="Assistant", instructions="You are a helpful assistant.")

with arthur.attributes(session_id=session_id):
    result = await Runner.run(agent, user_input)
```

---

### Python — CrewAI

```python
from arthur_observability_sdk import Arthur
from crewai import Agent, Task, Crew
import os

arthur = Arthur(task_id=os.environ["ARTHUR_TASK_ID"], service_name="my-crew-app")
arthur.instrument_crewai()

researcher = Agent(role="Researcher", goal="...", backstory="...")
task = Task(description=user_input, agent=researcher)
crew = Crew(agents=[researcher], tasks=[task])

with arthur.attributes(session_id=session_id):
    result = crew.kickoff()
```

---

### Python — AutoGen

#### v0.4+ (ConversableAgent / AgentChat — recommended)

```python
from arthur_observability_sdk import Arthur
import autogen, os

arthur = Arthur(task_id=os.environ["ARTHUR_TASK_ID"], service_name="my-autogen-app")
arthur.instrument_autogen_agentchat()

assistant = autogen.AssistantAgent("assistant", llm_config={"model": "gpt-4o"})
user_proxy = autogen.UserProxyAgent("user", human_input_mode="NEVER")

with arthur.attributes(session_id=session_id):
    user_proxy.initiate_chat(assistant, message=user_input)
```

#### v0.2.x (legacy event-based)

```python
arthur.instrument_autogen()   # instead of instrument_autogen_agentchat()
```

> **Note:** AutoGen renamed its API significantly between 0.2 and 0.4. The
> `instrument_autogen_agentchat()` call targets the v0.4 AgentChat interface.
> Use `instrument_autogen()` for v0.2 if you cannot upgrade.

---

### Python — LiteLLM (unified gateway)

Use when your app routes through LiteLLM to multiple providers:

```python
from arthur_observability_sdk import Arthur
import litellm, os

arthur = Arthur(task_id=os.environ["ARTHUR_TASK_ID"], service_name="my-litellm-app")
arthur.instrument_litellm()

with arthur.attributes(session_id=session_id):
    response = litellm.completion(
        model="gpt-4o",
        messages=[{"role": "user", "content": user_input}],
    )
```

---

### Python — MCP server app

For an app that calls MCP servers to execute tools, use `instrument_mcp()`. Each MCP
tool call is traced as a TOOL span with `mcp.server_name` and `mcp.tool_name` attributes.

```python
from arthur_observability_sdk import Arthur
import os

arthur = Arthur(task_id=os.environ["ARTHUR_TASK_ID"], service_name="my-mcp-app")
arthur.instrument_mcp()

# MCP tool calls are now traced automatically.
# Wrap the session in arthur.attributes() to group spans:
with arthur.attributes(session_id=session_id):
    # call_tool(name, arguments=...) — no server_name arg; the session is bound to one server
    result = await mcp_client.call_tool(tool_name, arguments=tool_input)
```

If using MCP without the SDK extra, see [MCP Tool Calls](#mcp-tool-calls) below for
the manual span pattern.

---

### Python — Slack Bolt (assistant bot)

Reference app: [slack-samples/bolt-python-assistant-template](https://github.com/slack-samples/bolt-python-assistant-template)

This template uses **Slack Bolt** with Socket Mode and the **OpenAI Responses API**
(`responses.create()`, not `chat.completions.create()`). LLM calls stream back to Slack
via `client.chat_stream()`. Tool calls follow the Responses API `function_call` /
`function_call_output` message format, with a recursive call to get the final reply.

Use the Slack `thread_ts` as `session_id` so every exchange in a thread is grouped
into one trace.

**`app.py` — one-time setup:**

```python
from arthur_observability_sdk import Arthur
import os

arthur = Arthur(
    task_id=os.environ["ARTHUR_TASK_ID"],
    service_name="my-slack-bot",
)
# instrument_openai() patches both chat.completions.create() AND responses.create()
arthur.instrument_openai()
```

**`agent/llm_caller.py` — instrumented call with streaming + tool loop:**

```python
import json, openai, os
from opentelemetry import trace
from opentelemetry.trace import StatusCode
from openinference.semconv.trace import SpanAttributes, OpenInferenceSpanKindValues
# Import the Arthur instance set up in app.py — do NOT instantiate a second one.
# Arthur() configures the global OTel tracer provider; doing it twice double-instruments.
from app import arthur

tracer = trace.get_tracer(__name__)  # safe from any module once app.py has been imported

def call_llm(streamer, prompts: list, thread_ts: str) -> None:
    """Stream a Responses API reply to Slack; recurse if tools are called."""
    llm = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # thread_ts groups all turns in a Slack thread into one trace session
    with arthur.attributes(session_id=thread_ts):
        response = llm.responses.create(
            model="gpt-4o-mini",
            input=prompts,
            tools=[roll_dice_definition],
            stream=True,
        )

        tool_calls = []
        for event in response:
            if event.type == "response.output_text.delta":
                streamer.append(markdown_text=event.delta)
            if event.type == "response.output_item.done":
                if event.item.type == "function_call":
                    tool_calls.append(event.item)

        if tool_calls:
            for call in tool_calls:
                # Wrap each tool execution in a TOOL span so it appears in the trace
                with tracer.start_as_current_span(call.name) as tool_span:
                    tool_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                                            OpenInferenceSpanKindValues.TOOL.value)
                    tool_span.set_attribute(SpanAttributes.TOOL_NAME, call.name)
                    tool_span.set_attribute("tool.id", call.call_id)  # links to LLM call
                    tool_span.set_attribute(SpanAttributes.INPUT_VALUE, call.arguments)
                    tool_span.set_attribute(SpanAttributes.INPUT_MIME_TYPE, "application/json")
                    try:
                        result = roll_dice(**json.loads(call.arguments))
                        tool_span.set_attribute(SpanAttributes.OUTPUT_VALUE, json.dumps(result))
                    except Exception as e:
                        tool_span.set_status(StatusCode.ERROR, str(e))
                        raise
                # Responses API tool-result format (not chat.completions format)
                prompts.append({
                    "type": "function_call",
                    "call_id": call.call_id,
                    "name": call.name,
                    "arguments": call.arguments,
                })
                prompts.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result),
                })
            call_llm(streamer, prompts, thread_ts)  # recursive — gets final text reply
```

**`listeners/assistant/message.py` — Bolt message handler:**

```python
from slack_bolt import BoltContext
from slack_sdk import WebClient
from agent.llm_caller import call_llm

def message(context: BoltContext, client: WebClient, payload: dict) -> None:
    thread_ts = payload.get("thread_ts") or payload["ts"]
    channel = payload["channel"]

    # Build conversation history from thread so the LLM has prior context
    history = client.conversations_replies(channel=channel, ts=thread_ts)
    prompts = [
        {"role": "user" if m.get("user") != context.bot_user_id else "assistant",
         "content": m["text"]}
        for m in history["messages"]
    ]

    with client.chat_stream(channel=channel, thread_ts=thread_ts) as streamer:
        call_llm(streamer, prompts, thread_ts=thread_ts)
```

**`.env` additions required:**

```
ARTHUR_API_KEY=<your-arthur-api-key>
ARTHUR_BASE_URL=<your-arthur-engine-url>
ARTHUR_TASK_ID=<your-arthur-task-id>
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
OPENAI_API_KEY=sk-...
```

> **Responses API vs Chat Completions:** The template calls `responses.create()` (OpenAI
> v1.66+). `arthur.instrument_openai()` patches both surfaces. If you are on an older
> SDK version, swap to `chat.completions.create()` — the Arthur instrumentation is
> identical; only the OpenAI call shape differs.

---

### Python — Slack Bolt + MCP servers

Same Slack Bolt pattern, but tools come from one or more MCP servers instead of
inline Python functions. Key differences from the inline-tool version above:

- Use `AsyncApp` so MCP's async client works naturally in handlers
- Keep a single `ClientSession` alive for the process lifetime — don't reconnect per message
- Fetch the tool list from MCP via `list_tools()` at startup and convert to OpenAI format
- Dispatch all tool calls in parallel with `asyncio.gather` since each is an independent MCP request
- Wrap each MCP call in a TOOL span with `tool.id` linking back to the LLM `call_id`

**`app.py` — MCP lifecycle + Arthur setup:**

```python
import asyncio, json, os
import openai
from contextlib import AsyncExitStack
from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from opentelemetry import trace
from opentelemetry.trace import StatusCode
from openinference.semconv.trace import SpanAttributes, OpenInferenceSpanKindValues
from arthur_observability_sdk import Arthur

arthur = Arthur(task_id=os.environ["ARTHUR_TASK_ID"], service_name="my-slack-mcp-bot")
arthur.instrument_openai()
tracer = trace.get_tracer(__name__)

app = AsyncApp(token=os.environ["SLACK_BOT_TOKEN"])

# Shared MCP state — initialised once at startup, reused across all messages
_exit_stack = AsyncExitStack()          # holds stdio_client + ClientSession open for lifetime
_mcp_session: ClientSession | None = None
_mcp_tools: list[dict] = []            # OpenAI Responses API tool definitions


async def init_mcp() -> None:
    """Connect to the MCP server and cache the tool list. Called once at startup."""
    global _mcp_session, _mcp_tools
    server_params = StdioServerParameters(
        command=os.environ["MCP_SERVER_COMMAND"],   # e.g. "npx"
        args=os.environ["MCP_SERVER_ARGS"].split(), # e.g. "-y @modelcontextprotocol/server-filesystem /tmp"
    )
    # AsyncExitStack holds both context managers open for the process lifetime
    # and calls __aexit__ on each during shutdown (see finally in main() below)
    read, write = await _exit_stack.enter_async_context(stdio_client(server_params))
    _mcp_session = await _exit_stack.enter_async_context(ClientSession(read, write))
    await _mcp_session.initialize()

    tools_result = await _mcp_session.list_tools()
    _mcp_tools = [
        {
            "type": "function",
            "name": t.name,
            "description": t.description or "",
            "parameters": t.inputSchema,
        }
        for t in tools_result.tools
    ]
    print(f"MCP ready: {[t['name'] for t in _mcp_tools]}")


async def dispatch_mcp_tool(call, server_name: str) -> str:
    """Execute one MCP tool call; returns string output for Responses API."""
    if _mcp_session is None:
        raise RuntimeError("MCP session not initialised — call init_mcp() at startup")
    with tracer.start_as_current_span(call.name) as tool_span:
        tool_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                                OpenInferenceSpanKindValues.TOOL.value)
        tool_span.set_attribute(SpanAttributes.TOOL_NAME, call.name)
        tool_span.set_attribute("mcp.server_name", server_name)
        tool_span.set_attribute("mcp.tool_name", call.name)
        tool_span.set_attribute("tool.id", call.call_id)   # links span → LLM tool_call
        tool_span.set_attribute(SpanAttributes.INPUT_VALUE, call.arguments)
        tool_span.set_attribute(SpanAttributes.INPUT_MIME_TYPE, "application/json")
        try:
            result = await _mcp_session.call_tool(
                call.name, arguments=json.loads(call.arguments)
            )
            output = result.content[0].text if result.content else ""
            tool_span.set_attribute(SpanAttributes.OUTPUT_VALUE, output)
            return output
        except Exception as e:
            tool_span.set_status(StatusCode.ERROR, str(e))
            raise


async def call_llm(streamer, prompts: list, thread_ts: str) -> None:
    """Stream Responses API reply to Slack; dispatch MCP tools in parallel if needed."""
    llm_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    tool_calls = []

    # arthur.attributes() must remain open across the tool dispatch phase so that
    # TOOL spans created inside dispatch_mcp_tool inherit the session.id from context
    with arthur.attributes(session_id=thread_ts):
        response = await llm_client.responses.create(
            model="gpt-4o-mini",
            input=prompts,
            tools=_mcp_tools,
            stream=True,
        )
        async for event in response:
            if event.type == "response.output_text.delta":
                streamer.append(markdown_text=event.delta)
            if event.type == "response.output_item.done":
                if event.item.type == "function_call":
                    tool_calls.append(event.item)

        if tool_calls:
            # Run all MCP tool calls concurrently; catch per-tool errors without aborting others
            server_name = os.environ.get("MCP_SERVER_NAME", "mcp")
            outputs = await asyncio.gather(
                *(dispatch_mcp_tool(call, server_name) for call in tool_calls),
                return_exceptions=True,
            )
            for call, output in zip(tool_calls, outputs):
                result_str = f"error: {output}" if isinstance(output, Exception) else output
                prompts.append({
                    "type": "function_call",
                    "call_id": call.call_id,
                    "name": call.name,
                    "arguments": call.arguments,
                })
                prompts.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": result_str,
                })

    if tool_calls:
        await call_llm(streamer, prompts, thread_ts)  # recursive; each call gets fresh session context


@app.event("assistant_thread_message")
async def handle_message(body: dict, client: AsyncWebClient) -> None:
    payload = body["event"]
    thread_ts = payload.get("thread_ts") or payload["ts"]
    channel = payload["channel"]

    history = await client.conversations_replies(channel=channel, ts=thread_ts)
    bot_user_id = body["authorizations"][0]["user_id"]
    prompts = [
        {
            "role": "user" if m.get("user") != bot_user_id else "assistant",
            "content": m["text"],
        }
        for m in history["messages"]
    ]

    async with client.chat_stream(channel=channel, thread_ts=thread_ts) as streamer:
        await call_llm(streamer, prompts, thread_ts=thread_ts)


if __name__ == "__main__":
    async def main():
        await init_mcp()
        handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
        try:
            await handler.start_async()
        finally:
            await _exit_stack.aclose()  # graceful MCP server shutdown

    asyncio.run(main())
```

**Additional `.env` entries for the MCP variant:**

```
MCP_SERVER_COMMAND=npx
MCP_SERVER_ARGS=-y @modelcontextprotocol/server-filesystem /tmp
MCP_SERVER_NAME=filesystem
```

> **SSE transport:** swap `stdio_client` for `mcp.client.sse.sse_client` and pass the
> server's URL. The `ClientSession` usage is identical.
>
> **Multiple MCP servers:** call `init_mcp()` once per server, append each server's
> `_mcp_tools` to a combined list, and route each `dispatch_mcp_tool` call to the right
> session based on the tool name (keep a `{tool_name: session}` lookup dict).

---

### TypeScript — Mastra

```typescript
import { Mastra } from "@mastra/core/mastra";
import { ArthurExporter } from "@mastra/arthur";

export const mastra = new Mastra({
  // ... preserve existing config ...
  observability: {
    configs: {
      arthur: {
        serviceName: "my-mastra-app",
        exporters: [
          new ArthurExporter({
            apiKey: process.env.ARTHUR_API_KEY!,
            endpoint: process.env.ARTHUR_BASE_URL!,
            taskId: process.env.ARTHUR_TASK_ID,
          }),
        ],
      },
    },
  },
});
```

Tag individual agent calls for filtering in the Arthur UI:

```typescript
const result = await agent.generate(userInput, {
  tracingOptions: {
    tags: ["production"],
    metadata: { userId: user.id, sessionId: session.id },
  },
});
```

---

### TypeScript — OpenAI (OpenInference manual)

```typescript
import { NodeTracerProvider } from "@opentelemetry/sdk-trace-node";
import { BatchSpanProcessor } from "@opentelemetry/sdk-trace-base";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-proto";
import { Resource } from "@opentelemetry/resources";
import { trace, context } from "@opentelemetry/api";
import { SemanticConventions } from "@arizeai/openinference-semantic-conventions";
import { OpenAIInstrumentation } from "@arizeai/openinference-instrumentation-openai";
import OpenAI from "openai";

const provider = new NodeTracerProvider({
  resource: new Resource({ "service.name": "my-openai-ts-app" }),
  spanProcessors: [
    new BatchSpanProcessor(
      new OTLPTraceExporter({
        url: `${process.env.ARTHUR_BASE_URL}/api/v1/traces`,
        headers: { Authorization: `Bearer ${process.env.ARTHUR_API_KEY}` },
      })
    ),
  ],
});
provider.register();

const openaiModule = await import("openai");
new OpenAIInstrumentation().manuallyInstrument(openaiModule);

const tracer = trace.getTracer("my-openai-ts-app");
const client = new OpenAI();

async function handleRequest(userInput: string, sessionId: string) {
  const span = tracer.startSpan("handle_request");
  span.setAttribute(SemanticConventions.OPENINFERENCE_SPAN_KIND, "CHAIN");
  span.setAttribute(SemanticConventions.INPUT_VALUE, userInput);
  span.setAttribute("session.id", sessionId);

  return context.with(trace.setSpan(context.active(), span), async () => {
    try {
      const response = await client.chat.completions.create({
        model: "gpt-4o",
        messages: [{ role: "user", content: userInput }],
      });
      const output = response.choices[0].message.content ?? "";
      span.setAttribute(SemanticConventions.OUTPUT_VALUE, output);
      return output;
    } finally {
      span.end();
    }
  });
}
```

---

## By Span Pattern

Reference for building spans manually or supplementing auto-instrumentation.
All Python examples assume `tracer = trace.get_tracer(__name__)` and the imports
from the Python arthur-sdk or OpenInference task prompts in SKILL.md.

---

### Retrieval / RAG

Use RETRIEVER kind for any step that fetches documents, chunks, or context
(vector store search, BM25, SQL lookup, web search).

**Python:**

```python
with tracer.start_as_current_span("retrieve") as ret_span:
    ret_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                           OpenInferenceSpanKindValues.RETRIEVER.value)
    ret_span.set_attribute(SpanAttributes.INPUT_VALUE, query)

    docs = vector_store.similarity_search(query, k=5)

    retrieved = []
    for i, doc in enumerate(docs):
        ret_span.set_attribute(
            f"retrieval.documents.{i}.document.content", doc.page_content
        )
        ret_span.set_attribute(
            f"retrieval.documents.{i}.document.id", doc.metadata.get("id", "")
        )
        score = doc.metadata.get("score")
        if score is not None:
            ret_span.set_attribute(
                f"retrieval.documents.{i}.document.score", float(score)
            )
        retrieved.append({"document_content": doc.page_content, "score": score})

    # REQUIRED: Arthur Engine reads output.value to render the retrieved docs in UI
    ret_span.set_attribute(SpanAttributes.OUTPUT_VALUE, json.dumps(retrieved))
    ret_span.set_attribute(SpanAttributes.OUTPUT_MIME_TYPE, "application/json")
```

**TypeScript:**

```typescript
const retSpan = tracer.startSpan("retrieve");
retSpan.setAttribute(SemanticConventions.OPENINFERENCE_SPAN_KIND, "RETRIEVER");
retSpan.setAttribute(SemanticConventions.INPUT_VALUE, query);

return context.with(trace.setSpan(context.active(), retSpan), async () => {
  try {
    const docs = await vectorStore.similaritySearch(query, 5);
    const retrieved = docs.map((doc, i) => {
      retSpan.setAttribute(
        `retrieval.documents.${i}.document.content`, doc.pageContent
      );
      return { document_content: doc.pageContent };
    });
    retSpan.setAttribute(
      SemanticConventions.OUTPUT_VALUE, JSON.stringify(retrieved)
    );
    retSpan.setAttribute(SemanticConventions.OUTPUT_MIME_TYPE, "application/json");
    return docs;
  } finally {
    retSpan.end();
  }
});
```

---

### Agent Orchestrator + Subagent

Use AGENT kind for any component that runs an LLM reasoning loop and decides
what tools or subagents to call. Nest subagents as children of the orchestrator span.

**Single agent (Python):**

```python
with arthur.attributes(session_id=session_id):
    with tracer.start_as_current_span("orchestrate") as agent_span:
        agent_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                                 OpenInferenceSpanKindValues.AGENT.value)
        agent_span.set_attribute("agent.name", "planner")
        agent_span.set_attribute(SpanAttributes.INPUT_VALUE, user_input)

        result = run_planning_loop(user_input)   # contains LLM calls + tool calls

        agent_span.set_attribute(SpanAttributes.OUTPUT_VALUE, result)
```

**Multi-agent: orchestrator calls a subagent (Python):**

```python
with tracer.start_as_current_span("orchestrator") as orch_span:
    orch_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                            OpenInferenceSpanKindValues.AGENT.value)
    orch_span.set_attribute("agent.name", "orchestrator")
    orch_span.set_attribute(SpanAttributes.INPUT_VALUE, user_input)

    # Subagent span is a child because it starts inside the orchestrator context
    with tracer.start_as_current_span("researcher") as sub_span:
        sub_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                               OpenInferenceSpanKindValues.AGENT.value)
        sub_span.set_attribute("agent.name", "researcher")
        sub_span.set_attribute(SpanAttributes.INPUT_VALUE, research_query)

        research_result = run_researcher(research_query)

        sub_span.set_attribute(SpanAttributes.OUTPUT_VALUE, research_result)

    final = synthesize(research_result)
    orch_span.set_attribute(SpanAttributes.OUTPUT_VALUE, final)
```

**TypeScript:**

```typescript
const orchSpan = tracer.startSpan("orchestrator");
orchSpan.setAttribute(SemanticConventions.OPENINFERENCE_SPAN_KIND, "AGENT");
orchSpan.setAttribute("agent.name", "orchestrator");
orchSpan.setAttribute(SemanticConventions.INPUT_VALUE, userInput);

return context.with(trace.setSpan(context.active(), orchSpan), async () => {
  try {
    const researchSpan = tracer.startSpan("researcher");
    researchSpan.setAttribute(SemanticConventions.OPENINFERENCE_SPAN_KIND, "AGENT");
    researchSpan.setAttribute("agent.name", "researcher");

    const result = await context.with(
      trace.setSpan(context.active(), researchSpan),
      async () => {
        try {
          return await runResearcher(userInput);
        } finally {
          researchSpan.end();
        }
      }
    );

    orchSpan.setAttribute(SemanticConventions.OUTPUT_VALUE, result);
    return result;
  } finally {
    orchSpan.end();
  }
});
```

---

### MCP Tool Calls

Use TOOL kind with `mcp.server_name` and `mcp.tool_name` attributes.
If using `arthur.instrument_mcp()`, these are set automatically.

**Python (manual):**

`tool_call_id` links the TOOL span back to the specific LLM `function_call` that requested
it. Set it when you have a `call_id` from the LLM response (Responses API) or `id` from
`tool_calls` (Chat Completions API).

```python
with tracer.start_as_current_span(f"{server_name}.{tool_name}") as mcp_span:
    mcp_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                           OpenInferenceSpanKindValues.TOOL.value)
    mcp_span.set_attribute(SpanAttributes.TOOL_NAME, f"{server_name}/{tool_name}")
    mcp_span.set_attribute("mcp.server_name", server_name)
    mcp_span.set_attribute("mcp.tool_name", tool_name)
    mcp_span.set_attribute("tool.id", tool_call_id)  # call_id from LLM response
    mcp_span.set_attribute(SpanAttributes.INPUT_VALUE, json.dumps(tool_input))
    mcp_span.set_attribute(SpanAttributes.INPUT_MIME_TYPE, "application/json")
    try:
        result = await mcp_client.call_tool(tool_name, arguments=tool_input)
        mcp_span.set_attribute(SpanAttributes.OUTPUT_VALUE, json.dumps(result))
        mcp_span.set_attribute(SpanAttributes.OUTPUT_MIME_TYPE, "application/json")
    except Exception as e:
        mcp_span.set_status(StatusCode.ERROR, str(e))
        raise
```

**TypeScript (manual):**

```typescript
const mcpSpan = tracer.startSpan(`${serverName}.${toolName}`);
mcpSpan.setAttribute(SemanticConventions.OPENINFERENCE_SPAN_KIND, "TOOL");
mcpSpan.setAttribute(SemanticConventions.TOOL_NAME, `${serverName}/${toolName}`);
mcpSpan.setAttribute("mcp.server_name", serverName);
mcpSpan.setAttribute("mcp.tool_name", toolName);
mcpSpan.setAttribute("tool.id", toolCallId);  // call_id from LLM response
mcpSpan.setAttribute(SemanticConventions.INPUT_VALUE, JSON.stringify(toolInput));
mcpSpan.setAttribute(SemanticConventions.INPUT_MIME_TYPE, "application/json");
try {
  const result = await mcpClient.callTool(serverName, toolName, toolInput);
  mcpSpan.setAttribute(SemanticConventions.OUTPUT_VALUE, JSON.stringify(result));
  mcpSpan.setAttribute(SemanticConventions.OUTPUT_MIME_TYPE, "application/json");
  return result;
} catch (e) {
  mcpSpan.setStatus({ code: SpanStatusCode.ERROR, message: String(e) });
  throw e;
} finally {
  mcpSpan.end();
}
```

---

### Tool Spans (LLM function calling)

Use TOOL kind for each function/tool execution called by the LLM. The `tool.id`
attribute links this execution back to the tool_call.id from the LLM response.

**Python:**

```python
def execute_tool(tool_call):
    with tracer.start_as_current_span(tool_call.function.name) as tool_span:
        tool_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                                OpenInferenceSpanKindValues.TOOL.value)
        tool_span.set_attribute(SpanAttributes.TOOL_NAME, tool_call.function.name)
        tool_span.set_attribute("tool.id", tool_call.id)
        tool_span.set_attribute(SpanAttributes.INPUT_VALUE, tool_call.function.arguments)
        tool_span.set_attribute(SpanAttributes.INPUT_MIME_TYPE, "application/json")
        try:
            args = json.loads(tool_call.function.arguments)
            result = dispatch_tool(tool_call.function.name, args)
            result_str = json.dumps(result) if not isinstance(result, str) else result
            tool_span.set_attribute(SpanAttributes.OUTPUT_VALUE, result_str)
            tool_span.set_attribute(SpanAttributes.OUTPUT_MIME_TYPE, "application/json")
            return result
        except Exception as e:
            tool_span.set_status(StatusCode.ERROR, str(e))
            raise
```

**TypeScript:**

```typescript
async function executeTool(toolCall: ChatCompletionMessageToolCall) {
  const toolSpan = tracer.startSpan(toolCall.function.name);
  toolSpan.setAttribute(SemanticConventions.OPENINFERENCE_SPAN_KIND, "TOOL");
  toolSpan.setAttribute(SemanticConventions.TOOL_NAME, toolCall.function.name);
  toolSpan.setAttribute("tool.id", toolCall.id);
  toolSpan.setAttribute(
    SemanticConventions.INPUT_VALUE, toolCall.function.arguments
  );
  toolSpan.setAttribute(SemanticConventions.INPUT_MIME_TYPE, "application/json");
  try {
    const args = JSON.parse(toolCall.function.arguments);
    const result = await dispatchTool(toolCall.function.name, args);
    toolSpan.setAttribute(
      SemanticConventions.OUTPUT_VALUE, JSON.stringify(result)
    );
    toolSpan.setAttribute(SemanticConventions.OUTPUT_MIME_TYPE, "application/json");
    return result;
  } catch (e) {
    toolSpan.setStatus({ code: SpanStatusCode.ERROR, message: String(e) });
    throw e;
  } finally {
    toolSpan.end();
  }
}
```

---

### Guardrail Spans

Use GUARDRAIL kind to trace content filtering or safety checks run before or after
an LLM call. Useful for tracking which requests were blocked and why.

**Python:**

```python
with tracer.start_as_current_span("safety_check") as guard_span:
    guard_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                             OpenInferenceSpanKindValues.GUARDRAIL.value)
    guard_span.set_attribute(SpanAttributes.INPUT_VALUE, user_input)

    passed, reason = run_safety_check(user_input)

    guard_span.set_attribute(SpanAttributes.OUTPUT_VALUE,
                             json.dumps({"passed": passed, "reason": reason}))
    guard_span.set_attribute(SpanAttributes.OUTPUT_MIME_TYPE, "application/json")
    if not passed:
        guard_span.set_status(StatusCode.ERROR, description=reason)
```

---

### Embedding Spans

Use EMBEDDING kind for calls to an embedding model (e.g., during indexing or query
embedding in a RAG pipeline).

**Python:**

```python
with tracer.start_as_current_span("embed_query") as emb_span:
    emb_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                           OpenInferenceSpanKindValues.EMBEDDING.value)
    emb_span.set_attribute(SpanAttributes.INPUT_VALUE, text)
    emb_span.set_attribute("embedding.model_name", "text-embedding-3-small")

    vector = embed(text)

    emb_span.set_attribute("embedding.embeddings.0.embedding.text", text)
    # vector values are large — only log the dimension count, not the full vector
    emb_span.set_attribute("embedding.embeddings.0.embedding.vector_length",
                           len(vector))
```

---

### Streaming Responses (Python)

Standard context managers cannot span across `yield` points. Use explicit OTel
`attach`/`detach` so the session context propagates to child spans inside the generator.

```python
from opentelemetry import context as otel_ctx
from opentelemetry.trace import set_span_in_context
from opentelemetry.context import set_value as otel_set_value

def stream_response(user_input: str, session_id: str):
    root_span = tracer.start_span("stream_handler")
    root_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                            OpenInferenceSpanKindValues.CHAIN.value)
    root_span.set_attribute(SpanAttributes.INPUT_VALUE, user_input)

    # Attach session_id to OTel context so LLM child spans inherit it
    ctx = otel_set_value(
        SpanAttributes.SESSION_ID, session_id,
        context=set_span_in_context(root_span),
    )
    token = otel_ctx.attach(ctx)
    full_response = []
    try:
        for chunk in call_llm_stream(user_input):
            otel_ctx.detach(token)
            yield chunk
            full_response.append(chunk)
            token = otel_ctx.attach(ctx)
        root_span.set_attribute(SpanAttributes.OUTPUT_VALUE,
                                "".join(full_response))
    finally:
        root_span.end()
        otel_ctx.detach(token)
```
