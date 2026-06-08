---
id: deploy
title: Deploy and verify
kicker: Section 7 of 7
intro:
  heading: Ship and watch
  cta: Open Prompts
  scenario:
    label: What you'll do
steps:
  - id: open-production-prompt
    title: Reopen the winning prompt
  - id: tag-production
    title: Tag the winning prompt as production
  - id: reopen-demo-agent
    title: Reopen the Demo Agent
  - id: send-verification-message
    title: Send another message
  - id: review-verification-message
    title: Review the fresh chat
  - id: verify-eval-passes
    title: Verify the eval passes
  - id: review-latest-trace
    title: Check the latest trace
---

## intro

Take the winning prompt from your experiment, tag it as production, then send another Demo Agent message and check that the **Source Attribution Eval** passes on the new trace. That's the point of the whole workflow: the failure you found in Observe gets a fix you can verify before it ships.

## scenario

Go back to the prompt detail view, promote the best experiment candidate to production, send another Demo Agent message, then check the new trace in Observe. The **Source Attribution Eval** should be green now that the agent cites its source.

## step: open-production-prompt

Open the prompt you want to ship. You tag it as production from the prompt detail view, so this takes you back to the version metadata before you promote it.

## step: tag-production

In the prompt detail view, click the tag icon next to the version chips and mark this version as production. Whichever version you tag is the one production traffic will use. (Mark complete when done.)

## step: reopen-demo-agent

Open **Demo Agent** again from the sidebar. The next chat run will use the production version you just tagged.

## step: send-verification-message

Send another general-knowledge question to generate a fresh trace with the production prompt. Using the same question as before makes for an easy before-and-after comparison.

## step: review-verification-message

Wait for the Demo Agent to finish responding, then click **Next** to check the evals on the new trace.

## step: verify-eval-passes

Open **Observe** from the sidebar to see the traces from your verification message.

## step: review-latest-trace

Open the latest trace (the one from the message you just sent) and check the evals. The **Source Attribution Eval** should be green now that the agent cites its source. That passing eval is your confirmation the fix worked.
