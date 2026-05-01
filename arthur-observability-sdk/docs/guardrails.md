# Guardrails

The Arthur Observability SDK lets you validate prompts and LLM responses against
the rules configured for an Arthur task.  Every call automatically emits an
OpenTelemetry **GUARDRAIL** span so that guardrail checks are visible alongside
your LLM traces.

> **Prerequisite:** `task_id` or `task_name` must be provided when constructing
> `Arthur`.  Validation calls require a resolved task UUID.

---

## Validating a prompt

`arthur.validate_prompt(prompt)` runs the prompt through every prompt-side rule
configured for the task and returns the raw `ValidationResult` dict.  The
returned `inference_id` is what links the prompt check to the response check
that follows.

```python
prompt_result = arthur.validate_prompt("What is the capital of France?")
inference_id = prompt_result["inference_id"]
# rule_results: [{"id": ..., "name": "PII Check", "result": "Pass", ...}, ...]
```

### Signature

```python
arthur.validate_prompt(
    prompt: str,
    task_id: str | None = None,  # overrides the instance-level task_id
) -> dict
```

---

## Validating a response

`arthur.validate_response(response, inference_id)` runs the response through
every response-side rule configured for the task.  Pass `context` whenever a
Hallucination rule is enabled — it is the ground-truth text that each claim in
the response is checked against.

```python
response_result = arthur.validate_response(
    response="The capital of France is Paris.",
    inference_id=inference_id,
    context="Paris is the capital and most populous city of France.",
)
# rule_results: [{"id": ..., "name": "Hallucination Check", "result": "Pass", ...}, ...]
```

### Signature

```python
arthur.validate_response(
    response: str,
    inference_id: str,            # from a prior validate_prompt call
    context: str | None = None,   # required for Hallucination rules
    task_id: str | None = None,   # overrides the instance-level task_id
) -> dict
```

---

## GUARDRAIL spans

Every `validate_prompt` and `validate_response` call creates an OpenTelemetry
span with `openinference.span.kind = GUARDRAIL`.  Key attributes:

| Attribute | `validate_prompt` | `validate_response` |
|-----------|-------------------|---------------------|
| `openinference.span.kind` | `GUARDRAIL` | `GUARDRAIL` |
| `arthur.task.id` | resolved task UUID | resolved task UUID |
| `arthur.inference.id` | from response (if returned) | from `inference_id` parameter |
| `input.value` | `{"prompt": ...}` | `{"response": ..., "context": ...}` |
| `input.mime_type` | `application/json` | `application/json` |
| `output.value` | raw `ValidationResult` dict | raw `ValidationResult` dict |
| `output.mime_type` | `application/json` | `application/json` |

If the underlying API call raises, the exception is recorded on the span, the
span status is set to `ERROR`, and the exception is re-raised.

---

## Attaching session and user context to GUARDRAIL spans

GUARDRAIL spans are created manually rather than via an auto-instrumentor.  The
SDK explicitly copies any active OpenInference context attributes (`session.id`,
`user.id`, `metadata`, `tags`) onto each span.  Wrap the call in the relevant
context:

```python
with arthur.session("session-abc-123"):
    result = arthur.validate_prompt("...")

with arthur.user("user-42"):
    result = arthur.validate_response("...", inference_id=inference_id)

with arthur.attributes(session_id="sess-1", user_id="user-99"):
    arthur.validate_prompt("...")
```

The resulting GUARDRAIL span will have `session.id` and/or `user.id` set,
linking the guardrail check to the rest of the conversation trace.

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
prompt = "What is the capital of France?"
context = "Paris is the capital and most populous city of France."

with arthur.attributes(session_id="sess-1", user_id="user-42"):
    prompt_result = arthur.validate_prompt(prompt)
    if any(r["result"] == "Fail" for r in prompt_result["rule_results"]):
        raise RuntimeError("Prompt failed guardrails")

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    response_text = completion.choices[0].message.content

    response_result = arthur.validate_response(
        response=response_text,
        inference_id=prompt_result["inference_id"],
        context=context,
    )
    if any(r["result"] == "Fail" for r in response_result["rule_results"]):
        raise RuntimeError("Response failed guardrails")

    print(response_text)

arthur.shutdown()
```
