---
id: prompts
title: Experiment with prompts
kicker: Section 6 of 7
intro:
  heading: Tune, then prove it
  cta: Open Prompts
  scenario:
    label: What you'll do
steps:
  - id: open-prompts
    title: Open Prompts
  - id: open-prompts-tab
    title: Open the Prompts tab
  - id: inspect-prompt
    title: Inspect a prompt
  - id: open-in-playground
    title: Open it in the playground
  - id: duplicate-prompt-in-playground
    title: Duplicate the prompt
  - id: review-playground-prompt
    title: Review the prompt card
  - id: open-variables
    title: Open the variables panel
  - id: review-playground-controls
    title: Review variables and config
  - id: save-prompt-version
    title: Save the prompt
  - id: review-notebook
    title: Review your notebook
  - id: open-create-experiment
    title: Start an experiment
  - id: experiment-info-name
    title: Name the experiment
  - id: experiment-info-versions
    title: Pick prompt versions
  - id: experiment-info-dataset
    title: Choose the dataset
  - id: experiment-info-evaluators
    title: Add the evaluators
  - id: review-experiment-info
    title: Review the experiment setup
  - id: explain-prompt-mapping
    title: Map prompt variables
  - id: complete-prompt-mapping
    title: Review the variable mapping
  - id: explain-eval-mapping
    title: Map evaluator variables
  - id: create-experiment
    title: Create the experiment
  - id: review-experiment
    title: Watch the experiment run
---

## intro

A prompt is a bundle of messages, variables, and a model. Change any of them and you have a candidate fix. The playground lets you try variants side-by-side, and Experiments run those candidates against your dataset and evals so you have data before you commit to a change.

## scenario

Inspect the current prompt, open it in the playground, and draft a variant that fixes the citation failure (instruct the agent to tell users its answers come from Wikipedia). Then run an experiment against the dataset and evals to see which version performs better.

## step: open-prompts

Click **Prompt** in the sidebar to see the prompts powering this agent.

## step: open-prompts-tab

Click the **Prompts** tab to see the prompt library for this task.

## step: inspect-prompt

Click the highlighted prompt in the list. Each prompt is a bundle of messages, variables, and a model. Changing any of those produces a new version you can compare.

## step: open-in-playground

Click **Open in Playground** from the prompt detail view. This creates or reuses a notebook seeded with the prompt so you can iterate without touching the production version.

## step: duplicate-prompt-in-playground

Click **Duplicate Prompt** to copy the prompt into a side-by-side variant. Working from a copy keeps the original baseline intact while you make edits.

## step: review-playground-prompt

Edit the system prompt in this duplicated card so the agent cites its source. For example, instruct it to tell users the answer comes from Wikipedia. You can change the messages or swap the model.

## step: open-variables

Click **Variables** to open the panel where you set the values your prompts run against.

## step: review-playground-controls

This is the variables panel. The values here control what data your prompts run against. Review or fill them in so the experiment compares the same scenario across variants, then close the panel to continue.

## step: save-prompt-version

Click the **Save** icon on this prompt card to store it as a new version. Save at least one prompt before moving on. Each saved version is a candidate you can include in an experiment.

## step: review-notebook

This is your notebook. Prompts, variables, and config all live here so you can compare variants in one place. When you're ready to run the experiment, continue.

## step: open-create-experiment

Open the Experiment menu and choose **Create New**. The tour will stay with you inside the modal while you configure the run.

## step: experiment-info-name

Give the run a name. A clear name (and optional description) makes it easier to find later when you're looking back at results. Click **Next** when you're done.

## step: experiment-info-versions

Choose the prompt versions you want to compare. These are the saved variants from your notebook. Pick the ones worth testing, then click **Next**.

## step: experiment-info-dataset

Select the dataset and version that holds the captured failure. Every prompt version will run against the same data, so the comparison is fair. Click **Next** to continue.

## step: experiment-info-evaluators

Add the evals that will judge each result. Once your evaluators are in, click **Next**.

## step: review-experiment-info

This is the full setup: name, prompt versions, dataset, and evals. Look it over, and when it looks right, click **Configure Prompts** to wire up the variables.

## step: explain-prompt-mapping

Variable mappings tell each prompt version where to read its inputs. Map every prompt variable to the dataset column that feeds it. Exact name matches are pre-filled, but check each one and fill any that are empty. The run won't start until every variable is mapped. Click **Next** when they're all set.

## step: complete-prompt-mapping

Each prompt variable should now point at a column. Click **Configure Evals** to set up the judges, or **Create Experiment** if you skipped evals.

## step: explain-eval-mapping

Each evaluator reads its variables from a source you choose. Map the agent's **response** (and any other value the prompt generates) to **Experiment Output** so the eval scores what your new prompt actually produced, not a stored value. Map input variables like the user's question to the **Dataset Column** that holds them. Exact name matches are pre-filled, but every variable defaults to **Dataset Column**, so switch your response variables to **Experiment Output** before clicking **Next**.

## step: create-experiment

Final check. Make sure every eval variable has the right source, with response variables mapped to **Experiment Output**. Then click **Create Experiment** to start the run.

## step: review-experiment

You're now on the experiment's results page. It's running against the dataset and evals, and the page updates as each row finishes — give it a moment to complete, then compare how your prompt versions scored. Click **Next** when you're ready to move on.
