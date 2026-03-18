# Prompt Management

The Arthur Observability SDK lets you fetch and render versioned prompts stored in the
Arthur GenAI Engine.  Every call automatically emits an OpenTelemetry **PROMPT** span so
that prompt usage is visible alongside your LLM traces.

> **Prerequisite:** `task_id` or `task_name` must be provided when constructing `Arthur`.
> Prompt calls require a resolved task UUID.

---

## Fetching a prompt

`arthur.get_prompt(name)` retrieves a prompt by name from the GenAI Engine and returns
the raw prompt dict (matches the `AgenticPrompt` schema).

### Default version (`"latest"`)

```python
prompt = arthur.get_prompt("system-instructions")
# Returns: {"name": "system-instructions", "messages": [...], "variables": [...], ...}
```

### Specific version

```python
prompt = arthur.get_prompt("system-instructions", version="3")
```

### By tag

When `tag` is provided, `version` is ignored and the by-tag endpoint is used:

```python
prompt = arthur.get_prompt("system-instructions", tag="stable")
```

### Signature

```python
arthur.get_prompt(
    name: str,
    version: str = "latest",   # ignored when tag is set
    tag: str | None = None,     # fetch the tagged version
    task_id: str | None = None, # overrides the instance-level task_id for this call
) -> dict
```

---

## Rendering a prompt

`arthur.render_prompt(name, variables)` fetches the prompt template and substitutes
`{{variable}}` placeholders with the provided values.  Returns the fully rendered prompt
dict with substituted messages.

```python
rendered = arthur.render_prompt(
    "rag-answer",
    variables={
        "context": "Arthur is an AI observability platform...",
        "question": "What does Arthur do?",
    },
)
messages = rendered["messages"]
# [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
```

### With a specific version or tag

```python
rendered = arthur.render_prompt(
    "rag-answer",
    variables={"context": "...", "question": "..."},
    version="2",
)

rendered = arthur.render_prompt(
    "rag-answer",
    variables={"context": "...", "question": "..."},
    tag="production",
)
```

### Strict mode

Set `strict=True` to raise an error if any template variable is missing from
`variables`:

```python
rendered = arthur.render_prompt("rag-answer", variables={"context": "..."}, strict=True)
# raises ArthurAPIError if "question" variable is not supplied
```

### Signature

```python
arthur.render_prompt(
    name: str,
    variables: dict[str, str],
    version: str = "latest",    # ignored when tag is set
    tag: str | None = None,     # used as version path segment
    strict: bool = False,       # raise if a variable is missing
    task_id: str | None = None, # overrides instance-level task_id
) -> dict
```

---

## PROMPT spans

Every `get_prompt` and `render_prompt` call creates an OpenTelemetry span with
`openinference.span.kind = PROMPT`.  Key attributes:

| Attribute | `get_prompt` | `render_prompt` |
|-----------|-------------|-----------------|
| `openinference.span.kind` | `PROMPT` | `PROMPT` |
| `arthur.prompt.name` | prompt name | prompt name |
| `arthur.task.id` | resolved task UUID | resolved task UUID |
| `llm.prompt_template.version` | version or tag | version or tag |
| `llm.prompt_template` | JSON-encoded messages | JSON-encoded unrendered messages |
| `llm.prompt_template.variables` | JSON-encoded variable list | JSON-encoded variable values |
| `input.value` | — | unrendered messages + variables |
| `output.value` | raw prompt dict | rendered prompt dict |

For `render_prompt`, the span `input` captures the **unrendered** template plus the
variable values so you can audit what was substituted, while `output` shows the final
rendered messages.

---

## Attaching session and user context to prompt spans

Prompt spans are created manually rather than via an auto-instrumentor.  The SDK
explicitly copies any active OpenInference context attributes (`session.id`, `user.id`,
`metadata`, `tags`) onto each PROMPT span.  Simply wrap the call in the relevant context:

```python
with arthur.session("session-abc-123"):
    prompt = arthur.get_prompt("system-instructions")

with arthur.user("user-42"):
    rendered = arthur.render_prompt("rag-answer", variables={...})

with arthur.attributes(session_id="sess-1", user_id="user-99"):
    rendered = arthur.render_prompt("rag-answer", variables={...})
```

The resulting PROMPT span will have `session.id` and/or `user.id` set, linking it to the
rest of the conversation trace.

---

## Full example

```python
import openai
from arthur_observability_sdk import Arthur

arthur = Arthur(
    api_key="your-api-key",
    task_id="<your-task-uuid>",
)
arthur.instrument_openai()

client = openai.OpenAI()

with arthur.attributes(session_id="sess-1", user_id="user-42"):
    # Fetch and render the saved prompt
    rendered = arthur.render_prompt(
        "rag-answer",
        variables={
            "context": "Arthur is an AI observability platform.",
            "question": "How does Arthur help with LLM monitoring?",
        },
    )

    # Pass the rendered messages directly to the LLM
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=rendered["messages"],
    )
    print(response.choices[0].message.content)

arthur.shutdown()
```
