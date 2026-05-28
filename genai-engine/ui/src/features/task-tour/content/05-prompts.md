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
  - id: add-prompt-in-playground
    title: Add a prompt variant
  - id: review-playground-prompt
    title: Review the prompt card
  - id: review-playground-controls
    title: Review variables and config
  - id: run-experiment
    title: Run an experiment
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

## step: add-prompt-in-playground

Click **Add Prompt** to create a side-by-side variant seeded from the current notebook.

## step: review-playground-prompt

Use this new prompt card to draft a tighter system prompt for readability. Try a different model or edit the messages — anything that might fix the failure.

## step: review-playground-controls

Variables and config control what data your prompts run against. Review them before you move on so the experiment compares the same scenario fairly.

## step: run-experiment

Click the highlighted Experiment button on the Runs tab to set up a run. Configure it with your dataset (the one with the captured failure), your candidate prompts, and the evals — then run it. This is the final ADLC checkpoint before you ship.
