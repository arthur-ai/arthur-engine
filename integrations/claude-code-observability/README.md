# Claude Code → Arthur Engine Integration

Traces Claude Code sessions as OpenInference spans in Arthur Engine. Every user prompt becomes a trace containing the tool calls Claude made and the LLM API calls it used to respond.

## How it works

The tracer hooks into Claude Code's `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `SubagentStop`, and `Stop` events. `UserPromptSubmit` fires before Claude starts processing each prompt, giving accurate turn start times and the exact prompt text. Tool failures are captured as error spans so they're visible in traces.

A turn is identified by the `prompt_id` Claude Code passes to every hook, and the transcript entries labelled with the same `promptId`. That covers typed prompts, Agent SDK prompts, background-task notifications, messages from other sessions, and messages typed while Claude is working (which Claude Code folds into the running turn or runs as their own). Use a Claude Code version that sends `prompt_id` (2.1.241 and later are verified); with an older one, each `UserPromptSubmit` starts a turn.

```
Trace: "claude-code-turn"              ← one per user prompt
├── LLM  claude/claude-sonnet-4-6     ← from transcript (actual timestamps)
├── TOOL Read                          ← PostToolUse (success)
├── TOOL Edit [ERROR]                  ← PostToolUseFailure (failure)
├── RETRIEVER WebSearch                ← PostToolUse, web retrieval
├── RETRIEVER WebFetch                 ← PostToolUse, web retrieval
└── AGENT Agent                        ← PostToolUse, sub-agent call
    └── LLM  claude/claude-haiku-4-5  ← SubagentStop, from the subagent's transcript
```

Subagents write their API calls to their own transcript (`<session>/subagents/agent-<id>.jsonl`), so their LLM spans are sent when `SubagentStop` fires, under the Agent span that launched them. The tool calls a subagent makes are nested under that span too. For a subagent running in the background, the Agent span itself is held back and sent at `SubagentStop`, so it covers the subagent's whole run even when that outlasts the turn.

LLM span timing comes from the transcript: a span runs from the entry the call answers (the prompt or tool result, written when the request is sent) to the last response entry written before any tool ran.

Traces are linked to a task in Arthur Engine via the `arthur.task` resource attribute and share a `arthur.session` attribute so you can filter by session across traces.

---

## Local setup

The installer supports two modes. Use **global** to trace all your Claude Code sessions with one install, or **per-project** to scope tracing to a specific project with its own credentials.

---

### Option A — Global install (trace all projects)

```bash
cd integrations/claude-code-observability

# Optional but recommended: add credentials so the installer writes the config for you
cp .env.example .env   # or create .env manually (see below)

./install.sh
```

What this does:

1. `pip install -r requirements.txt`
2. Copies tracer to `~/.claude/hooks/`
3. Registers hooks in `~/.claude/settings.json` (fires in every Claude Code session)
4. Writes `~/.claude/arthur_config.json` from `.env` (if present)

Restart Claude Code after the first install.

---

### Option B — Per-project install (scoped to one project)

```bash
cd integrations/claude-code-observability
./install.sh --project-dir path/to/your/project
```

What this does:

1. `pip install -r requirements.txt`
2. Copies tracer to `<project>/.claude/hooks/`
3. Registers hooks in `<project>/.claude/settings.local.json` (gitignored — fires only in this project)
4. Writes `<project>/.claude/arthur_config.json` from `.env` (project dir or this dir)
5. Adds `.claude/arthur_config.json` to `<project>/.gitignore`

Restart Claude Code after the first install.

> **Note:** `settings.local.json` uses `$CLAUDE_PROJECT_DIR` to locate the tracer at runtime, so the same hook registration also works in CI (as long as the tracer is copied into the project — the install step handles this).

---

### Credentials

Populate `.env` in this directory before running `install.sh` and the config file will be written automatically:

```bash
# integrations/claude-code-observability/.env
GENAI_ENGINE_API_KEY=<your-api-key>
GENAI_ENGINE_TASK_ID=<your-task-id>
GENAI_ENGINE_TRACE_ENDPOINT=https://<your-arthur-engine-host>/api/v1/traces
```

The tracer resolves credentials in this priority order:

1. Environment variables (`GENAI_ENGINE_API_KEY`, `GENAI_ENGINE_TASK_ID`, `GENAI_ENGINE_TRACE_ENDPOINT`)
2. `<project>/.claude/arthur_config.json`
3. `~/.claude/arthur_config.json`

You can also write either config file manually:

```json
{
  "api_key": "<your-api-key>",
  "task_id": "<your-task-id>",
  "endpoint": "https://<your-arthur-engine-host>/api/v1/traces"
}
```

If none of the above are configured, the tracer silently does nothing — safe to install in shared projects.

---

### Re-running install.sh

`install.sh` is idempotent. Re-running updates the tracer binary and config without duplicating hook entries.

---

## Burn-rate circuit breaker (optional)

`claude_code_circuit_breaker.py` turns the spend telemetry above into a kill switch. It reads the cost of the LLM spans the tracer shipped to Arthur Engine, computes a **burn rate** against a budget, and trips when the burn rate is too high. While tripped it blocks new prompts (`UserPromptSubmit`) and ends the in-flight turn (`PreToolUse` with `continue: false`), so a runaway agent loop stops spending until the breaker cools down or you reset it.

```bash
./install.sh --with-circuit-breaker                       # global
./install.sh --with-circuit-breaker --project-dir DIR     # per-project
```

This copies the breaker next to the tracer, registers its `UserPromptSubmit`, `PreToolUse` and `SessionStart` hooks (15 s timeout), and writes a default `arthur_circuit_breaker.json` next to `arthur_config.json` if there isn't one. It reads engine credentials from the same places the tracer does and is a silent no-op when none are configured. `uninstall.sh` removes it along with the tracer.

**It needs a key that can read traces.** The tracer only writes, so its key is often a `VALIDATION-USER` or `CHAT-USER` key, which the engine refuses for reads (HTTP 403). Give the breaker a key with the `ORG-AUDITOR` (read-only), `TASK-ADMIN`, `TENANT-USER` or `ORG-ADMIN` role as `GENAI_ENGINE_READ_API_KEY` in `.env` (written to `arthur_config.json` as `read_api_key`), or set either one yourself; it takes precedence over the tracer's `api_key` wherever it is set. The installer finishes with `claude_code_circuit_breaker.py check` and exits non-zero if the engine refuses the key, since such a breaker would never trip. Run the check again after changing credentials.

### How burn rate works

```
burn_rate = (spend in window / window hours) / (budget_usd / budget_period_hours)
```

A burn rate of 1.0 uses the budget up exactly at the end of the period; 14.4x on a 24 h budget means 1 % of it goes every minute. Each rule pairs a long window with a short one (SRE multi-window alerting): the long window shows the burn is significant, the short window shows it is still happening, and the rule fires only when **both** exceed its threshold. That is why spend is measured on individual LLM spans rather than whole traces — a turn that runs for hours lands in the right minute buckets as it runs.

Breaker states:

| State | Behaviour |
|-------|-----------|
| closed | Normal. The engine is queried at most once per `check_interval_seconds`; between checks the last verdict is reused, so per-tool-call hooks stay cheap. |
| open | Prompts are blocked and the turn is stopped, without touching the engine, for `cooldown_minutes`. |
| half-open | After the cooldown the next hook probes the engine: calm → closed, still burning → open again, engine unreachable → stays open and probes again on the next hook. |

An open breaker blocks every prompt, so you cannot simply ask Claude to carry on. To lift it from inside Claude Code, send a prompt that **starts with** `breaker override` (also `circuit breaker override`, `override the breaker`, or `bypass` instead of `override`). The breaker closes for `override_minutes` (default 30) and says so. The override prompt itself is not sent to Claude, so Claude does not take it as a cue to resume the work the breaker just stopped. Your next prompt says what happens next. Add a duration to change it: `breaker override for 45m`, `breaker override for 2h`. The phrase must open the prompt, so a prompt that merely mentions the breaker is not an override. When the override lapses, burn-rate checks resume and the breaker can trip again.

Blocked prompts never run, so the tracer sends no trace for them. This applies to both the prompts the breaker stops and the override prompt.

`python3 ~/.claude/hooks/claude_code_circuit_breaker.py reset` closes it by hand. `ARTHUR_BREAKER_BYPASS=1` disables it for one process. State files live in `~/.claude/circuit_breaker/` and are pruned after 48 h; the directory is shared by global and per-project installs, so only a global `uninstall.sh` removes it.

### Configuration

`ARTHUR_BREAKER_CONFIG` (a path), then `<project>/.claude/arthur_circuit_breaker.json`, then `~/.claude/arthur_circuit_breaker.json`; keys you leave out keep their defaults. `ARTHUR_BREAKER_SCOPE` and `ARTHUR_BREAKER_BUDGET_USD` override the file.

```json
{
  "enabled": true,
  "scope": "session",
  "budget_usd": null,
  "budget_period_hours": 24.0,
  "rules": [
    { "name": "fast-burn", "window_minutes": 10, "short_window_minutes": 2,  "burn_rate": 14.4 },
    { "name": "slow-burn", "window_minutes": 60, "short_window_minutes": 10, "burn_rate": 6.0 }
  ],
  "hard_cap_usd": null,
  "warn_fraction": 0.75,
  "check_interval_seconds": 30,
  "cooldown_minutes": 15,
  "fail_mode": "open",
  "http_timeout_seconds": 5,
  "engine_timezone": "UTC",
  "fallback_usd_per_million_tokens": null,
  "override_minutes": 30
}
```

| Key | Meaning |
|-----|---------|
| `scope` | Whose spend counts: `session` (this Claude Code session, via `arthur.session`), `user` (every session of this OS user on the task, via `user.id`) or `task` (everything on the task). The breaker state is keyed the same way, so a `task`-scope trip pauses every session. |
| `enabled` | `false` leaves the hooks installed but inert. |
| `budget_usd`, `budget_period_hours` | The budget the burn rate is measured against, for the whole scope. `null` takes the scope's default: $200 for `session`, and $600 for `user`, whose parallel sessions all share it. `task` has no default, since it depends on the team, and its burn-rate rules stay off until you set one; `SessionStart`, `check` and `status` say so. |
| `rules` | Multi-window burn-rate rules. `short_window_minutes: null` makes a single-window rule. The widest `window_minutes` sets how far back spans are fetched. `[]` disables burn-rate rules, leaving only `hard_cap_usd`. |
| `hard_cap_usd` | Absolute ceiling on the scope's total: the whole session for `session`, the last `budget_period_hours` for `user`/`task`. `null` disables it (and skips the extra engine call). |
| `warn_fraction` | Show a warning in Claude Code once a rule reaches this fraction of its threshold. |
| `fail_mode` | `open` keeps working when the engine is unreachable or refuses the key (with a warning); `closed` trips instead. |
| `http_timeout_seconds` | Cap on one engine request. All the requests of one hook share a 10 s budget, under the 15 s hook timeout; spans that budget cannot page through are left out and reported as a lower bound. |
| `engine_timezone` | The zone the engine stamps span times in. It stores them as its server's local time with no offset, and compares time filters against them as is. `UTC` for the container images and hosted engines; `local` for an engine running on this machine outside a container (`uv run serve`); otherwise an IANA name such as `America/Los_Angeles`. A wrong value makes recent spend look hours old, so the breaker sees $0. |
| `fallback_usd_per_million_tokens` | `{"prompt": 3, "completion": 15}` prices spans whose model the engine could not price (their cost comes back empty). Leave `null` to be warned about such spans instead. |
| `override_minutes` | How long a `breaker override` prompt keeps the breaker lifted when the prompt names no duration. |

The defaults are generous on purpose. Out of the box the breaker is there to stop a runaway, not to enforce a budget, and a trip on ordinary work is what gets a breaker switched off. Set `budget_usd` when you want it to hold a real budget. At `session` scope, $200/24 h is an $8.33/h budget rate, so `fast-burn` trips at $120/h sustained over 10 minutes ($20, with $4 of it in the last 2), and `slow-burn` at $50/h over an hour ($50, with $8.33 of it in the last 10 minutes). At `user` scope the same thresholds are three times higher.

### Checking what it sees

```bash
python3 ~/.claude/hooks/claude_code_circuit_breaker.py status                      # task-wide
python3 ~/.claude/hooks/claude_code_circuit_breaker.py status --session <id>       # one session
```

prints the current spend per window, burn rates, whether each rule would fire, which key is in use, any clock warning, and the persisted breaker state.

```bash
python3 ~/.claude/hooks/claude_code_circuit_breaker.py check
```

checks that the key can read spans and that the engine's span times read right in `engine_timezone`. It exits 0 when they do (printing any clock warning), 1 when no credentials are configured, 2 when the engine refuses the key, and 3 when the engine cannot be reached. `SessionStart` runs the same clock check and shows a warning in Claude Code. It catches an engine whose spans end in the future, and, with `engine_timezone` at `UTC`, an engine on local time beside a database on UTC (`uv run serve` with Postgres in Docker). An engine and database that both run on local time leave nothing to detect, so set `local` yourself.

### Engine calls

| Scope need | Endpoint |
|------------|----------|
| Spend per window | `GET /api/v1/traces/spans?task_ids=…&span_types=LLM&sort=desc&sort_by=start_time` plus `session_ids` / `user_ids` for the narrower scopes. The endpoint's `start_time`/`end_time` filters apply to the *trace*, which is a whole turn, so they would drop a long-running turn's recent spans. The breaker sends none. It pages newest first (50, 50, 100, 200 … up to 800 rows a page) and stops at the first page that reaches spans which started before the widest window (less 15 min of slack). Spans are bucketed locally per rule window by their **end** time, since the cost is realised when the response completes. The engine's `user_ids` filter is a substring match, so rows are re-checked for an exact `user_id` |
| Hard cap, `session` | `GET /api/v1/traces/sessions?task_ids=…&session_ids=…` |
| Hard cap, `user` | `GET /api/v1/traces?task_ids=…&user_ids=…&start_time=…&end_time=…`, summing this user's traces (no endpoint returns one user's spend over a window) |
| Hard cap, `task` | `POST /api/v1/traces/overview` |
| Startup clock check | `GET /api/v1/traces/spans?task_ids=…&span_types=LLM&page_size=1`, the newest span's `end_time` (engine clock) against now and its `created_at` (database clock) |

Time filters go out in `engine_timezone` without an offset, the form the engine compares against its stored values.

Caveat: spend lands in the engine when the tracer emits LLM spans, which happens at each tool call and at the end of the turn, so a single very long generation is only visible once it finishes.

---

## GitHub Actions setup

Copy the ready-to-use workflow files into your repo's `.github/workflows/` directory:

| File | Use case |
|------|----------|
| `workflow-claude-code.yml` | Interactive Claude (`@claude` mentions on issues/PRs) |
| `workflow-claude-code-review.yml` | Automated PR review on every push |

Credentials are passed via GitHub secrets/variables set in the `env:` block of each workflow.

**GitHub repo configuration:**

| Type | Name | Value |
|------|------|-------|
| Secret | `GENAI_ENGINE_API_KEY` | Arthur Engine API key |
| Variable | `GENAI_ENGINE_TASK_ID` | Task UUID in Arthur Engine |
| Variable | `GENAI_ENGINE_TRACE_ENDPOINT` | `https://<host>/api/v1/traces` |

Set these under **Settings → Secrets and variables → Actions**.

---

## Testing

Unit tests cover config discovery, transcript parsing, turn detection, LLM span extraction, all six hook handlers, RETRIEVER span kind routing, and error span emission. No credentials or running services are required — OTLP export is mocked. The circuit breaker tests cover burn-rate math, multi-window rules, the open/half-open/closed state machine, fail-open/closed and the hook JSON for each event, with the engine HTTP calls mocked.

```bash
cd integrations/claude-code-observability
pip install pytest -r requirements.txt
python3 -m pytest test_tracer.py test_circuit_breaker.py -v
```

---

## Files

| File | Purpose |
|------|---------|
| `claude_code_tracer.py` | Hook script — handles `user_prompt_submit`, `pre_tool`, `post_tool`, `post_tool_failure`, `subagent_stop`, `stop` |
| `claude_code_circuit_breaker.py` | Optional burn-rate circuit breaker hook — handles `user_prompt_submit`, `pre_tool`, `session_start`; CLI `status` / `check` / `reset` |
| `test_tracer.py` | Unit tests (pytest, no credentials needed) |
| `test_circuit_breaker.py` | Unit tests for the circuit breaker (pytest, engine mocked) |
| `install.sh` | Local dev installer |
| `requirements.txt` | Python dependencies |
| `workflow-claude-code.yml` | GitHub Actions workflow for interactive Claude (`@claude` mentions) |
| `workflow-claude-code-review.yml` | GitHub Actions workflow for automated PR review |
| `.env` | Local credentials (not committed) |
