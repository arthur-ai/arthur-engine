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

A trace is the timeline of everything the agent did to produce one answer — retrieval calls, model invocations, post-processing, evals. Continuous Evals run on every trace automatically, so you can spot failure patterns the moment they happen.

## scenario

Open Observe, drill into a trace, walk through the spans, read the eval annotations, and leave manual feedback. We'll specifically call out where the **Source Attribution Eval** is failing — the agent answered without citing where the information came from — that's the signal you'll fix later in this tour.

## step: open-observe

Open the Observe view to see the trail of requests this agent has generated. Click **Observe** in the sidebar.

## step: open-trace

Open one of the traces to see what's actually inside — any trace works. Click the top row, or mark this step complete and we'll open the first trace for you.

## step: review-spans

A **trace** is the full request; each **span** is one step the agent took (retrieval, model call, post-processing). Look at latency, cost, and tokens to see where time and money are going. (Mark complete when done.)

## step: review-annotations

**Continuous Evals** attach automatically to every trace — they measure quality on every request so you catch regressions early. For the evals on this trace, notice the **Source Attribution Eval** is failing because the answer doesn't cite its source — that's the live signal we'll fix in the prompt playground. (Mark complete when done.)

## step: add-feedback

**Manual feedback** is how humans (or your own app, via the API) tell Arthur something an automated eval can't capture. Leave a quick note about this answer — developers use it to triage, and production apps can post it programmatically. (Mark complete when done.)
