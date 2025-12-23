# Customer Support Agent - Arthur AI

This is an AI-powered customer support agent built with [Mastra](https://mastra.ai) and integrated with the Arthur GenAI Engine. The agent helps answer questions about Arthur AI products by searching documentation and GitHub repositories.

## Architecture

The agent uses a multi-agent workflow with 5 specialized agents:

1. **Plan Agent** - Analyzes the user's question and creates a structured plan
2. **Websearch Agent** - Searches Arthur AI documentation at docs.arthur.ai
3. **GitHub Agent** - Searches the arthur-engine GitHub repository for code examples
4. **Draft Agent** - Drafts a response based on search results
5. **Review Agent** - Reviews and finalizes the response

The websearch and GitHub agents run in parallel for efficiency.

### Dynamic Model Selection

Each agent uses the **model specified in its Arthur prompt configuration**. When a prompt is fetched from Arthur, it includes:
- `model_provider` (e.g., "openai")
- `model_name` (e.g., "gpt-4o", "gpt-4-turbo")

The agent automatically uses this model for inference, allowing you to:
- Change models without code changes (just update the prompt in Arthur)
- Use different models for different agents (e.g., faster models for planning, more capable models for drafting)
- A/B test different models by changing prompt configurations

## Prerequisites

- Node.js 18+
- Yarn package manager
- OpenAI API key
- Arthur Engine instance with API access
- Tavily API key (for documentation search)
- GitHub Personal Access Token (for code search)

## Getting Started

### 1. Set up environment variables

```bash
# Copy the example file
cp .env.example .env
```

Then edit the `.env` file with your actual values:

```bash
# OpenAI API Configuration
OPENAI_API_KEY=your-openai-api-key-here

# Arthur Engine Configuration
ARTHUR_BASE_URL=https://your-arthur-instance.com
ARTHUR_API_KEY=your-arthur-api-key-here
ARTHUR_TASK_ID=your-arthur-task-id-here

# Tavily Search API
TAVILY_API_KEY=your-tavily-api-key-here

# GitHub API
GITHUB_TOKEN=your-github-token-here

# Logging Configuration (optional)
LOG_LEVEL=info
```

### 2. Install dependencies

```bash
yarn install
```

### 3. Configure Arthur Prompts

The customer support agent uses the Arthur GenAI Engine to manage prompts. You need to create **5 prompts** in your Arthur task, each with the tag `production`.

#### Prompt 1: `mastra-agent-support-plan`

**System Message:**
```
You are a planning assistant for Arthur AI customer support. Your task is to analyze the user's question and create a structured plan for answering it.

Determine what information is needed to answer the question:
- Does the question require searching Arthur AI documentation? (features, usage, concepts)
- Does the question require searching code examples? (implementation, APIs, configuration)

Create search queries that will be used to find relevant information.

Return your response in the following JSON format:
{
  "plan": "Detailed plan for answering the question",
  "needsDocs": true/false,
  "needsCode": true/false,
  "searchQueries": {
    "docs": "Query for documentation search (if needsDocs is true)",
    "code": "Query for code search (if needsCode is true)"
  }
}
```

**User Message:**
```
{{ userQuestion }}
```

**Variables:**
- `userQuestion`: The user's question (string)

---

#### Prompt 2: `mastra-agent-support-websearch`

**System Message:**
```
You are a documentation search specialist for Arthur AI. Your task is to use the websearch tool to find relevant information from Arthur AI documentation at docs.arthur.ai.

Use the websearch tool to search for information related to the query. Review the search results and extract the most relevant information.

Return your response in the following JSON format:
{
  "summary": "Summary of findings from the documentation",
  "relevantInfo": ["Key point 1", "Key point 2", "Key point 3"],
  "sources": ["URL 1", "URL 2", "URL 3"]
}
```

**User Message:**
```
Search Query: {{ searchQuery }}

Context/Plan: {{ plan }}
```

**Variables:**
- `searchQuery`: The search query for documentation (string)
- `plan`: The plan created by the plan agent (string)

---

#### Prompt 3: `mastra-agent-support-github`

**System Message:**
```
You are a code search specialist for Arthur AI. Your task is to use the github search tool to find relevant code examples and implementation details from the arthur-engine repository.

Use the github search tool to search for code related to the query. Review the search results and extract the most relevant code snippets and patterns.

Return your response in the following JSON format:
{
  "summary": "Summary of findings from the code repository",
  "relevantInfo": ["Code pattern 1", "Code pattern 2", "Implementation detail 3"],
  "sources": ["GitHub URL 1", "GitHub URL 2", "GitHub URL 3"]
}
```

**User Message:**
```
Search Query: {{ searchQuery }}

Context/Plan: {{ plan }}
```

**Variables:**
- `searchQuery`: The search query for code (string)
- `plan`: The plan created by the plan agent (string)

---

#### Prompt 4: `mastra-agent-support-draft`

**System Message:**
```
You are a technical writer for Arthur AI customer support. Your task is to draft a comprehensive response to the user's question based on the information gathered from documentation and code searches.

Guidelines:
- Synthesize information from both documentation and code results
- Provide clear, accurate, and helpful answers
- Include relevant code examples when available
- Cite sources for all information
- Be concise but thorough
- Use technical language appropriately for the audience

Return your response in the following JSON format:
{
  "response": "The drafted response to the user's question",
  "confidence": "high/medium/low - your confidence in the response",
  "sources": ["Source URL 1", "Source URL 2", "Source URL 3"]
}
```

**User Message:**
```
User Question: {{ userQuestion }}

Documentation Results:
{{ docsResults }}

Code/GitHub Results:
{{ githubResults }}
```

**Variables:**
- `userQuestion`: The user's original question (string)
- `docsResults`: JSON string of documentation search results
- `githubResults`: JSON string of GitHub search results

---

#### Prompt 5: `mastra-agent-support-review`

**System Message:**
```
You are a quality reviewer for Arthur AI customer support. Your task is to review the drafted response against the original plan and ensure it fully answers the user's question.

Review the draft for:
- Completeness - Does it address all aspects of the question?
- Accuracy - Is the information correct and well-sourced?
- Clarity - Is it easy to understand?
- Relevance - Does it stay on topic?

Make any necessary improvements and produce the final polished response.

Return your response in the following JSON format:
{
  "finalResponse": "The final polished response to the user",
  "completeness": "Assessment of how completely the question was answered",
  "sources": ["Final list of source URLs"]
}
```

**User Message:**
```
User Question: {{ userQuestion }}

Original Plan: {{ plan }}

Draft Response:
{{ draftResponse }}
```

**Variables:**
- `userQuestion`: The user's original question (string)
- `plan`: The original plan from the plan agent (string)
- `draftResponse`: JSON string of the draft response

---

### 4. Obtain API Keys

#### OpenAI API Key
1. Go to https://platform.openai.com/
2. Create an account or sign in
3. Navigate to API keys and create a new key

#### Arthur Engine Access
1. Contact your Arthur AI administrator for:
   - Arthur instance URL (ARTHUR_BASE_URL)
   - API key (ARTHUR_API_KEY)
   - Task ID (ARTHUR_TASK_ID)

#### Tavily API Key
1. Go to https://tavily.com/
2. Sign up for an account
3. Get your API key from the dashboard

#### GitHub Personal Access Token
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate a new token (classic)
3. Select scope: `public_repo` (for public repositories)
4. Copy the token

### 5. Start the development server

```bash
yarn dev
```

The application will be available at http://localhost:3000

## Running the Agent

### Start the Development Server

```bash
yarn dev
```

The chat interface will be available at http://localhost:3000

### Run with Debug Logging

```bash
yarn dev:debug
```

## Demo Setup Scripts

The customer support agent includes several scripts to help you bootstrap and set up demo environments with realistic data.

### 1. Bootstrap Extract - Download Data from Existing Task

Extract all configuration from an existing Arthur task (prompts, evals, transforms, datasets):

```bash
yarn bootstrap:extract
```

This will save all task data to `scripts/bootstrap-data/` including:
- Task configuration
- All 5 agent prompts with templates
- LLM evaluations
- Continuous evaluations with transforms
- Test question datasets

### 2. Setup New Task - Create Task from Bootstrap Data

Create a complete new Arthur task using the bootstrap data:

```bash
yarn setup:new-task "Demo Customer Support Agent"
```

This will create:
- A new task with the specified name
- 5 prompts (tagged as `production`)
- 3 LLM evals
- 2 transforms
- 3 continuous evals
- Test questions dataset

### 3. Test Harness - Run Test Dataset Through API

Test the agent with multiple questions:

1. **Add your test questions** to `scripts/test-questions.json`:

```json
{
  "questions": [
    {
      "id": "q1",
      "question": "What metrics does the Arthur platform support?",
      "category": "metrics"
    }
  ]
}
```

2. **Run the test harness**:

```bash
yarn test:questions
```

The test harness will:
- Process each question through the full agent workflow
- Generate unified traces for each question in Arthur
- Save detailed results to `scripts/test-results-{timestamp}.json`
- Print a summary of successes/failures and average duration

Run with debug logging:

```bash
yarn test:questions:debug
```

### 4. Demo Harness - Generate Multi-Day Demo Data

Create a realistic demo dataset with 100 inferences spread over 10 days:

```bash
yarn test:demo
```

This special demo version will:
- Run 100 inferences (10 loops through 10 test questions)
- Backdate timestamps to show 10 inferences per day over 10 days
- Start from today and go backwards in time
- Spread each inference throughout the day (8am-8pm)
- Run multiple inferences in parallel (5 concurrent by default)
- Save results to `scripts/demo-results-{timestamp}.json`
- Create traces in Arthur with backdated timestamps

**Performance**: ~10-20 minutes with parallel execution (default)

This is useful for:
- Creating realistic historical datasets for demos
- Testing date-based filtering and analytics features
- Preparing presentations that show trends over time

Run with debug logging:

```bash
yarn test:demo:debug
```

## Available Scripts

### Development
- `yarn dev` - Starts the development server with Turbopack
- `yarn dev:debug` - Starts development server with debug logging enabled
- `yarn build` - Builds the application for production
- `yarn start` - Starts the production server
- `yarn lint` - Runs ESLint for code linting

### Demo Setup
- `yarn bootstrap:extract` - Extract data from existing Arthur task
- `yarn setup:new-task <name>` - Create new task from bootstrap data
- `yarn test:questions` - Run test harness with questions from `scripts/test-questions.json`
- `yarn test:questions:debug` - Run test harness with debug logging
- `yarn test:demo` - Generate multi-day demo data (100 inferences over 10 days)
- `yarn test:demo:debug` - Run demo harness with debug logging

## How It Works

### Multi-Agent Workflow

1. **User submits a question** via the chat interface

2. **Plan Agent analyzes** the question and creates a structured plan:
   - Determines if documentation search is needed
   - Determines if code search is needed
   - Creates optimized search queries

3. **Parallel Search Phase** (if needed):
   - **Websearch Agent** searches docs.arthur.ai using Tavily API
   - **GitHub Agent** searches arthur-ai/arthur-engine using GitHub API
   - Both agents run simultaneously for efficiency

4. **Draft Agent synthesizes** information from search results:
   - Combines findings from documentation and code
   - Creates a comprehensive draft response
   - Includes citations and sources

5. **Review Agent finalizes** the response:
   - Reviews draft against original plan
   - Ensures completeness and accuracy
   - Produces polished final response

6. **User receives** the final answer with sources

### Arthur Engine Integration

All agent prompts are managed through the Arthur GenAI Engine, enabling:

- **Version control** for prompts with tagging (production, staging, etc.)
- **Centralized management** of all agent instructions
- **Templating** with variable substitution
- **Observability** with full trace capture of agent execution
- **A/B testing** of different prompt versions

Traces are automatically sent to Arthur Engine via OpenTelemetry, providing:
- Complete visibility into agent execution
- Token usage tracking
- Performance metrics
- Error monitoring

## Project Structure

```
customer-support-agent/
├── src/
│   ├── app/
│   │   ├── api/chat/route.ts      # Main chat API endpoint
│   │   ├── layout.tsx              # Next.js layout
│   │   ├── page.tsx                # Home page with chat UI
│   │   └── globals.css             # Global styles
│   ├── components/
│   │   ├── ChatInterface.tsx       # Main chat component
│   │   └── MessageBubble.tsx       # Message display component
│   └── mastra/
│       ├── index.ts                # Mastra configuration
│       ├── agents/
│       │   └── index.ts            # All 5 agent definitions
│       ├── tools/
│       │   ├── websearch.ts        # Tavily documentation search
│       │   ├── githubSearch.ts     # GitHub code search
│       │   └── index.ts
│       ├── lib/
│       │   └── arthur-api-client/  # Arthur API client
│       └── observability/
│           └── arthur/             # Arthur tracing integration
├── .env.example
├── package.json
├── tsconfig.json
└── README.md
```

## Example Usage

**User:** "How do I set up hallucination detection in Arthur Engine?"

**Agent Workflow:**
1. Plan Agent determines both docs and code search are needed
2. Websearch Agent searches docs.arthur.ai for hallucination documentation
3. GitHub Agent searches for hallucination implementation examples
4. Draft Agent combines findings into a response with code examples
5. Review Agent ensures completeness and accuracy
6. User receives answer with links to documentation and code examples

## Troubleshooting

### Agent doesn't return a response
- Check that all 5 prompts are created in Arthur Engine with the `production` tag
- Verify environment variables are set correctly
- Check console logs for specific errors

### "Prompt not found" error
- Ensure the prompt name matches exactly (e.g., `mastra-agent-support-plan`)
- Verify the prompt has the `production` tag in Arthur Engine
- Check that ARTHUR_TASK_ID is correct

### Search tools return empty results
- Verify TAVILY_API_KEY is valid
- Check that GITHUB_TOKEN has the correct permissions
- Ensure network connectivity to APIs

### Traces not appearing in Arthur
- Verify ARTHUR_BASE_URL, ARTHUR_API_KEY, and ARTHUR_TASK_ID
- Check that the Arthur Engine endpoint is accessible
- Review console logs for trace export errors

## Documentation

- [Mastra Documentation](https://mastra.ai/en/docs)
- [Arthur AI Documentation](https://docs.arthur.ai)
- [Next.js Documentation](https://nextjs.org/docs)
- [Tavily API Documentation](https://docs.tavily.com)
- [GitHub REST API Documentation](https://docs.github.com/en/rest)

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is licensed under the MIT License - see the LICENSE file for details.
