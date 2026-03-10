# Translator Agent

A minimal [Mastra](https://mastra.ai) agent that translates English text into French, built to demonstrate how Arthur's remote prompt management enables instant prompt updates and version rollbacks — without redeploying your application.

## How it works

The project ships in two versions, side by side:

| File | Description |
|---|---|
| `agent.js` | Hardcoded prompt — the starting point |
| `updated-agent-with-prompt-management.js` | Prompt fetched remotely from Arthur at startup |

Both expose the same `translatorAgent` and are consumed by the same `index.js` entry point. Swapping between them is the core demo: the same agent, but one phones home to Arthur for its instructions.

## Project structure

```
translater-agent/
├── lib/
│   └── arthur.js                          # Lightweight Arthur API client
├── agent.js                               # Agent with hardcoded prompt (v1)
├── updated-agent-with-prompt-management.js # Agent powered by Arthur (v2)
├── index.js                               # Entry point
├── .env                                   # Your credentials (git-ignored)
├── .env.example                           # Credential template
└── .gitignore
```

## Prerequisites

- **Node.js v20.6 or later** — required for the built-in `--env-file` flag used in `npm start`
- **An OpenAI API key**
- **An Arthur GenAI Engine instance** — for the remote prompt version only

## Setup

### 1. Install dependencies

```bash
npm install
```

### 2. Configure environment variables

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

Open `.env` and set the following:

```
OPENAI_API_KEY=your-openai-api-key-here

# Arthur Engine — only required for updated-agent-with-prompt-management.js
ARTHUR_BASE_URL=http://localhost:3030
ARTHUR_API_KEY=your-arthur-api-key-here
ARTHUR_TASK_ID=your-task-uuid-here
```

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | Your OpenAI API key, used to call `gpt-5-mini` |
| `ARTHUR_BASE_URL` | Base URL of your Arthur GenAI Engine instance |
| `ARTHUR_API_KEY` | Your Arthur API key (sent as a Bearer token) w/ Task Admin Role |
| `ARTHUR_TASK_ID` | The UUID of the Arthur task that owns the `translator-agent` project |

## Running the agent

### With the hardcoded prompt

`index.js` imports from `agent.js` by default:

```bash
npm start
```

Expected output:
```
Input: Translate to French: Good morning! I hope you have a wonderful day.
Output: Bonjour ! J'espère que vous passez une merveilleuse journée.
```

### With Arthur remote prompt management

Update the import in `index.js` to point to the Arthur-powered agent:

```js
import { translatorAgent } from "./updated-agent-with-prompt-management.js";
```

Then run:

```bash
npm start
```

Expected output:
```
Loaded prompt "translator-prompt" v3 (tags: production)
Input: Translate to French: Good morning! I hope you have a wonderful day.
Output: Bonjour ! J'espère que vous passez une merveilleuse journée.
```

The agent fetches whichever prompt version is currently tagged `production` in Arthur. No code changes or redeployments are needed to update, extend, or roll back the prompt.

## The Arthur client

`lib/arthur.js` is a lightweight wrapper around the Arthur API — no generated SDK, no extra dependencies. It reads credentials from your environment and exposes a single method:

```js
arthurClient.getPromptByTag(promptName, tag)
// → fetches GET /api/v1/tasks/{task_id}/prompts/{promptName}/versions/tags/{tag}
// → returns the full AgenticPrompt object, including a `messages` array in OpenAI format
```

## Why remote prompt management?

With a hardcoded prompt, any change — fixing a bug, adding a language, tuning tone — requires editing code and redeploying. With Arthur:

- **Update**: push a new prompt version and tag it `production` — the agent picks it up on next startup
- **Rollback**: move the `production` tag back to a previous version — instant, no code involved
- **Experiment**: tag different versions for different environments (e.g. `staging`, `production`)
