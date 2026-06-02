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
  - id: review-evaluator-versions
    title: Browse evaluator versions
  - id: review-evaluator-instructions
    title: Read the instructions
  - id: review-evaluator-model
    title: Check the judge model
  - id: open-results-tab
    title: Open Results
  - id: review-result-details
    title: Review a result
---

## intro

Evals are the **contract** you set with your agent. Before tuning prompts or swapping models you need to know how the agent is being measured — and against what bar — so any change can be judged objectively.

Each eval reads a few **variables** — things like the agent's response, the user's question, or retrieved context. A **Transform** is what pulls those values out of a trace and hands them to the eval: the trace records everything the agent did, and the transform picks out just the fields this eval needs to score. For example, the **Source Attribution Eval** on this task uses a transform to extract the agent's response, then checks whether that response cites where its information came from.

## scenario

Open Evaluate and inspect the first evaluator. Pay attention to the model that judges each trace and the variables a transform feeds into the eval — together with the threshold, they decide whether a trace passes or fails.

## step: open-evaluate

Click Evaluate in the sidebar to see the evaluators currently running on this task.

## step: review-evaluator

Click the **maximize** icon on the first evaluator to open its full details. Each evaluator runs a model against a set of variables pulled from every trace, then scores the result against a threshold — that's how Arthur decides whether the agent is meeting the bar.

## step: review-evaluator-versions

Evaluators are **versioned**. The drawer on the left lists every version with its model and creation date, so you can track how the eval evolved and roll back if a change regresses.

## step: review-evaluator-instructions

The **instructions** are the prompt sent to the judge model. They define exactly what the model is asked to score — the clearer the instructions, the more reliable the evaluation.

## step: review-evaluator-model

This is the **model** that judges each trace. Picking the right model — and keeping it consistent across versions — is what makes scores comparable over time.

## step: open-results-tab

Click the **Results** tab to see how those evaluator rules have scored recent traces.

## step: review-result-details

Click the first result row and review the details modal. The row-level view shows the trace, score, explanation, and rerun controls for understanding why an eval passed or failed.
