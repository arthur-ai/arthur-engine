# Customer Support Agent Bootstrap & Setup Automation

This directory contains automation scripts to bootstrap and stamp out new customer support agent tasks in the GenAI Engine.

## Overview

The automation consists of two main scripts:

1. **Bootstrap Extract** (`run-bootstrap-extract.js`) - Extracts configuration from an existing task
2. **Setup New Task** (`run-setup-new-task.js`) - Creates a complete new task with all components

## What Gets Created

When you run the setup script, it creates:

- ✅ **1 New Task** - A new agentic task in Arthur
- ✅ **5 Prompts** - All tagged as "production", using gpt-4o-mini:
  - `mastra-agent-support-plan` - Creates an action plan for the user query
  - `mastra-agent-support-websearch` - Searches documentation
  - `mastra-agent-support-github` - Searches code repositories
  - `mastra-agent-support-draft` - Drafts an initial response
  - `mastra-agent-support-review` - Reviews and finalizes the response
- ✅ **3 LLM Evals** - Quality evaluation criteria:
  - `friendly-tone` - Evaluates friendliness and warmth
  - `hedging` - Detects excessive uncertainty or hedging
  - `compliance` - Checks accuracy and policy compliance
- ✅ **3 Continuous Evals** - Automated metrics based on the evals above
- ✅ **1 Dataset** - Test questions for validation

## Prerequisites

1. **Environment Variables** - Make sure your `.env` file contains:
   ```bash
   ARTHUR_BASE_URL=https://your-instance.arthur.ai
   ARTHUR_API_KEY=your-api-key-here
   ARTHUR_TASK_ID=existing-task-id  # Only needed for bootstrap extract
   ```

2. **Dependencies** - Install if needed:
   ```bash
   yarn install  # or npm install
   ```

## Usage

### Step 1: Bootstrap Extract (One-time setup)

Extract the configuration from your existing customer support agent task:

```bash
cd /Users/zfry/git/arthur-engine/genai-engine/examples/agents/customer-support-agent/scripts
node run-bootstrap-extract.js
```

This will:
- Read your existing task details
- Extract all 5 prompts (production versions)
- Copy test questions
- Save everything to `bootstrap-data/` directory

**Output Files:**
- `bootstrap-data/task.json` - Task configuration
- `bootstrap-data/prompts.json` - All 5 prompts with their messages
- `bootstrap-data/eval-definitions.json` - Eval templates
- `bootstrap-data/test-questions.json` - Test dataset

### Step 2: Create New Tasks

Once you have the bootstrap data, you can create as many new tasks as you want:

```bash
node run-setup-new-task.js "My New Customer Support Agent"
```

Replace `"My New Customer Support Agent"` with your desired task name.

**What it does:**
1. Creates a new agentic task
2. Creates all 5 prompts with gpt-4o-mini, tagged as "production"
3. Creates 3 LLM evals
4. Creates 3 continuous eval metrics
5. Creates a dataset with test questions
6. Saves the results to `setup-result.json`

### Step 3: Update Your Environment

After setup completes, update your `.env` file with the new task ID:

```bash
ARTHUR_TASK_ID=<new-task-id-from-output>
```

### Step 4: Test Your New Task

Run the test harness to verify everything works:

```bash
node run-test.js
```

Or run the demo harness to generate historical data:

```bash
node run-demo.js
```

## Example Workflow

```bash
# 1. Bootstrap from existing task (one time)
node run-bootstrap-extract.js

# 2. Create first demo task
node run-setup-new-task.js "Demo Task 1"

# 3. Create second demo task
node run-setup-new-task.js "Demo Task 2"

# 4. Create production task
node run-setup-new-task.js "Production Customer Support"
```

## Directory Structure

```
scripts/
├── bootstrap-extract.ts           # Extracts data from existing task
├── run-bootstrap-extract.js       # Runner for bootstrap extract
├── setup-new-task.ts              # Creates new task with all components
├── run-setup-new-task.js          # Runner for setup
├── bootstrap-data/                # Generated bootstrap data
│   ├── task.json                  # Task configuration
│   ├── prompts.json               # All 5 prompts
│   ├── eval-definitions.json      # Eval templates
│   └── test-questions.json        # Test dataset
├── setup-result.json              # Latest setup results
└── BOOTSTRAP_README.md            # This file
```

## Customization

### Modifying Evals

Edit `bootstrap-data/eval-definitions.json` to customize the eval criteria:

```json
{
  "friendly-tone": {
    "name": "friendly-tone",
    "instructions": "Your custom eval instructions here...",
    "model_name": "gpt-4o-mini",
    "model_provider": "openai"
  }
}
```

### Modifying Prompts

Edit `bootstrap-data/prompts.json` to customize the prompt templates:

```json
{
  "mastra-agent-support-plan": {
    "messages": [
      {
        "role": "system",
        "content": "Your custom system prompt here..."
      }
    ],
    "model_name": "gpt-4o-mini",
    "model_provider": "openai"
  }
}
```

### Using Different Models

By default, all prompts and evals use `gpt-4o-mini`. To change this:

1. Edit the setup script (`setup-new-task.ts`)
2. Change the `model_name` in the `createPrompts` and `createEvals` functions
3. Optionally change `model_provider` (openai, anthropic, gemini)

### Adding More Test Questions

Edit `bootstrap-data/test-questions.json`:

```json
{
  "questions": [
    {
      "id": "q11",
      "question": "Your new question here?",
      "category": "general"
    }
  ]
}
```

## Troubleshooting

### "Bootstrap data not found"

Run `node run-bootstrap-extract.js` first to extract the bootstrap data.

### "Missing required environment variables"

Make sure your `.env` file exists and contains all required variables.

### "Error creating prompt/eval"

Check that:
1. Your API key has the correct permissions
2. The task name doesn't already exist
3. The bootstrap data files are valid JSON

### Rate Limiting

If you're creating many prompts/evals quickly, you may hit rate limits. The script will show errors for failed operations. Wait a moment and try again.

## Advanced Usage

### Scripting Multiple Tasks

Create a shell script to automate multiple tasks:

```bash
#!/bin/bash
# create-demo-tasks.sh

tasks=(
  "Demo Task Alpha"
  "Demo Task Beta"
  "Demo Task Gamma"
)

for task in "${tasks[@]}"; do
  echo "Creating: $task"
  node run-setup-new-task.js "$task"
  sleep 5  # Wait between tasks to avoid rate limiting
done
```

### Programmatic Access

You can import and use the setup functions in your own scripts:

```typescript
import { getArthurApiClient } from "../src/mastra/lib/arthur-api-client";

const apiClient = getArthurApiClient();
// Use apiClient.api.* methods to interact with Arthur
```

## Support

For issues or questions:
1. Check the console output for specific error messages
2. Verify your `.env` configuration
3. Check the Arthur UI to see what was created
4. Review the `setup-result.json` file for task details

## References

- [Test Harness Guide](./QUICK_START.md)
- [Demo Harness Guide](./DEMO_HARNESS_GUIDE.md)
- [Arthur Engine API Documentation](https://docs.arthur.ai)

