# Prompt Experiments User Guide

Prompt Experiments enable systematic testing and comparison of prompts against datasets with automated evaluations. This guide helps you understand how to use experiments for prompt A/B testing, improvement, and quality assurance.

## Overview

A **Prompt Experiment** runs one or more prompts against a dataset, executes evaluations, and provides detailed results for analysis. Each row in your dataset becomes a test case. Experiments run asynchronously and provide real-time progress updates.

## Why Use Prompt Experiments?

Prompt Experiments enable systematic, data-driven prompt development and optimization. Here's why they're valuable:

### Make Data-Driven Decisions

Instead of guessing which prompt works best, experiments give you concrete metrics. You can:

- **Compare prompts objectively**: Test multiple prompts on the same inputs and see which performs better
- **Identify patterns**: Discover which types of inputs cause failures or successes
- **Track improvements**: Measure how prompt changes affect performance over time

### Save Time and Reduce Manual Work

Running prompts manually on test cases is tedious and error-prone. Experiments automate:

- **Batch execution**: Run prompts on hundreds or thousands of test cases automatically
- **Consistent evaluation**: Apply the same evaluation criteria across all test cases

### Improve Quality Assurance

Before deploying prompts to production, experiments help ensure quality:

- **Catch failures early**: Identify edge cases and failure modes before users encounter them
- **Validate improvements**: Confirm that prompt changes actually improve performance
- **Document performance**: Create a record of how prompts perform on your test data

### Enable Systematic Iteration

Experiments support an iterative improvement workflow:

- **Clone and modify**: Start from existing experiments and make incremental changes
- **Compare versions**: Test new prompts alongside proven ones to measure improvement
- **Track history**: See how your prompts have evolved and what worked
- **Promote to Production**: Promote the best prompts to production and integrate them into your applications with one click

## Core Concepts

### 1. Prompt

A prompt is a set of messages and instructions sent to a language model to generate outputs. It typically includes system messages (defining the model's role), user messages (the actual request), and can contain variables (like `user_query` or `context`) that get filled in with values, either from the dataset, or by you. When you run an experiment, each prompt executes against each row of your dataset, with variables replaced by the corresponding column values. Prompts can be:

- **Saved Prompts**: Versioned prompts stored in Prompt Management. These are reusable across experiments and can be referenced by name and version.
- **Unsaved Prompts**: Ad-hoc prompts defined directly in the experiment. These are useful for quick testing without creating a saved prompt first.

You can test multiple prompts (both saved and unsaved) in a single experiment to compare their performance.

**Example:**

```
System message: "You are a helpful assistant that answers questions concisely."
User message: "Answer this question: {{question}}"
```

This prompt has one variable: `question`, which will be filled with values from your dataset

### 2. Dataset

A dataset contains test data organized in rows and columns. Each row represents a test case, and columns contain the input data. When creating an experiment, you:

- Select a dataset and version
- Optionally filter rows using column name-value pairs (AND logic - all conditions must match)
- Map dataset columns to prompt variables

**Example:**

A dataset with two rows:

| question | expected_answer |
| --- | --- |
| "What is 2+2?" | "4" |
| "What is the capital of France?" | "Paris" |

Each row becomes a test case in your experiment.

### 3. Eval (Evaluator)

An evaluator is an automated test that scores prompt outputs. Evaluators can check for:

- Quality metrics (e.g., correctness, relevance, completeness)
- Safety checks (e.g., toxicity, bias)
- Custom criteria defined by your team

Each evaluator requires specific input variables, which can come from:

- **Dataset columns**: Static values from your test data
- **Experiment output**: Values extracted from prompt outputs

**Example:**

An evaluator called "Answer Correctness" that checks if the prompt's answer matches the expected answer. It requires:

- `response`: The prompt's output
- `expected_answer`: The correct answer

For each test case, it compares the response to the expected answer and returns a pass/fail score.

### 4. Mappings

Mappings connect your dataset to prompts and evaluators:

- **Prompt Variable Mappings**: Map dataset columns to prompt variables. For example, map a `user_query` column to a `query` variable in your prompt.
- **Eval Variable Mappings**: Map dataset columns or prompt outputs to evaluator variables. For example, map the prompt's output content to an evaluator's `response` variable.

**Example:**

Using the prompt and dataset examples above:

**Prompt Variable Mapping:**

- Dataset column `question` → Prompt variable `question`

**Eval Variable Mappings:**

- Experiment output (prompt's response) → Eval variable `response`
- Dataset column `expected_answer` → Eval variable `expected_answer`

When the experiment runs:

- Row 1: `question` = "What is 2+2?" → Prompt executes → Gets response → Eval compares response to "4"
- Row 2: `question` = "What is the capital of France?" → Prompt executes → Gets response → Eval compares response to "Paris"

### 5. Results

Experiment results include:

- **Summary Statistics**: Overall pass rates, costs, and completion status
- **Per-Prompt Performance**: Evaluation scores for each prompt across all test cases
- **Test Case Details**: Individual results showing inputs, rendered prompts, outputs, and evaluation scores
- **Cost Tracking**: Total cost per test case and per prompt

**Example:**

After running the experiment with the examples above, you might see:

**Test Cases:**

| Test Case | Input | Rendered Prompt | Output | Eval Result | Cost |
| --- | --- | --- | --- | --- | --- |
| 1 | `question = "What is 2+2?"` | "Answer this question: What is 2+2?" | "4" | ✅ Pass (response matches expected answer "4") | $0.001 |
| 2 | `question = "What is the capital of France?"` | "Answer this question: What is the capital of France?" | "Paris" | ✅ Pass (response matches expected answer "Paris") | $0.001 |

**Summary:**

| Metric | Value |
| --- | --- |
| Total test cases | 2 |
| Passed | 2 |
| Failed | 0 |
| Pass rate | 100% |
| Total cost | $0.002 |

### 6. Prompt Experiment

A Prompt Experiment brings together all the concepts above into a systematic testing configuration. It defines:

- **Prompts to test**: One or more prompts (saved or unsaved) to evaluate
- **Dataset**: The test data to run prompts against
    - **Row filters** (optional): Conditions to test on a subset of dataset rows
- **Evaluations**: Automated tests to score prompt outputs
- **Variable mappings**: How dataset columns map to prompt and evaluator variables

When you run an experiment, it creates a test case for each row in your dataset (or filtered subset), executes each prompt with the mapped variables, runs evaluations, and collects results.

## Common Workflows

### Workflow 1: Create and Iterate Experiment from Scratch

This workflow is ideal when you're starting fresh and want to test new prompts.

**Step 1: Create a New Experiment**

1. Navigate to the Prompt Experiments page for your task
2. Click "Create Experiment"
3. Enter a name and optional description

**Step 2: Select Prompts**

1. Choose a saved prompt from the dropdown
2. Select one or more versions of that prompt to test (e.g., Prompt A v1, Prompt A v2, Prompt A v4)

**Step 3: Select Dataset**

1. Choose a dataset from the dropdown
2. Select a dataset version
3. (Optional) Add row filters to test on a subset

**Step 4: Select Evaluators**

1. Add one or more evaluators to score prompt outputs
2. Select the version of each evaluator you want to use

**Step 5: Map Prompt Variables**

1. For each variable required by your prompts, select the corresponding dataset column
2. The system validates that all required variables are mapped

**Step 6: Configure Evaluators**

1. For each evaluator, map its required variables:
    - Map dataset columns to evaluator variables
    - Or map prompt outputs to evaluator variables (using JSON paths)

**Step 7: Create Experiment**

1. Review your configuration summary
2. Click "Create Experiment" to start execution
3. The experiment runs asynchronously - results will populate automatically, and you can navigate away and return later

**Step 8: Analyze Results**

1. View the experiment detail page to see results as they populate
2. Review summary statistics and per-prompt performance once complete
3. Click on individual prompts to see detailed results
4. Click on test cases to see inputs, outputs, and evaluation scores

**Step 9: Iterate**

1. Clone the experiment to create a new version with modifications
2. Or create a new experiment based on what you learned

### Workflow 2: Load Existing Experiment Configuration with New Prompts

This workflow is useful when you want to test new prompts using a proven experiment setup.

**Step 1: Start from Existing Experiment**

1. Navigate to an existing experiment
2. Click "Create from Existing" or use the clone functionality
3. The experiment configuration will be pre-filled

**Step 2: Modify Prompts**

1. Add new prompts (saved or unsaved) to test alongside existing ones
2. Remove prompts you no longer want to test
3. Keep the same dataset, evaluators, and mappings

**Step 3: Adjust as Needed**

1. Review variable mappings (may need updates if new prompts have different variables)
2. Verify evaluator configurations still make sense
3. Update experiment name and description

**Step 4: Run and Compare**

1. Create the new experiment
2. Compare results with the original experiment to see how new prompts perform

### Workflow 3: Deep Dive into a Single Prompt

This workflow helps you understand how a specific prompt performs across all test cases.

**Step 1: Open Experiment Results**

1. Navigate to a completed experiment
2. Review the summary statistics

**Step 2: Select a Prompt**

1. Click on a prompt card in the summary view to see detailed results for all test cases
2. Or click "Open in Notebook" on the prompt card to open the prompt in a notebook with the experiment configuration (dataset, evaluators, mappings) pre-loaded, allowing you to iterate directly

**Step 3: Analyze Performance**

1. Review evaluation performance metrics (pass rates, scores)
2. Browse test case results in the table
3. Use pagination to navigate through all test cases

**Step 4: Inspect Individual Test Cases**

1. Click on a test case row to see full details
2. Review:
    - Input variables used
    - Rendered prompt (with variables filled in)
    - Prompt output (content, tool calls, cost)
    - Evaluation results (scores, explanations)

**Step 5: Identify Patterns**

1. Filter or search for specific patterns
2. Look for common failure modes
3. Identify inputs where the prompt excels or struggles

**Step 6: Take Action**

1. **Open in Notebook**: Click the "Open in Notebook" button on the prompt card to open the prompt in a notebook with the existing experiment configuration pre-loaded. This allows you to iterate on the prompt directly while preserving the dataset, evaluators, and variable mappings from the experiment.
2. Use insights to refine prompts
3. Create new experiments to test improvements
4. Document findings for your team

## Understanding Experiment Status

Experiments progress through several statuses:

- **Queued**: Experiment is waiting to start execution
- **Running**: Experiment is actively executing prompts and evaluations
- **Completed**: All test cases finished successfully
- **Failed**: Experiment encountered an error and stopped

Individual test cases also have statuses:

- **Queued**: Waiting to be processed
- **Running**: Prompt execution in progress
- **Evaluating**: Evaluations running on prompt output
- **Completed**: Test case finished successfully
- **Failed**: Test case encountered an error

You can monitor progress in real-time - the UI auto-refreshes while experiments are running.

## Best Practices

- **Iterate Incrementally**: Make small changes and test them systematically rather than large overhauls
- **Compare Systematically**: Test multiple prompt versions in the same experiment for fair comparison
- **Review Explanations**: Don't just look at pass/fail - read evaluator explanations to understand why prompts succeed or fail
- **Document Findings**: Use experiment descriptions to note what changed and what you learned

## Relationship to Notebooks

Prompt Experiments can be created from and linked to **Prompt Notebooks**. Notebooks provide a workspace for iterating on prompt configurations before running experiments. Key points:

- **Notebooks** are draft workspaces where you can develop and test prompts
- **Experiments** are formal runs that test prompts against datasets
- You can create experiments from notebook configurations
- Experiments can be linked back to notebooks for organization

For more information about notebooks, see the [Prompt Notebooks User Guide](./prompt_notebooks_user_guide.md).

## Next Steps

- Learn about creating and managing prompts in Prompt Management
- Understand how to create datasets for testing
- Explore evaluator options and how to create custom evaluators
- Review experiment results to improve your prompts iteratively