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

Before tuning prompts or swapping models, you need to know how the agent is being measured and against what bar. That way any change has an objective before-and-after.

Each eval reads a few **variables**: the agent's response, the user's question, retrieved context, etc. A **Transform** is what pulls those values out of a trace and hands them to the eval. The trace records everything the agent did; the transform picks out just the fields this eval needs to score. The **Source Attribution Eval** on this task, for example, uses a transform to extract the agent's response and checks whether it cites a source.

## scenario

Open Evaluate and look at the first evaluator. Pay attention to the model that judges each trace and the variables a transform feeds in. Together with the threshold, those are what determine whether a trace passes or fails.

## step: open-evaluate

Click Evaluate in the sidebar to see the evaluators running on this task.

## step: review-evaluator

Click the **maximize** icon on the first evaluator to open its full details. Each evaluator runs a model against a set of variables pulled from every trace, then scores the result against a threshold. That score is how Arthur decides whether a trace passes.

## step: review-evaluator-versions

Evaluators are versioned. The drawer on the left lists every version with its model and creation date, so you can see how the eval has changed and roll back if needed.

## step: review-evaluator-instructions

The **instructions** are the prompt sent to the judge model. They define what the model is being asked to score.

## step: review-evaluator-model

This is the judge model for this evaluator. Keeping it consistent across versions is what makes scores comparable over time.

## step: open-results-tab

Click the **Results** tab to see how recent traces scored against this evaluator.

## step: review-result-details

Click the first result row to open the details. You'll see the trace, the score, the explanation, and controls to rerun it if you want to dig into why it passed or failed.
