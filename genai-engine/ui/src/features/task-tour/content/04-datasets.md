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
  - id: review-dataset-rows
    title: Read a test case
  - id: review-dataset-columns
    title: Shape the columns
  - id: review-dataset-grow
    title: Grow the suite
  - id: review-dataset-versions
    title: Track versions
  - id: review-dataset-experiments
    title: Run experiments
  - id: open-traces-for-dataset
    title: Return to Observe
  - id: open-trace-for-dataset
    title: Open a failing trace
  - id: review-trace-actions
    title: Find Trace Actions
  - id: open-add-to-dataset
    title: Open Add to Dataset
  - id: save-trace-to-dataset
    title: Save the trace to the dataset
  - id: verify-new-row
    title: Confirm the new row landed
  - id: generate-synthetic
    title: Generate synthetic data (optional)
---

## intro

Datasets are the test cases your agent has to pass before every release. Promote real traces — including the readability failure you just annotated — into a dataset, then enrich it with synthetic examples so future regressions get caught automatically.

## scenario

Open the pre-loaded dataset and look at how a test suite is built, then add the failing trace from Observe into it, return to the dataset to see the new row land, and (optional) generate a few synthetic rows to broaden coverage.

## step: open-datasets

Click Dataset in the sidebar to see the test sets available on this task.

## step: open-preloaded-dataset

Click the top dataset row. This is the test suite developers use to make sure the agent doesn't regress on cases we already know matter.

## step: review-dataset-rows

Each row is a test case — the inputs your agent receives plus the expected output it should reproduce. This pre-loaded suite is what every release has to pass.

## step: review-dataset-columns

Columns define the fields of each case. **Configure Columns** is where you add or rename the input and expected-output fields.

## step: review-dataset-grow

Three ways to add cases: **Add Row** by hand, **Import** a CSV in bulk, or **Generate** synthetic rows with AI — we'll generate some at the end of this section.

## step: review-dataset-versions

Datasets are versioned. Every save creates a new version, and experiments pin a specific one so results stay reproducible.

## step: review-dataset-experiments

**Experiments** replay your prompt candidates against this dataset and score them with your evals — that's how you prove a fix before shipping. We'll set one up in the Prompts section.

## step: open-traces-for-dataset

Head back to Observe so you can capture the real failing trace as a regression case.

## step: open-trace-for-dataset

Open the trace with the failing readability eval. This is the example you want future prompt versions to pass.

## step: review-trace-actions

Trace Actions is where you can promote real production behavior into reusable assets. Find the actions area before opening the dataset drawer.

## step: open-add-to-dataset

Click **Add to Dataset** in Trace Actions to start capturing this trace as a test case.

## step: save-trace-to-dataset

Configure the drawer and save the row. This turns the observed failure into a permanent regression check.

## step: verify-new-row

Reopen Datasets and click the same dataset — the trace you just added should be a new row, ready to be replayed against future prompt versions. (Mark complete when done.)

## step: generate-synthetic

Click Generate to enrich the dataset with 5–10 synthetic rows based on the examples already captured. Synthetic data broadens test coverage without waiting for real users to hit edge cases. You can also cancel the modal to skip this optional step and keep moving.
