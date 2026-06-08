---
id: traces
title: Look at traces
kicker: Section 4 of 7
intro:
  heading: Follow the request, span by span
  cta: Open Observe
  scenario:
    label: What you'll do
steps:
  - id: open-observe
    title: Open Observe
  - id: open-trace
    title: Open a trace
  - id: review-spans
    title: Review the trace
  - id: review-annotations
    title: Review the annotations on the trace
  - id: add-feedback
    title: Add manual feedback to the trace
---

## intro

A trace is a timeline of everything the agent did to produce one answer: retrieval calls, model invocations, post-processing, evals. Continuous Evals attach to every trace automatically, so you can see failures as soon as they show up.

## scenario

Open Observe, drill into a trace, walk through the spans, read the eval annotations, and leave some manual feedback. We'll point out where the **Source Attribution Eval** is failing (the agent answered without citing its source). That's the problem you'll fix later in the tour.

## step: open-observe

Click **Observe** in the sidebar to see the requests this agent has generated.

## step: open-trace

Open one of the traces to see what's inside. Any trace works. Click the top row, or mark this step complete and we'll open the first trace for you.

## step: review-spans

A **trace** is the full request; each **span** is one step the agent took (retrieval, model call, post-processing). Check latency, cost, and tokens to see where time and money are going. (Mark complete when done.)

## step: review-annotations

**Continuous Evals** run on every trace automatically. Notice the **Source Attribution Eval** is failing here because the answer doesn't cite its source. That's the live signal we'll address in the prompt playground. (Mark complete when done.)

## step: add-feedback

**Manual feedback** is how you (or your app, via the API) flag something an automated eval can't catch. Leave a quick note on this trace. Developers use it to triage, and production apps can post it programmatically. (Mark complete when done.)
