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

Reopen the winning prompt, tag it as production, then re-run the Demo Agent and confirm the **Source Attribution Eval** is green on fresh traces. That's the loop closing — the failure you found in Observe is the failure you just shipped a fix for.

## scenario

Return to the prompt detail view, promote the best experiment candidate to production, send another Demo Agent message, then return to Observe and verify the new trace clears the **Source Attribution Eval** — the agent now cites its source.

## step: open-production-prompt

Open the prompt you want to ship. The production tag is applied from the prompt detail view, so this brings you back to the version metadata before you promote it.

## step: tag-production

Open the prompt detail view, click the tag icon next to the version chips, and mark this version as production. Whichever version you tag becomes the one production traffic uses. (Mark complete when done.)

## step: reopen-demo-agent

Open **Demo Agent** again from the sidebar. Now that the winning prompt is tagged as production, the next chat run will use that promoted version.

## step: send-verification-message

Send another general-knowledge question to create a fresh trace with the production prompt. Use the same question as before if you want an easy before-and-after comparison.

## step: review-verification-message

Wait for the Demo Agent to finish responding. When the reply is complete, click **Next** so you can check the evals on the new trace.

## step: verify-eval-passes

Open **Observe** from the sidebar to see the traces your verification message produced.

## step: review-latest-trace

This is the latest trace — the one from the message you just sent. Open it to check the evals: the **Source Attribution Eval** should now be green now that the agent cites its source. That passing eval is your proof the fix held, closing the loop you started back in Observe.
