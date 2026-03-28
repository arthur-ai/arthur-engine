# Prompt Management (TypeScript)

The Arthur Observability SDK lets you fetch and render versioned prompts stored in the
Arthur GenAI Engine.  Every call automatically emits an OpenTelemetry **PROMPT** span so
that prompt usage is visible alongside your LLM traces.

> **Prerequisite:** `taskId` or `taskName` must be provided when constructing `Arthur`.
> Prompt calls require a resolved task UUID.

---

## Fetching a prompt

`arthur.getPrompt(name)` retrieves a prompt by name from the GenAI Engine and returns
the raw prompt object (matches the `AgenticPrompt` schema).

### Default version (`"latest"`)

```typescript
const prompt = await arthur.getPrompt("system-instructions");
// Returns: { name: "system-instructions", messages: [...], variables: [...], ... }
```

### Specific version

```typescript
const prompt = await arthur.getPrompt("system-instructions", { version: "3" });
```

### By tag

When `tag` is provided, `version` is ignored and the by-tag endpoint is used:

```typescript
const prompt = await arthur.getPrompt("system-instructions", { tag: "stable" });
```

### Signature

```typescript
arthur.getPrompt(
  name: string,
  options?: {
    version?: string;   // default "latest"; ignored when tag is set
    tag?: string;       // fetch the tagged version
    taskId?: string;    // overrides the instance-level taskId for this call
  },
): Promise<Record<string, any>>
```

---

## Rendering a prompt

`arthur.renderPrompt(name, variables)` fetches the prompt template and substitutes
`{{variable}}` placeholders with the provided values.  Returns the fully rendered prompt
object with substituted messages.

```typescript
const rendered = await arthur.renderPrompt(
  "rag-answer",
  {
    context: "Arthur is an AI observability platform...",
    question: "What does Arthur do?",
  },
);
const messages = rendered.messages;
// [{ role: "system", content: "..." }, { role: "user", content: "..." }]
```

### With a specific version or tag

```typescript
const rendered = await arthur.renderPrompt(
  "rag-answer",
  { context: "...", question: "..." },
  { version: "2" },
);

const rendered = await arthur.renderPrompt(
  "rag-answer",
  { context: "...", question: "..." },
  { tag: "production" },
);
```

### Strict mode

Set `strict: true` to raise an error if any template variable is missing from
`variables`:

```typescript
const rendered = await arthur.renderPrompt(
  "rag-answer",
  { context: "..." },
  { strict: true },
);
// throws if "question" variable is not supplied
```

### Signature

```typescript
arthur.renderPrompt(
  name: string,
  variables: Record<string, string>,
  options?: {
    version?: string;    // default "latest"; ignored when tag is set
    tag?: string;        // used as version path segment
    strict?: boolean;    // raise if a variable is missing
    taskId?: string;     // overrides instance-level taskId
  },
): Promise<Record<string, any>>
```

---

## PROMPT spans

Every `getPrompt` and `renderPrompt` call creates an OpenTelemetry span with
`openinference.span.kind = PROMPT`.  Key attributes:

| Attribute | `getPrompt` | `renderPrompt` |
|-----------|-------------|-----------------|
| `openinference.span.kind` | `PROMPT` | `PROMPT` |
| `arthur.prompt.name` | prompt name | prompt name |
| `arthur.task.id` | resolved task UUID | resolved task UUID |
| `llm.prompt_template.version` | version or tag | version or tag |
| `llm.prompt_template.template` | JSON-encoded messages | JSON-encoded unrendered messages |
| `llm.prompt_template.variables` | JSON-encoded variable list | JSON-encoded variable values |
| `input.value` | — | unrendered messages + variables |
| `output.value` | raw prompt object | rendered prompt object |

For `renderPrompt`, the span `input` captures the **unrendered** template plus the
variable values so you can audit what was substituted, while `output` shows the final
rendered messages.

---

## Attaching session and user context to prompt spans

Prompt spans are created manually rather than via an auto-instrumentor.  The SDK
explicitly copies any active OpenInference context attributes (`session.id`, `user.id`,
`metadata`, `tags`) onto each PROMPT span.  Simply wrap the call in the relevant context:

```typescript
await arthur.session("session-abc-123", async () => {
  const prompt = await arthur.getPrompt("system-instructions");
});

await arthur.user("user-42", async () => {
  const rendered = await arthur.renderPrompt("rag-answer", { ... });
});

await arthur.attributes(
  { sessionId: "sess-1", userId: "user-99" },
  async () => {
    const rendered = await arthur.renderPrompt("rag-answer", { ... });
  },
);
```

The resulting PROMPT span will have `session.id` and/or `user.id` set, linking it to the
rest of the conversation trace.

---

## Full example

```typescript
import { Arthur } from "@arthur-ai/observability-sdk";
import OpenAI from "openai";

const arthur = new Arthur({
  apiKey: "your-api-key",
  taskId: "<your-task-uuid>",
});
arthur.instrumentOpenAI();

const client = new OpenAI();

await arthur.attributes(
  { sessionId: "sess-1", userId: "user-42" },
  async () => {
    // Fetch and render the saved prompt
    const rendered = await arthur.renderPrompt(
      "rag-answer",
      {
        context: "Arthur is an AI observability platform.",
        question: "How does Arthur help with LLM monitoring?",
      },
    );

    // Pass the rendered messages directly to the LLM
    const response = await client.chat.completions.create({
      model: "gpt-4o-mini",
      messages: rendered.messages,
    });
    console.log(response.choices[0].message.content);
  },
);

await arthur.shutdown();
```
