# Spend breaker as a Claude Code mod (experimental)

`arthur-spend-breaker` pauses Claude Code once model spend in the last five
minutes reaches a cap. It is a [mod](https://code.claude.com/docs/en/plugins/mods/overview):
a plugin whose code runs inside Claude Code (CLI 2.1.287+, Desktop 2.1.286+),
rather than a settings hook that Claude Code starts as a separate process.

It is an alternative to the settings-hook circuit breaker in
`../claude_code_circuit_breaker.py`; install one or the other. Both answer the
same `breaker override` / `breaker reset` / `breaker status` prompts, but each
keeps its own state, so with both installed an override lifts only one of them.

## Why a mod

Settings hooks get a say at a prompt and before a tool call. A mod also sees
every model request ([`turn.step`](https://code.claude.com/docs/en/plugins/mods/events))
and the usage it reports as it finishes, so it:

| | Settings hooks | This mod |
|---|---|---|
| Where spend comes from | Arthur Engine, once the tracer has uploaded it | Each model request's `usage`, in process, immediately |
| Engine key, timezone, query window | Needed | Not involved |
| Stops a turn | At the next tool call | At the next model request |
| A long answer with no tool calls | Runs to the end | Cut mid-stream once its own output would pass the cap |
| Works on | Any CLI version | CLI 2.1.287+ / Desktop 2.1.286+ |

## What it does

- **`turn.step`**: before each model request, if spend in the window is at the
  cap, it answers the request itself with the pause message, so nothing is
  sent. While an answer streams, it estimates the answer's own cost (four
  characters a token at the model's output price), and stops reading once that
  would pass the cap, which ends the request.
- **`prompt.submit`**: while over the cap, a new prompt is dropped before it
  starts a turn. `breaker override` lifts it for ten minutes, `breaker reset`
  clears the spend, and `breaker status` prints it. None of these reach the
  model.
- Spend and the override live in `$.store`, so a restarted session is still
  paused.

The cap is `ARTHUR_BREAKER_CAP_USD` (default `0.10` USD per five minutes).
Prices are list prices per model family in `hooks/register.ts`. Cache writes
are priced at the 1-hour rate, because the usage a mod sees does not say which
cache was written, so the estimate errs high.

## Try it

```bash
claude plugin validate integrations/claude-code-observability/mod-spend-breaker
claude plugin test integrations/claude-code-observability/mod-spend-breaker
ARTHUR_BREAKER_CAP_USD=0.05 claude --plugin-dir integrations/claude-code-observability/mod-spend-breaker
```

`--plugin-dir` loads it for one session. For an organization, it is only
enforceable as a managed mod (managed `enabledPlugins`, with
`allowManagedModsOnly` so users can't load their own first): see
[Manage mods for your organization](https://code.claude.com/docs/en/plugins/mods/admin).
Without that, `--safe-mode` or simply not loading it turns it off.

## Limits

- A request the mod cuts returns no usage, so Claude Code's own cost total
  leaves it out. The API still bills the output streamed before the cut, and
  the mod counts its estimate.
- The output estimate is characters / 4, not the model's tokenizer.
- Subagents' requests go through `turn.step` too and count toward the same cap.
