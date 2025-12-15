# 🚀 Customer Support Agent Demo Automation

> **Stamp out new customer support agent tasks in seconds!**

This automation suite allows you to quickly create complete, production-ready customer support agent tasks in the GenAI Engine with all prompts, evals, metrics, and datasets pre-configured.

## ✨ What You Get

Each new task includes:
- **1 Agentic Task** - Fully configured customer support agent
- **5 Prompts** - All using `gpt-4o-mini`, tagged as "production"
- **3 LLM Evals** - Quality evaluations (Friendly Tone, Hedging, Compliance)
- **3 Continuous Evals** - Automated monitoring metrics
- **1 Dataset** - 10 test questions for validation

## 🎯 Quick Start (3 Steps)

### Step 1: Extract Bootstrap Data (One Time)

```bash
cd genai-engine/examples/agents/customer-support-agent
yarn bootstrap:extract
```

This extracts all configuration from your existing task and saves it to `scripts/bootstrap-data/`.

### Step 2: Create New Task

```bash
yarn setup:new-task "My Demo Task"
```

Creates a complete new task in ~30 seconds!

### Step 3: Test It

```bash
# Update .env with new task ID
ARTHUR_TASK_ID=<task-id-from-output>

# Run test harness
yarn test:questions
```

## 📖 Full Documentation

For complete documentation, see:
- **[`scripts/BOOTSTRAP_README.md`](./scripts/BOOTSTRAP_README.md)** - Detailed usage guide
- **[`scripts/AUTOMATION_SUMMARY.md`](./scripts/AUTOMATION_SUMMARY.md)** - Feature summary

## 💡 Common Use Cases

### Create Demo Environments
```bash
yarn setup:new-task "Demo - Dev"
yarn setup:new-task "Demo - Staging"  
yarn setup:new-task "Demo - Production"
```

### Client-Specific Demos
```bash
yarn setup:new-task "Client Demo - Acme Corp"
yarn setup:new-task "Client Demo - Widget Inc"
```

### Testing & Development
```bash
yarn setup:new-task "Test - Feature Branch"
yarn setup:new-task "Test - Integration"
```

## 🎓 Example: Batch Creation

Create multiple tasks at once:

```bash
cd scripts
./example-create-demo-tasks.sh
```

This creates 3 demo tasks automatically with proper delays to avoid rate limiting.

## 📁 What's Included

```
scripts/
├── bootstrap-extract.ts              # Extracts from existing task
├── run-bootstrap-extract.js          # CLI runner
├── setup-new-task.ts                 # Creates new tasks
├── run-setup-new-task.js             # CLI runner
├── example-create-demo-tasks.sh      # Batch creation example
├── bootstrap-data/                   # Extracted configuration
│   ├── task.json                     # Task settings
│   ├── prompts.json                  # 5 prompt templates
│   ├── eval-definitions.json         # 3 eval definitions
│   └── test-questions.json           # Test dataset
├── BOOTSTRAP_README.md               # Detailed guide
└── AUTOMATION_SUMMARY.md             # Feature summary
```

## 🔧 Requirements

- Node.js 20+
- Yarn or npm
- Arthur Engine access with API key
- Existing customer support agent task (for bootstrap)

## 🎉 Success Stories

After setup, you can:
- ✅ Create unlimited demo tasks
- ✅ Each task is production-ready
- ✅ Consistent configuration across all tasks
- ✅ Easy to customize and iterate

## 🆘 Troubleshooting

### "Bootstrap data not found"
Run `yarn bootstrap:extract` first to extract the configuration.

### "Missing environment variables"
Ensure your `.env` file contains:
```bash
ARTHUR_BASE_URL=https://your-instance.arthur.ai
ARTHUR_API_KEY=your-api-key
ARTHUR_TASK_ID=existing-task-id  # Only for bootstrap
```

### Task creation fails
- Check API key has correct permissions
- Verify task name is unique
- Check console output for specific errors

## 📊 Task Structure

Each created task follows this structure:

```
Customer Support Agent Task
├── Prompts (5)
│   ├── Plan - Analyzes user question
│   ├── Websearch - Searches documentation
│   ├── GitHub - Searches code
│   ├── Draft - Creates initial response
│   └── Review - Finalizes response
├── Evals (3)
│   ├── Friendly Tone - Measures warmth
│   ├── Hedging - Detects uncertainty
│   └── Compliance - Checks accuracy
├── Continuous Evals (3)
│   └── Automated monitoring for each eval
└── Dataset
    └── 10 test questions
```

## 🎨 Customization

Edit files in `scripts/bootstrap-data/` to customize:
- **Prompt templates** - `prompts.json`
- **Eval criteria** - `eval-definitions.json`
- **Test questions** - `test-questions.json`
- **Model selection** - Edit `setup-new-task.ts`

See [BOOTSTRAP_README.md](./scripts/BOOTSTRAP_README.md) for details.

## 🚀 Next Steps

1. **Extract bootstrap data**: `yarn bootstrap:extract`
2. **Create your first demo task**: `yarn setup:new-task "My Demo"`
3. **Test it**: `yarn test:questions`
4. **Generate demo data**: `yarn test:demo`
5. **Create more tasks as needed!**

---

**Questions?** See the detailed guides in the `scripts/` directory.

**Happy stamping!** 🎉

