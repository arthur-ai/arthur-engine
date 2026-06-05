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

Datasets hold the test cases you run before each release. You can pull real traces into a dataset and add synthetic examples to fill in gaps. In this section you'll capture the citation failure from Observe as a test case so future prompt versions have to pass it.

## scenario

Open the pre-loaded dataset to see how a test suite is structured, then go back to Observe, add the failing trace to the dataset, and (optionally) generate a few synthetic rows to widen coverage.

## step: open-datasets

Click **Dataset** in the sidebar to see the test sets on this task.

## step: open-preloaded-dataset

Click the top dataset row. This is the suite developers run to check the agent doesn't break on cases they already know about.

## step: review-dataset-rows

Each row is a test case: the inputs your agent receives and the expected output it should produce. This pre-loaded suite is what you'd run before each release.

## step: review-dataset-columns

Columns define the fields in each case. **Configure Columns** is where you add or rename input and expected-output fields.

## step: review-dataset-grow

There are three ways to add cases: **Add Row** manually, **Import** a CSV, or **Generate** synthetic rows. We'll try generating some at the end of this section.

## step: review-dataset-versions

Datasets are versioned. Each save creates a new version, and experiments pin a specific one so results stay reproducible.

## step: review-dataset-experiments

**Experiments** run your prompt candidates against this dataset and score them with your evals. We'll set one up in the Prompts section.

## step: open-traces-for-dataset

Head back to Observe to capture the failing trace as a regression case.

## step: open-trace-for-dataset

Open the trace with the failing **Source Attribution Eval** (the answer that didn't cite its source). This is the example you want future prompt versions to pass.

## step: review-trace-actions

Trace Actions is where you can promote real production behavior into reusable assets. Find the actions area before opening the dataset drawer.

## step: open-add-to-dataset

Open **Trace Actions**, then choose **Add to Dataset** to start capturing this trace as a test case.

## step: save-trace-to-dataset

Fill out the drawer to save this trace as a test case:

1. **Select a dataset** to add the row to.
2. Map columns to the trace. Use **Fill from object**, or pick a span and drill into its keys (a transform can handle this automatically).
3. Once at least one column has a value, click **Add Row**.

## step: verify-new-row

Reopen Datasets and click the same dataset. The trace you just added should appear as a new row. (Mark complete when done.)

## step: generate-synthetic

Click **Generate** to add 5–10 synthetic rows based on the examples already in the dataset. This fills in edge cases without waiting for real users to hit them. You can cancel the modal to skip this step if you'd rather move on.
