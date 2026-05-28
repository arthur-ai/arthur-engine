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
  - id: verify-eval-passes
    title: Verify the eval passes
---

## intro

Reopen the winning prompt, tag it as production, then re-run the agent and confirm the readability eval is green on fresh traces. That's the loop closing — the failure you found in Observe is the failure you just shipped a fix for.

## scenario

Return to the prompt detail view, promote the best experiment candidate to production, then return to Observe and verify a new trace clears the readability eval.

## step: open-production-prompt

Open the prompt you want to ship. The production tag is applied from the prompt detail view, so this brings you back to the version metadata before you promote it.

## step: tag-production

Open the prompt detail view, click the tag icon next to the version chips, and mark this version as production. Whichever version you tag becomes the one production traffic uses. (Mark complete when done.)

## step: verify-eval-passes

Look at the most recent trace produced by the agent. With the new production prompt in place, the Readability Eval should now be passing — that's your proof the fix held. (Mark complete when done.)
