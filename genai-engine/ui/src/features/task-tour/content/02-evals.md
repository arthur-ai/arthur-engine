---
id: evals
title: Look at evals
kicker: Section 3 of 7
intro:
  heading: Measure before you change
  cta: Open Evaluate
  scenario:
    label: What you'll do
steps:
  - id: open-evaluate
    title: Open Evaluate
  - id: review-evaluator
    title: Review an evaluator
  - id: open-results-tab
    title: Open Results
  - id: review-result-details
    title: Review a result
---

## intro

Evals are the **contract** you set with your agent. Before tuning prompts or swapping models you need to know how the agent is being measured — and against what bar — so any change can be judged objectively.

## scenario

Open Evaluate and inspect the first evaluator. Pay attention to the model that judges each trace and the variables that get fed into the eval — together with the threshold, they decide whether a trace passes or fails.

## step: open-evaluate

Click Evaluate in the sidebar to see the evaluators currently running on this task.

## step: review-evaluator

Open the first evaluator card. Each evaluator runs a model against a set of variables pulled from every trace, then scores the result against a threshold — that's how Arthur decides whether the agent is meeting the bar.

## step: open-results-tab

Click the **Results** tab to see how those evaluator rules have scored recent traces.

## step: review-result-details

Click the first result row and review the details modal. The row-level view shows the trace, score, explanation, and rerun controls for understanding why an eval passed or failed.
