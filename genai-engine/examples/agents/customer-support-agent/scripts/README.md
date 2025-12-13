# Test Harness

This directory contains the test harness for the customer support agent.

## Setup

1. **Add your test questions** to `test-questions.json`:

```json
{
  "questions": [
    {
      "id": "q1",
      "question": "What metrics does the Arthur platform support?",
      "category": "metrics"
    },
    {
      "id": "q2",
      "question": "How do I set up model monitoring?",
      "category": "setup"
    }
  ]
}
```

### Question Format

Each question object should have:
- `id`: Unique identifier for the question (e.g., "q1", "q2")
- `question`: The actual question text to ask the agent
- `category` (optional): Category tag for organizing results

## Running the Test Harness

### Install dependencies (if not already done)

```bash
yarn install
```

### Run the test harness

```bash
yarn test:questions
```

This will:
1. Read all questions from `test-questions.json`
2. Process each question through the customer support agent
3. Log progress and results to the console
4. Save detailed results to `test-results-{timestamp}.json`
5. Each question will have its own unified trace in Arthur

### Run with debug logging

```bash
yarn test:questions:debug
```

## Output

### Console Output

The test harness will print:
- Progress for each question (plan, searches, draft, review)
- Summary statistics (success/failure counts, average duration)
- Individual results for each question

### Results File

A JSON file (`test-results-{timestamp}.json`) will be created with detailed results:

```json
[
  {
    "questionId": "q1",
    "question": "What metrics does the Arthur platform support?",
    "category": "metrics",
    "answer": "Arthur supports various metrics including...",
    "sources": ["https://docs.arthur.ai/...", "..."],
    "completeness": "complete",
    "metadata": {
      "plan": "Search documentation for metrics information",
      "searchesConducted": {
        "docs": true,
        "code": false
      }
    },
    "timestamp": "2024-12-13T19:30:00.000Z",
    "durationMs": 5432
  }
]
```

## Tracing

Each test question will generate a unified trace in Arthur with:
- Root span: `test-harness-{questionId}`
- All agent calls and tool executions nested underneath
- Metadata including `testRun: true` and `questionId`

You can view these traces in the Arthur trace viewer to analyze agent behavior across multiple test questions.

## Tips

- Start with a small set of questions (3-5) to validate the harness works
- Use the `category` field to organize questions by topic
- Review the generated `test-results-*.json` files to analyze patterns
- Use Arthur's trace viewer to compare agent behavior across different questions
- The harness processes questions sequentially with a 1-second pause between each
