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
    title: Review the trace and spans
  - id: review-annotations
    title: Review the eval annotations
  - id: add-feedback
    title: Add manual feedback
---

## intro

A trace is the timeline of everything the agent did to produce one answer — retrieval calls, model invocations, post-processing, evals. Continuous Evals run on every trace automatically, so you can spot failure patterns the moment they happen.

## scenario

Open Observe, drill into a trace, walk through the spans, read the eval annotations, and leave manual feedback. We'll specifically call out where the readability eval is failing — that's the signal you'll fix later in this tour.

## step: open-observe

Click Observe in the sidebar to see the trail of requests this agent has generated.

## step: open-trace

Click the top row to open the most recent trace. Any trace works for this exercise — we'll use whichever you pick to walk through what's inside.

## step: review-spans

A trace is the full request; each span is one step the agent took (retrieval, model call, post-processing). Look at latency, cost, and tokens to see where time and money are going. (Mark complete when done.)

## step: review-annotations

Continuous Evals attach automatically to every trace. Notice the Readability Eval is failing here — that's the live signal pointing at the failure mode we're going to fix in the prompt playground. (Mark complete when done.)

## step: add-feedback

Manual feedback is how humans (or your own app, via the API) tell Arthur something an eval can't. Leave a quick note about this answer — devs use it to triage and apps can post it programmatically. (Mark complete when done.)
