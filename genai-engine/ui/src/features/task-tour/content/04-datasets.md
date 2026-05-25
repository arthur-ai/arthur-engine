---
id: datasets
title: Work with datasets
kicker: Section 5 of 7
intro:
  heading: Build a test suite
  cta: Open Datasets
  scenario:
    label: What you'll do
steps:
  - id: open-datasets
    title: Open Datasets
  - id: open-preloaded-dataset
    title: Open the pre-loaded dataset
  - id: add-trace-to-dataset
    title: Add a trace to the dataset
  - id: verify-new-row
    title: Confirm the new row landed
  - id: generate-synthetic
    title: Generate synthetic data (optional)
---

## intro

Datasets are the test cases your agent has to pass before every release. Promote real traces — including the readability failure you just annotated — into a dataset, then enrich it with synthetic examples so future regressions get caught automatically.

## scenario

Open the pre-loaded dataset, then add the failing trace from Observe into it, return to the dataset to see the new row land, and (optional) generate a few synthetic rows to broaden coverage.

## step: open-datasets

Click Dataset in the sidebar to see the test sets available on this task.

## step: open-preloaded-dataset

Click the top dataset row. This is the test suite developers use to make sure the agent doesn't regress on cases we already know matter.

## step: add-trace-to-dataset

Head back to Observe, open the trace with the failing readability eval, and use 'Add to Dataset' to capture it as a test case. This is how you turn a real-world failure into a permanent regression check. (Mark complete when done.)

## step: verify-new-row

Reopen Datasets and click the same dataset — the trace you just added should be a new row, ready to be replayed against future prompt versions. (Mark complete when done.)

## step: generate-synthetic

Click Generate to enrich the dataset with 5–10 synthetic rows based on the examples already captured. Synthetic data broadens test coverage without waiting for real users to hit edge cases. (Mark complete when done — or skip if you'd rather move on.)
