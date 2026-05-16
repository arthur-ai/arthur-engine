---
name: arthur-onboard-prompts
description: Arthur onboarding sub-skill — Step 6: Extract prompts from the target repository and register them with Arthur Engine. Reads credentials from .arthur-engine.env.
allowed-tools: Bash, Read, Task
---

# Arthur Onboard — Step 6: Extract & Register Prompts

## Read State

```bash
cat .arthur-engine.env 2>/dev/null || echo "(no state file)"
```

Parse `ARTHUR_ENGINE_URL`, `ARTHUR_API_KEY`, `ARTHUR_TASK_ID`.

---

## Extract Prompts via Sub-agent

Delegate to a Task sub-agent (full claude agent) to find prompts in the repo:

```
Analyze the agentic application at: <REPO_PATH>

Use Read, Glob (find), and Grep to find all prompt definitions:
- System prompt strings assigned to variables (any language)
- User prompt templates with variables
- Multi-turn message arrays in OpenAI format ([{"role": "system", ...}])
- Prompt files (.txt, .md, .jinja2)
- Agent instruction strings passed to agent/chain initialization

Also detect the LLM model and provider used (from API call patterns, imports, env var names
like OPENAI_API_KEY, model= parameters, etc.).

Return ONLY a raw JSON object with no markdown, no explanation:
{
  "prompts": [
    {
      "name": "kebab-case-unique-name",
      "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."}
      ],
      "model_name": "gpt-4o" | null,
      "model_provider": "openai" | "anthropic" | "gemini" | "bedrock" | "vertex_ai" | null
    }
  ],
  "detected_model_name": "<model>" | null,
  "detected_model_provider": "<provider>" | null
}

Rules:
- Only include prompts with substantive content (skip empty strings and test fixtures)
- Convert template variables to {{double_brace}} format regardless of source syntax
- Names: unique, lowercase, kebab-case, descriptive
- If nothing found: {"prompts": [], "detected_model_name": null, "detected_model_provider": null}
```

---

## After Extraction

- **No prompts found:** tell the user, exit this skill
- **Prompts found:** show the list and ask for confirmation

For each confirmed prompt, register via:
```bash
curl -s -X POST \
  -H "Authorization: Bearer $ARTHUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$PROMPT_JSON" \
  "$ARTHUR_ENGINE_URL/api/v1/tasks/$ARTHUR_TASK_ID/prompts/$PROMPT_NAME"
```

Where `$PROMPT_JSON` = `{"messages": [...], "model_name": "...", "model_provider": "..."}`.

This step is non-blocking — log a warning and continue if it errors.
