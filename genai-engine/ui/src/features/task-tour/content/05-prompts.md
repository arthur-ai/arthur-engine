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
  - id: create-prompts-in-playground
    title: Draft variants in the playground
  - id: run-experiment
    title: Run an experiment
---

## intro

A prompt is a collection of messages, variables, and a model — change any of them and you've got a candidate fix. The playground lets you try variations side-by-side, and Experiments run those candidates against your dataset and evals so you can ship with confidence.

## scenario

Inspect the existing prompt, open the playground and draft 2–3 variants that fix the readability failure, then run an experiment against the dataset and evals to see which variant wins.

## step: open-prompts

Click Prompt in the sidebar to see the prompts powering this agent.

## step: open-prompts-tab

Click the **Prompts** tab to see the prompt library for this task.

## step: inspect-prompt

Click the top prompt in the list. Each prompt is a bundle of messages, variables, and a model — change any of those and you've got a new version worth comparing.

## step: create-prompts-in-playground

Open a notebook from the Notebooks tab, then use Add Prompt to draft 2–3 variants that tighten the system prompt for readability. You can also try a different model or tweak variables — anything that might fix the failure. (Mark complete when done.)

## step: run-experiment

Click the highlighted Experiment button on the Runs tab to set up a run. Configure it with your dataset (the one with the captured failure), your candidate prompts, and the evals — then run it. This is the final ADLC checkpoint before you ship.
