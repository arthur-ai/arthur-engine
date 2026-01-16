# Prompt Notebooks User Guide

Prompt Notebooks are persistent workspaces for developing prompts and running experiments. They provide a flexible environment where you can iterate on prompts, configure experiments, and track your work over time. This guide helps you understand how to use notebooks for prompt development and experimentation.

## Overview

A **Prompt Notebook** is a workspace that stores your prompt development state and experiment configurations. Notebooks operate in two modes: **Iteration Mode** for rapid prompt development, and **Experiment Mode** for systematic testing. When you run an experiment from a notebook, the notebook's current state becomes the experiment's configuration, and the experiment is tracked in the notebook's history.

## Core Concepts

### 1. Notebook

A notebook is a persistent container that stores your work. It has:

- **Name and description**: Metadata to help you organize your work
- **State**: The current draft configuration (prompts, variables, dataset, evaluators, mappings)
- **Experiment history**: A record of all experiments run from this notebook
- **Note**: Notebook changes are automatically saved as you work, so you can close and return to your work later.

Notebooks allow you to:

- Develop and test prompts without losing your work
- Iterate on experiment configurations
- Track the evolution of your prompts over time
- Run multiple experiments from the same configuration

### 2. Notebook State

A notebook's state is its current draft configuration. The state can include:

- **Prompts**: One or more prompts (saved or unsaved) you're working with
- **Variable mappings**: How variables are filled (manually in Iteration Mode, from dataset columns in Experiment Mode)
- **Dataset**: The test data to run prompts against (optional - required for Experiment Mode)
- **Evaluators**: Automated tests to score prompt outputs (optional - required for Experiment Mode)
- **Eval variable mappings**: How variables map to evaluators (optional)
- **Row filters**: Conditions to test on a subset of dataset rows (optional)
- **Key Point**: When you run an experiment from a notebook, the notebook's current state becomes the experiment's configuration. This means you can modify the notebook state, run an experiment, modify it again, and run another experiment - each experiment captures the state at that moment.
- **Example:**

A notebook state might contain:

- Prompt: "Answer this question: question"
- Variable mapping: `question` → dataset column `user_query`
- Dataset: "Customer Questions v2"
- Evaluator: "Answer Correctness"
- Eval mapping: `response` → experiment output, `expected_answer` → dataset column `correct_answer`

When you click "Run Experiment", this entire state becomes the configuration for a new experiment.

### 3. Iteration Mode

Iteration Mode is for rapid prompt development and testing. In this mode:

- **State contains**: Only prompts (no dataset or evaluators)
- **Variable handling**: You manually fill in variable values when testing prompts
- **Purpose**: Quick iteration on prompt design without running full experiments
- **Run behavior**: Execute prompts directly with manual inputs - no experiment is created
- **Best for**:
    - Developing new prompts
    - Testing prompt variations quickly
    - Refining prompt wording and structure
    - Exploring different approaches before committing to an experiment
- **When to use**: Use Iteration Mode when you're focused on prompt development and don't need systematic evaluation yet.

### 4. Experiment Mode

Experiment Mode is for systematic testing and evaluation. In this mode:

- **State contains**: Complete experiment configuration (prompts, dataset, evaluators, all mappings)
- **Purpose**: Run formal experiments against datasets with automated evaluation
- **Run behavior**: Creates a Prompt Experiment that runs against your dataset
- **Best for**:
    - Testing prompts on real data
    - Comparing prompt versions systematically
    - Measuring performance with evaluators
    - Production-ready testing
- **When to use**: Use Experiment Mode when you have a dataset and want to run formal experiments with evaluation.
- **Mode Detection**: The notebook automatically switches to Experiment Mode when you add a dataset to the state. It switches back to Iteration Mode if you remove the dataset.

### 5. Experiment History

Each notebook maintains a history of all experiments run from it. This history shows:

- **Experiment details**: Name, status, timestamps, row counts, costs
- **Chronological order**: Most recent experiments first
- **Quick access**: Click any experiment to view its full results

Experiment history helps you:

- Track how your prompts have evolved
- Compare results across multiple runs
- Understand what changes improved performance
- Maintain a record of your experimentation process

## Why Use Notebooks?

Notebooks provide a persistent workspace where you can develop prompts, iterate on configurations, and run multiple experiments. Unlike creating experiments directly, notebooks save your work automatically, allow you to switch between rapid iteration and systematic testing, and maintain a history of all experiments run from them.

## Common Workflows

### Workflow 1: Create Notebook and Iterate on Prompts

This workflow is ideal when you're developing new prompts and want to iterate quickly.

**Step 1: Create a Notebook**

1. Navigate to the Notebooks page for your task
2. Click "Create Notebook"
3. Enter a name and optional description
4. Click "Create" - you'll be taken to the playground

**Step 2: Develop Prompts (Iteration Mode)**

1. In the playground, add prompts and define variables
2. Your changes auto-save to the notebook
3. Test prompts by manually filling in variable values - no experiment is created
4. Iterate on prompt wording, structure, and variables

**Step 3: Continue Iterating**

1. Make changes as needed
2. Test prompts to see outputs
3. Refine until you're satisfied with the prompts

**Step 4: Add Experiment Configuration (Optional)**

1. When ready for formal testing, click "Set Config"
2. Choose to load an existing experiment configuration or create a new one
3. The notebook switches to Experiment Mode automatically
4. Your prompts remain, and the dataset/evaluators are added

**Step 5: Run Experiments**

1. Click "Run Experiment" to create an experiment from the current state
2. The experiment runs asynchronously
3. View results and experiment history in the notebook

### Workflow 2: Load Existing Experiment Configuration

This workflow lets you start from a proven experiment setup and iterate on it.

**Step 1: Open Experiment Results**

1. Navigate to an existing experiment
2. Review the results to understand what worked

**Step 2: Open in Notebook**

1. Click "Open in Notebook" on a prompt card
2. If the experiment doesn't have a notebook, one is created automatically
3. The experiment configuration is loaded into the notebook state
4. You're taken to the playground with the configuration pre-loaded

**Step 3: Modify and Iterate**

1. Modify prompts, variables, or other configuration as needed
2. Changes auto-save to the notebook
3. Run new experiments to test your changes

**Step 4: Compare Results**

1. View experiment history in the notebook
2. Compare new results with the original experiment
3. Continue iterating based on what you learn

### Workflow 3: Run Multiple Experiments from One Configuration

This workflow is useful for A/B testing different prompt variations.

**Step 1: Set Up Complete Configuration**

1. Create or open a notebook
2. Add prompts, dataset, evaluators, and mappings
3. Ensure you're in Experiment Mode (dataset is set)

**Step 2: Run First Experiment**

1. Click "Run Experiment"
2. Wait for results

**Step 3: Modify and Run Again**

1. Modify prompts (e.g., change system message, adjust variables)
2. Click "Run Experiment" again
3. A new experiment is created with the updated state

**Step 4: Compare Results**

1. View experiment history in the notebook
2. Compare pass rates, costs, and performance across experiments
3. Identify which prompt variations work best

**Step 5: Continue Iterating**

1. Make further modifications based on results
2. Run additional experiments
3. Track your progress in the experiment history

### Workflow 4: Organize Related Work

This workflow helps you organize experiments by project or use case.

**Step 1: Create Notebooks by Project**

1. Create separate notebooks for different projects or use cases
2. Use descriptive names (e.g., "Customer Support Prompts", "Content Generation")

**Step 2: Develop in Each Notebook**

1. Work on prompts specific to each project
2. Each notebook maintains its own state and history

**Step 3: Track Progress**

1. View experiment history in each notebook
2. See how each project's prompts evolved
3. Compare approaches across different notebooks

## Best Practices

- **Use Descriptive Names**: Name notebooks clearly to reflect their purpose or project
- **One Configuration, Multiple Runs**: Set up your configuration once, then run multiple experiments with prompt variations
- **Review History**: Regularly check experiment history to understand what's working
- **Organize by Project**: Create separate notebooks for different projects or use cases

## Relationship to Experiments

Notebooks and experiments work together:

- **Notebooks** are workspaces for development and iteration
- **Experiments** are formal runs that test prompts against datasets
- **Creating experiments**: When you run an experiment from a notebook, the notebook's current state becomes the experiment's configuration
- **Linking**: Experiments are linked to notebooks, so you can see all experiments run from a notebook
- **Opening experiments in notebooks**: You can open any experiment's configuration in a notebook to continue iterating
- **Key Difference**: Notebooks are mutable workspaces where you iterate. Experiments are immutable snapshots that capture a specific configuration at a point in time.

For more information about experiments, see the [Prompt Experiments User Guide](./prompt_experiments_user_guide.md).

## Examples

### Example 1: Developing a Customer Support Prompt

**Scenario**: You're creating a prompt to help customer support agents respond to common questions.

1. **Create notebook**: "Customer Support Q&A"
2. **Iteration Mode**:
    - Add a prompt with variables like `customer_question` and `product_name`
    - Manually fill in variable values to test the prompt
    - Refine the prompt wording based on outputs
3. **Switch to Experiment Mode**:
    - Add dataset: "Customer Questions v1"
    - Add evaluator: "Response Quality"
    - Map dataset columns to prompt variables
4. **Run experiments**:
    - Run experiment with initial prompt
    - Modify prompt based on results
    - Run experiment again
    - Compare results in history

### Example 2: A/B Testing Prompt Variations

**Scenario**: You want to test whether a more formal tone improves response quality.

1. **Create notebook**: "Formal vs Casual Tone Test"
2. **Set up configuration** (Experiment Mode):
    - Add dataset: "User Queries v3"
    - Add evaluator: "Tone Appropriateness"
    - Map dataset columns to prompt variables
3. **Run Experiment 1**: Use casual tone prompt
4. **Modify and Run Experiment 2**: Update prompt to formal tone, run again
5. **Compare**: View both experiments in history to compare pass rates and costs

### Example 3: Iterating from Existing Experiment

**Scenario**: An experiment showed good results, but you want to improve it further.

1. **Open experiment**: Navigate to the successful experiment
2. **Open in notebook**: Click "Open in Notebook" on a prompt card - configuration loads into notebook
3. **Modify**: Adjust the prompt based on failure cases you observed
4. **Run new experiment**: Test the improved version
5. **Compare**: See if the changes improved performance in experiment history

## Next Steps

- Learn about creating and managing prompts in Prompt Management
- Understand how to create datasets for testing
- Explore evaluator options and how to create custom evaluators
- Review the [Prompt Experiments User Guide](./prompt_experiments_user_guide.md) to understand experiment results