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
  sent. While an answer streams, it estimates this request's cost so far (its
  input side, as the conversation's previous prompt size at the cache-read
  price, plus the answer at four characters a token and the model's output
  price), and stops reading once that would pass the cap, which ends the
  request.
- **`prompt.submit`**: while over the cap, a new prompt is dropped before it
  starts a turn. `breaker override` lifts it for ten minutes, `breaker reset`
  clears the spend, and `breaker status` prints it. None of these reach the
  model.
- Spend and the override live in `$.store`, so a restarted session is still
  paused. Each request is its own key, so sessions finishing requests at the
  same time don't overwrite each other.

The cap is `ARTHUR_BREAKER_CAP_USD` (default `0.10` USD per five minutes); a
value that isn't a positive number falls back to the default.
Prices are Anthropic's list prices per model in `hooks/register.ts` (Opus 4 and
4.1, Fable and Haiku 5.5's long-prompt rate included); a model with no row is
priced at the highest rate of each kind. Cache writes are priced at the 1-hour
rate, because the usage a mod sees does not say which cache was written, so the
estimate errs high. An answer that is interrupted or fails partway is counted
from its running estimate.

## Try it

```bash
claude plugin validate integrations/claude-code-observability/mod-spend-breaker
claude plugin test integrations/claude-code-observability/mod-spend-breaker
ARTHUR_BREAKER_CAP_USD=0.05 claude --plugin-dir integrations/claude-code-observability/mod-spend-breaker
```

`--plugin-dir` loads it for one session, and nothing stops a user from simply
not loading it.

### Deploy it for an organization

To make it apply to everyone, Claude Code must count it as the organization's
own mod. It does only when the plugin is loaded in place from a marketplace that
is a **directory on each machine**: a plugin enabled from a GitHub, git, URL or
npm marketplace is copied into the cache, counts as a user's mod, and
`allowManagedModsOnly` refuses it. See
[Manage mods for your organization](https://code.claude.com/docs/en/plugins/mods/admin#install-your-organizations-mods).

1. Have device management copy a marketplace to the same absolute path on
   every machine, writable only by an administrator (anyone who can write there
   can change the mod):

   ```text
   /opt/arthur/claude-plugins/
   ├── .claude-plugin/marketplace.json
   └── plugins/arthur-spend-breaker/      <- this folder
   ```

   with `marketplace.json` listing the plugin by a relative path:

   ```json
   {
     "name": "arthur-tools",
     "owner": { "name": "Your organization" },
     "plugins": [{ "name": "arthur-spend-breaker", "source": "./plugins/arthur-spend-breaker" }]
   }
   ```

2. Deploy managed settings that register that directory, enable the plugin,
   run it first, and refuse users' own mods:

   ```json
   {
     "extraKnownMarketplaces": {
       "arthur-tools": { "source": { "source": "directory", "path": "/opt/arthur/claude-plugins" } }
     },
     "enabledPlugins": { "arthur-spend-breaker@arthur-tools": true },
     "prependPlugins": ["arthur-spend-breaker@arthur-tools", "sec-default@builtin"],
     "pluginConfigs": {
       "cc-plugin-sec-default@builtin": { "options": { "allowManagedModsOnly": true } }
     },
     "disableSideloadFlags": true
   }
   ```

3. Check a machine with `claude --debug`: the log should have
   `hooks module arthur-spend-breaker@arthur-tools loaded` with `tier prepend`.
   `tier user` means Claude Code is treating it as a user's mod.

Even deployed this way, `--safe-mode` starts a session without installed mods,
and `disableAllHooks` in managed settings turns it off.

## Limits

- A request the mod cuts returns no usage, so Claude Code's own cost total
  leaves it out. The API still bills the output streamed before the cut, and
  the mod counts its estimate.
- The output estimate is characters / 4, not the model's tokenizer.
- Subagents' requests go through `turn.step` too and count toward the same cap.
- A cut request's input side is estimated as the conversation's previous prompt
  size at the cache-read price, which is what a follow-up request mostly pays.
  It undercounts a request that writes a lot of new cache. The previous prompt
  size is kept in memory, so the first request after Claude Code starts or
  resumes a session has nothing to go on, and only its output is counted if it
  is cut.
