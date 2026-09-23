# Open-sourcing the discovery queries

**Status:** accepted, shipped, and now history · **Decided:** 2026-08 · **Scope:** the queries and
the detection catalog, never the collector

A decision record, kept for the reasoning rather than the instructions. The split is complete:
the queries, the runner, the catalog and the test suite are
[`osquery-ai-discovery`](https://github.com/arthur-ai/osquery-ai-discovery)'s, vendored here at a
pinned ref, and what is left in this tree is the deployable. For how the two fit together see
[`architecture.md`](architecture.md); for what is vendored today, `vendor/osquery-ai-discovery/VERSION`.

## What was decided

The queries answer a question nobody has a good public answer to: *what AI agents are on this
machine, and what can they reach?* That is generic osquery knowledge and it gets better with more
contributors. The collector — the fold, the Jamf poller, the app-plane publisher — is Arthur's
product and stayed private.

MIT, matching `arthur-engine`, so a consumer vendoring it faces no new legal question.

## The catalog was the contentious half, and it is the whole point

Matching runs in the collector (D20). That decides *where* signatures are evaluated; it says
nothing about *who authors them*. "OpenClaw's bundle id is `ai.openclaw.mac`, and it also ships via
npm and a curl installer" is exactly the knowledge a community produces better than a vendor —
the way ClamAV signatures, Sigma rules and osquery packs already work.

It is also, empirically, the thing we got wrong: five catalog corrections during one build week,
one of which — `bot.molt.mac` — was plausible, came from the vendor's own Homebrew cask metadata,
and matched nothing on any Mac anywhere. Hence the rule that a signature contribution requires a
passing VM scenario rather than a plausible-looking identifier.

Keeping it closed would have meant Arthur alone tracking a landscape that changes weekly.

## What it cost, honestly

- **A competitor can take the signatures wholesale.** MIT has no copyleft. But the value is in
  *maintenance*, not contents: any week's list is cheap to copy, staying correct is the expensive
  part. Open sourcing shifts who pays for upkeep rather than giving away an asset.
- **Public queries are a roadmap.** Anyone reading them learns what Arthur detects, and what it
  does not.
- **Maintenance became a commitment.** An unmaintained repo with stale signatures is worse than no
  repo, because people run it and believe the result.

## Superseded since

Recorded because the reasoning still reads as current otherwise:

- **"macOS only, and stated as such"** — upstream ships Linux now. *This deployable* is still
  macOS only, and `tools/build-collector.py` embeds the darwin artifact deliberately.
- **The one-file-or-many tension, the authoring layout, the contribution contract and the
  performance rules** — all upstream's, and upstream documents them better than this did.
  `queries/COST.md` carries the per-state cost table this doc once argued from. The measurements
  that killed the inline Extension Attribute live in
  [`mdm/jamf-pro.md`](mdm/jamf-pro.md#why-nothing-runs-inline), against the artifact that
  actually ships.
