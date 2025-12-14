# Dynamic Model Selection from Arthur Prompts

This document explains how the customer support agent dynamically selects models based on Arthur prompt configurations.

## Overview

Instead of hardcoding models in the agent code (e.g., `openai("gpt-4o")`), the agent now **reads the model configuration from each Arthur prompt** and uses it for inference. This provides flexibility to:

- Change models without code changes
- Use different models for different agents
- A/B test models via prompt versioning
- Centrally manage model selection in Arthur

## Implementation

### 1. Model Resolver (`src/mastra/lib/model-resolver.ts`)

A new utility module that resolves models dynamically:

```typescript
import { resolveModelFromPrompt } from "@/mastra/lib/model-resolver";

// Automatically resolves based on prompt's model_provider and model_name
const model = resolveModelFromPrompt(promptResult);
```

**Supported Providers:**
- `openai` - OpenAI models (gpt-4, gpt-4o, gpt-4-turbo, etc.)
- Falls back to OpenAI for unknown providers with a warning

**Easy to extend:**
```typescript
case "anthropic":
  return anthropic(modelName);
case "google":
  return google(modelName);
```

### 2. Updated API Route (`src/app/api/chat/route.ts`)

All agent calls now use the model from the prompt:

**Before:**
```typescript
const { messages } = await getTemplatedPrompt({...});
const result = await agent.generate(messages, {
  output: Schema,
});
```

**After:**
```typescript
const prompt = await getTemplatedPrompt({...});
const result = await agent.generate(prompt.messages, {
  output: Schema,
  model: resolveModelFromPrompt(prompt),  // ✨ Dynamic model
});
```

### 3. Updated Test Harness (`scripts/test-harness.ts`)

The test harness also uses dynamic models, ensuring consistency between testing and production.

## How It Works

### Flow Diagram

```
1. Fetch Prompt from Arthur
   ↓
   {
     messages: [...],
     model_provider: "openai",
     model_name: "gpt-4o",
     config: {...}
   }

2. Resolve Model
   ↓
   resolveModelFromPrompt(prompt)
   ↓
   openai("gpt-4o")

3. Pass to Agent
   ↓
   agent.generate(messages, {
     model: resolvedModel,
     ...
   })
```

### Arthur Prompt Configuration

When creating prompts in Arthur, specify the model:

```yaml
Prompt: mastra-agent-support-plan
Model Provider: openai
Model Name: gpt-4o
Version: production
```

You can use different models for different agents:
- **Plan Agent**: `gpt-4o-mini` (fast, cheap)
- **Draft Agent**: `gpt-4o` (high quality)
- **Review Agent**: `gpt-4-turbo` (balanced)

## Benefits

### 1. **No Code Deploys for Model Changes**
Change the model in Arthur → immediate effect (no redeploy needed)

### 2. **Per-Agent Model Optimization**
```
Plan Agent     → gpt-4o-mini  (fast planning)
Websearch      → gpt-4o-mini  (simple extraction)
GitHub Search  → gpt-4o-mini  (simple extraction)
Draft Agent    → gpt-4o       (quality writing)
Review Agent   → gpt-4o       (thorough review)
```

### 3. **A/B Testing**
Create prompt versions with different models:
- `production` → gpt-4o
- `canary` → gpt-4-turbo
- `experiment` → o1-mini

### 4. **Cost Optimization**
Use cheaper models where appropriate:
- Planning: `gpt-4o-mini` @ $0.15/1M tokens
- Drafting: `gpt-4o` @ $2.50/1M tokens
- Saves ~94% on planning costs!

### 5. **Centralized Management**
All model configuration in Arthur:
- Audit trail of model changes
- Version control for prompts
- Easy rollback to previous models

## Agent Definitions

Agents are still defined with a default model in `src/mastra/agents/index.ts`:

```typescript
export const planAgent = new Agent({
  name: "planAgent",
  model: openai("gpt-4o"),  // Default fallback
  instructions: "",  // Loaded from Arthur
});
```

But the **actual model used is overridden** by the prompt configuration at runtime via the `model` parameter in `agent.generate()`.

## Testing

The test harness in `scripts/test-harness.ts` uses the same dynamic model resolution, ensuring:
- Tests use the same models as production
- Model changes are automatically tested
- Consistent behavior across environments

## Future Enhancements

### Support Additional Providers

```typescript
// In model-resolver.ts
case "anthropic":
  return anthropic(modelName);

case "google":
  return google(modelName);

case "mistral":
  return mistral(modelName);
```

### Model Configuration Parameters

Arthur prompts can include `config` object:
```json
{
  "model_provider": "openai",
  "model_name": "gpt-4o",
  "config": {
    "temperature": 0.7,
    "max_tokens": 1000,
    "top_p": 0.9
  }
}
```

These could be passed to `agent.generate()` as well.

### Fallback Chain

```typescript
function resolveModel(provider: string, modelName: string) {
  try {
    return getModel(provider, modelName);
  } catch {
    console.warn(`Model ${modelName} not available, trying fallback`);
    return openai("gpt-4o");  // Fallback
  }
}
```

## Summary

Dynamic model selection provides:
- ✅ Flexibility to change models without code changes
- ✅ Per-agent model optimization
- ✅ Cost optimization opportunities
- ✅ A/B testing capabilities
- ✅ Centralized management in Arthur
- ✅ Full tracing visibility (model used is logged)

All while maintaining code simplicity and unified tracing!
