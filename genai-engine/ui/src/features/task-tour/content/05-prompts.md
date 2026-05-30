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
---

## intro

A prompt is a collection of messages, variables, and a model — change any of them and you've got a candidate fix. The playground lets you try variations side-by-side, and Experiments run those candidates against your dataset and evals so you can ship with confidence.

## scenario

Inspect the existing prompt, open it in the playground, draft 2–3 variants that fix the readability failure, then run an experiment against the dataset and evals to see which variant wins.

## step: open-prompts

Click Prompt in the sidebar to see the prompts powering this agent.

## step: open-prompts-tab

Click the **Prompts** tab to see the prompt library for this task.

## step: inspect-prompt

Click the top prompt in the list. Each prompt is a bundle of messages, variables, and a model — change any of those and you've got a new version worth comparing.

## step: open-in-playground

Click **Open in Playground** from the prompt detail view. This creates or reuses a notebook seeded with the prompt so you can iterate without losing the production version.

## step: duplicate-prompt-in-playground

Click **Duplicate Prompt** to copy the seeded prompt into a side-by-side variant. Start from a copy so you can make targeted edits without losing the original baseline.

## step: review-playground-prompt

Use this duplicated prompt card to draft a tighter system prompt for readability. Try a different model or edit the messages — anything that might fix the failure.

## step: open-variables

Click **Variables** to open the panel where you fill in the values your prompts run against.

## step: review-playground-controls

This is the variables panel. The values here control what data your prompts run against — review or fill them in so the experiment compares the same scenario fairly, then close the panel to continue.

## step: save-prompt-version

Click the **Save** icon on this prompt card to store it as a new prompt version. Save at least one prompt before moving on — each saved version is a candidate you can pit against the others in an experiment.

## step: review-notebook

This is your notebook — prompts, variables, and config all live together here so you can iterate side-by-side. Take one last look. When you're ready to prove which variant actually wins, continue to set up an experiment.

## step: open-create-experiment

Open the Experiment menu and choose **Create New**. The tour will stay with you inside the modal while you configure the run.

## step: experiment-info-name

Start by naming the run — a clear name (and an optional description) makes it easy to find later when you're comparing results. Click **Next** when you're done.

## step: experiment-info-versions

Choose the candidate prompt versions you want to pit against each other. These are the saved variants from your notebook — pick the ones worth comparing, then click **Next**.

## step: experiment-info-dataset

Select the dataset and version that holds the captured failure. This is the data every prompt version will run against, so the comparison stays fair. Click **Next** to continue.

## step: experiment-info-evaluators

Add the evals that should judge each result — these decide which variant actually wins. Once your evaluators are in, click **Next**.

## step: review-experiment-info

Here's the full setup for the run — name, prompt versions, dataset, and evals. Give it a once-over, and when it looks right, click **Configure Prompts** to wire up the variables.

## step: explain-prompt-mapping

Map each prompt variable to the dataset column that should feed it. Exact name matches are filled in for you — just confirm them, then click **Next**.

## step: complete-prompt-mapping

That's your prompt-to-data wiring. When the mappings look right, click **Configure Evals** to set up the judges (or **Create Experiment** if you skipped evals).

## step: explain-eval-mapping

For each evaluator, map its variables to a dataset column or to the experiment's output. Wire them up, then click **Next**.

## step: create-experiment

This is the final review. Confirm the eval mappings, then click **Create Experiment** to launch the run.
