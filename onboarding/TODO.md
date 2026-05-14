# Buzz — Post-Review TODO

Issues surfaced in the CEO + engineering review of the `onboarding-agent` branch.
Severity: **BLOCKER** (must fix before shipping) → **Medium** → **Low**.

---

## BLOCKERS — Fix before `npm publish`

### 1. `package.json` missing `files` array
Without it, `npm publish` ships everything: `example.txt`, `tech-design.txt`,
`specifications.txt`, test files, source maps, and all TypeScript source.
```json
"files": ["dist/"]
```

### 2. `package.json` missing `publishConfig`
No registry or public-access declaration.
```json
"publishConfig": { "access": "public" }
```

### 3. `@anthropic-ai/claude-agent-sdk: "latest"` in dependencies
`latest` in a published package means each `npm install` resolves a different
version. A breaking SDK change silently breaks every Buzz installation.
Pin to a specific version (e.g. `"^0.0.12"`).
Same concern for `@mastra/core: "^1.24.1"` — Mastra makes breaking changes in
minor releases; consider a tighter pin.

### 4. No npm publish CI/CD workflow
None of the 13 GitHub Actions workflows in `.github/workflows/` publish
`@arthur-ai/buzz` to npm. Create a workflow triggered on tag push
(e.g. `onboarding/v*`) that runs `npm run build && npm publish`.

### 5. Dev artifacts committed with no `.gitignore`
`example.txt`, `tech-design.txt`, `specifications.txt` are in the repo and
would be included in `npm publish` without the `files` fix (item 1).
Added to `.gitignore` in this commit; also consider deleting them outright.

### 6. Semver: `version: "1.0.0"` on a pre-stable tool
First publish of a tool that may still have breaking changes. Consider starting
at `0.1.0` and promoting to `1.0.0` when the API stabilises.

---

## Bugs

### 7. Repo basename collision in persisted config
`getBuzzEnvPath(repoPath)` keys config by `path.basename(repoPath)`.
Two repos both named `my-app` in different directories share the same
`~/.arthur-engine/local-stack/buzz/my-app/.env` and silently inherit each
other's task IDs on subsequent runs.
Fix: key by a hash or full-path slug.
File: `src/config/env.ts`

### 8. Hardcoded "60 seconds" in trace-timeout message
`08-verify.ts:41` prints `'No traces detected after 60 seconds.'` but
`POLL_MAX_MS` is `120_000` when `BUZZ_CI=true`.
Fix: compute the message from `POLL_MAX_MS`.

### 9. Non-null assertions in step 9 without guard
`09-model-provider.ts:91` uses `state.engineUrl!` / `state.apiKey!`.
If step 2 somehow short-circuits, these throw `Cannot read properties of null`
with no user-friendly message.
Fix: add an early-return guard (same pattern as step 10's existing guard).

### 10. `query({prompt:''}).accountInfo()` not wrapped in try/catch
`01-prereqs.ts:63` — if the Claude Agent SDK throws on a network error,
the exception propagates uncaught and prints a raw stack trace.
Fix: wrap in try/catch and throw a `BuzzError` with a helpful message.

---

## UX Gaps

### 11. `confirm('Press Enter…')` in step 8 is semantically wrong
Pressing "N" returns `false` and silently exits verification with no message.
Users who misread it as "press any key" will skip trace verification unknowingly.
Fix: use a pause/anykey prompt, or print an explicit skip notice when the user
answers `false`.
File: `src/workflow/steps/08-verify.ts`

### 12. No post-instrumentation restart reminder
After step 4 instruments the user's app, Buzz immediately proceeds to step 5
with no mention that the app must be restarted for the instrumentation to take
effect. Step 6 then times out waiting for traces from an app that never reloaded.
Fix: add a `note()` or `logInfo()` after successful instrumentation reminding
the user to restart before running their agent.
File: `src/workflow/steps/04-python.ts` (and 05, 06)

---

## Code Quality

### 13. Duplicated `PROVIDER_LABELS` and `MODEL_DEFAULTS`
These maps are defined identically in both `07-prompts.ts` and
`09-model-provider.ts`. A new provider added to one file won't appear in the
other.
Fix: extract to `src/arthur/constants.ts` and import from both files.

### 14. Confusing naming: `handleRemoteEngine` vs `handleRemoteConnection`
`handleRemoteEngine` also asks for a task ID; `handleRemoteConnection` does not.
The names don't communicate this distinction.
Fix: rename `handleRemoteEngine` → `handleRemoteEngineWithTaskId`.
File: `src/workflow/steps/02-arthur-engine.ts`

### 15. Comment numbering gap in step 1
`01-prereqs.ts` has comments `// 1.1`, `// 1.3` (skipping `1.2`) — leftover
from an earlier iteration. Minor, but confusing during code review.

---

## Security

### 16. API key visible in process environment during instrumentation
`04-python.ts` sets `process.env.ARTHUR_API_KEY = state.apiKey` so Claude Code
can read it during instrumentation. The key is accessible via `ps -Eww <pid>`
(macOS) or `/proc/<pid>/environ` (Linux) for the lifetime of the Buzz process.
Acceptable for a developer tool, but should be documented in the README security
notes and cleared from `process.env` after the instrumentation step returns.

### 17. No TLS warning when transmitting third-party API keys
`configureModelProvider` POSTs provider API keys (OpenAI, Anthropic, etc.) to
Arthur Engine. If `engineUrl` is `http://` the key travels in plaintext.
Fix: warn the user if the engine URL is HTTP and they are about to configure a
provider key.
File: `src/workflow/steps/09-model-provider.ts`

---

## Observability

### 18. Buzz has no self-telemetry
No way to know which step users abandon, how often instrumentation fails,
or what frameworks are most common. This data would directly drive roadmap.
Consider opt-in anonymous analytics with a first-run prompt (similar to
`create-react-app`). Track as a v1.1 feature.

### 19. No `--debug` / `--verbose` flag
When something goes wrong there is no way to get more output.
Fix: add a `--debug` flag that enables verbose HTTP logging and SDK output.

---

## Future-Proofing

### 20. No versioning for persisted config
`~/.arthur-engine/.../buzz/<repo>/.env` has no `BUZZ_CONFIG_VERSION` field.
If a future Buzz version requires new fields, old configs fail silently.
Fix: write `BUZZ_CONFIG_VERSION=1` on first save; check and migrate at startup.

### 21. Eval recommender is static
The `eval-recommender` prompt hardcodes what evals exist. When Arthur Engine
adds new eval types, Buzz won't recommend them (and may recommend ones that
no longer exist).
Fix (v1.1): fetch available eval types dynamically from the engine before
constructing the recommendation prompt.

### 22. No non-interactive / headless mode
Buzz is 100% interactive. `BUZZ_CI=true` only changes the trace poll timeout.
There is no `--yes` flag or env-var-driven mode for automated pipelines.
Track as a v1.1 feature.

### 23. `instrumentCodeWithClaude()` has no timeout
The Claude Code instrumentation step can run indefinitely (no `maxTurns` cap
or wall-clock timeout). If it hangs, Buzz hangs with it.
Fix: pass a `maxTurns` limit or wrap with a wall-clock timeout.

---

## Tests

### 24. Zero coverage for step files (01–10)
Only `src/arthur/client.ts` has unit tests. None of the 10 step files, the
orchestrator, or the Mastra analysis module are tested.
At minimum: the orchestrator guard logic and `isInstrumented` detection should
have unit tests before v1.1.
