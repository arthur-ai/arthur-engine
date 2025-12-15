# Customer Support Agent Demo Automation - Summary

## 🎉 What Was Created

A complete automation suite for stamping out new customer support agent tasks in the GenAI Engine.

### Files Created

#### Bootstrap & Setup Scripts
1. **`bootstrap-extract.ts`** - Extracts configuration from existing task
2. **`run-bootstrap-extract.js`** - Runner for bootstrap extract
3. **`setup-new-task.ts`** - Creates complete new task with all components
4. **`run-setup-new-task.js`** - Runner for setup
5. **`example-create-demo-tasks.sh`** - Example batch creation script

#### Documentation
1. **`BOOTSTRAP_README.md`** - Complete usage guide
2. **`AUTOMATION_SUMMARY.md`** - This file

#### Bootstrap Data (Generated)
Located in `bootstrap-data/` directory:
- `task.json` - Task configuration
- `prompts.json` - All 5 prompts with full message templates
- `eval-definitions.json` - 3 eval templates
- `test-questions.json` - 10 test questions dataset

### Package.json Scripts Added

```json
{
  "bootstrap:extract": "node scripts/run-bootstrap-extract.js",
  "setup:new-task": "node scripts/run-setup-new-task.js"
}
```

## 🚀 Quick Start

### One-Time Setup: Extract Bootstrap Data

```bash
cd /Users/zfry/git/arthur-engine/genai-engine/examples/agents/customer-support-agent
yarn bootstrap:extract
```

This extracts:
- ✅ Task details from existing task
- ✅ 5 prompts (all using gpt-4o-mini, tagged as production):
  - `mastra-agent-support-plan`
  - `mastra-agent-support-websearch`
  - `mastra-agent-support-github`
  - `mastra-agent-support-draft`
  - `mastra-agent-support-review`
- ✅ Test questions dataset

### Create New Tasks (As Many As You Want!)

```bash
# Create a single task
yarn setup:new-task "My Demo Task"

# Or use the full command
node scripts/run-setup-new-task.js "My Demo Task"
```

Each new task gets:
- ✅ 1 new agentic task
- ✅ 5 prompts (gpt-4o-mini, tagged as "production")
- ✅ 3 LLM evals:
  - `friendly-tone` - Evaluates friendliness
  - `hedging` - Detects uncertainty
  - `compliance` - Checks accuracy
- ✅ 3 continuous eval metrics (automated monitoring)
- ✅ 1 dataset with 10 test questions

## 📊 What Gets Created Per Task

```
New Task: "Demo Customer Support Agent"
├── Task (Agentic)
├── Prompts (5)
│   ├── mastra-agent-support-plan [gpt-4o-mini, production]
│   ├── mastra-agent-support-websearch [gpt-4o-mini, production]
│   ├── mastra-agent-support-github [gpt-4o-mini, production]
│   ├── mastra-agent-support-draft [gpt-4o-mini, production]
│   └── mastra-agent-support-review [gpt-4o-mini, production]
├── LLM Evals (3)
│   ├── friendly-tone [gpt-4o-mini, production]
│   ├── hedging [gpt-4o-mini, production]
│   └── compliance [gpt-4o-mini, production]
├── Continuous Evals (3)
│   ├── friendly-tone-continuous
│   ├── hedging-continuous
│   └── compliance-continuous
└── Dataset
    └── Test Questions (10 questions)
```

## 🔄 Typical Workflow

### For Demo Setup

```bash
# 1. Extract bootstrap data (one time)
yarn bootstrap:extract

# 2. Create demo tasks
yarn setup:new-task "Demo Environment - Dev"
yarn setup:new-task "Demo Environment - Staging"
yarn setup:new-task "Demo Environment - Production"

# 3. Use any task by updating .env
# Update ARTHUR_TASK_ID in .env to the task you want to use

# 4. Test the task
yarn test:questions

# 5. Generate demo data
yarn test:demo
```

### For Production

```bash
# 1. Extract from production-ready task
yarn bootstrap:extract

# 2. Create new production task
yarn setup:new-task "Production Customer Support"

# 3. Update .env with new task ID
# ARTHUR_TASK_ID=<new-task-id>

# 4. Deploy and monitor
```

## 💡 Use Cases

### 1. Demo Environments
Create separate tasks for different demo scenarios:
```bash
yarn setup:new-task "Demo - Financial Services"
yarn setup:new-task "Demo - Healthcare"
yarn setup:new-task "Demo - E-commerce"
```

### 2. Testing & Development
Create isolated environments for testing:
```bash
yarn setup:new-task "Test - Feature Branch A"
yarn setup:new-task "Test - Integration Testing"
```

### 3. Client Demos
Quickly stamp out client-specific demos:
```bash
yarn setup:new-task "Client Demo - Acme Corp"
yarn setup:new-task "Client Demo - Widget Inc"
```

### 4. Training & Education
Create learning environments:
```bash
yarn setup:new-task "Training - Week 1"
yarn setup:new-task "Training - Week 2"
```

## 🎯 Key Features

### ✅ Complete Automation
- No manual clicking in the UI
- Reproducible task creation
- Consistent configuration across tasks

### ✅ Customizable
- Edit `bootstrap-data/` files to customize:
  - Prompt templates
  - Eval criteria
  - Test questions
  - Model selection

### ✅ Production-Ready
- All prompts tagged as "production"
- Continuous monitoring enabled
- Quality evals configured

### ✅ Fast Iteration
- Create new task in ~30 seconds
- Batch create multiple tasks
- Easy to tear down and recreate

## 📝 Customization Examples

### Change Model for All Prompts

Edit `setup-new-task.ts`:
```typescript
// Change this line in createPrompts function
model_name: "gpt-4o",  // Instead of "gpt-4o-mini"
```

### Add Custom Eval

Edit `bootstrap-data/eval-definitions.json`:
```json
{
  "response-time": {
    "name": "response-time",
    "instructions": "Evaluate if the response was timely...",
    "model_name": "gpt-4o-mini",
    "model_provider": "openai"
  }
}
```

### Customize Prompt Templates

Edit `bootstrap-data/prompts.json`:
```json
{
  "mastra-agent-support-plan": {
    "messages": [
      {
        "role": "system",
        "content": "Your custom system prompt here..."
      }
    ]
  }
}
```

## 🔍 Verification

After creating a task, verify it in the Arthur UI:
1. Navigate to Tasks
2. Find your new task
3. Check Prompts tab (should see 5 prompts tagged "production")
4. Check Evals tab (should see 3 evals tagged "production")
5. Check Metrics tab (should see 3 continuous evals)
6. Check Datasets tab (should see 1 dataset with 10 questions)

## 📚 Files Reference

### Core Scripts
- `bootstrap-extract.ts` - Extracts from existing task
- `setup-new-task.ts` - Creates new task with all components
- `run-bootstrap-extract.js` - CLI runner for extract
- `run-setup-new-task.js` - CLI runner for setup

### Bootstrap Data
- `bootstrap-data/task.json` - Task metadata
- `bootstrap-data/prompts.json` - 5 prompt templates
- `bootstrap-data/eval-definitions.json` - 3 eval definitions
- `bootstrap-data/test-questions.json` - 10 test questions

### Output
- `setup-result.json` - Latest task creation results

### Documentation
- `BOOTSTRAP_README.md` - Detailed usage guide
- `AUTOMATION_SUMMARY.md` - This summary

## 🎓 Learning Resources

1. **Test the Setup**: Run `yarn test:questions` after creating a task
2. **Generate Demo Data**: Run `yarn test:demo` to create historical data
3. **Check Logs**: Look at console output for detailed progress
4. **Review Results**: Check `setup-result.json` for task details
5. **Inspect Bootstrap**: Look at `bootstrap-data/*.json` to understand structure

## 🐛 Troubleshooting

### "Bootstrap data not found"
```bash
# Run this first
yarn bootstrap:extract
```

### "Missing environment variables"
```bash
# Check your .env file has:
ARTHUR_BASE_URL=https://...
ARTHUR_API_KEY=...
ARTHUR_TASK_ID=...  # Only for bootstrap extract
```

### "Task creation failed"
- Check API key permissions
- Verify task name doesn't already exist
- Check console output for specific error
- Try again with different task name

### Rate Limiting
If creating many tasks quickly:
- Add delays between creations
- Use the example batch script which includes delays
- Wait a few seconds and retry

## 🚀 Next Steps

1. **Create Your First Demo Task**
   ```bash
   yarn setup:new-task "My First Demo"
   ```

2. **Update Your .env**
   ```bash
   ARTHUR_TASK_ID=<task-id-from-output>
   ```

3. **Test It**
   ```bash
   yarn test:questions
   ```

4. **Generate Demo Data**
   ```bash
   yarn test:demo
   ```

5. **Create More Tasks As Needed!**

---

**Bootstrap extraction completed successfully on:** Dec 14, 2025

**Extracted from task:** Customer Support Agent (57057493-ee94-47e2-8cbb-9493f423e63d)

**Ready to create unlimited demo tasks!** 🎉

