---
name: maintain-codeowners
description: Audit or extend .github/CODEOWNERS, the human-review gate for sensitive paths. Use when asked whether a path should be gated, when auditing the list for stale or missing entries, or after a refactor moves code that a CODEOWNERS comment describes.
allowed-tools: Bash, Read, Edit, Grep, Glob, Task
---

# Maintain CODEOWNERS

`.github/CODEOWNERS` lists the paths where a PR needs one approval from
`@arthur-ai/arthur-engineers`. Everything else is left to the automated
reviewer. The file only works if every line is still true and the list stays
short enough that ordinary PRs are not slowed down. This skill keeps it that
way.

The gate only takes effect when "Require review from Code Owners" is on for the
`dev` ruleset. Check it first and say so in the report if it is off; the rest of
the audit is moot until it is on:

```bash
gh api repos/arthur-ai/arthur-engine/rules/branches/dev \
  -q '.[] | select(.type=="pull_request") | .parameters.require_code_owner_review'
```

## The bar for gating a path

A path belongs in CODEOWNERS only if **all three** hold:

1. **A mistake there is one of these**, matching a section of the file:
   - **secrets / config**: a credential (customer or ours) could be logged,
     sent to a different host, stored unencrypted, or sent over unverified TLS.
     Tests still pass; the customer has to rotate the secret. Not reversible
     with a revert.
   - **deploy / infra**: code or config ships inside a release image, a Helm or
     CloudFormation deployment, or is run by customers on their own machines
     (anything customers paste, download, or install from this repo).
   - **ci/cd**: runs in a CI job that holds a protected-branch secret, or
     decides what goes into a published artifact (wheel, image, bundle).
   - **auth**: authn/authz checks, role→permission mapping, org scoping, the
     signup path, and the tests that pin them.
   - **guardrails**: changes guardrail results, so it needs evaluation and
     benchmarking before shipping. Includes which model is loaded, not just the
     scorer code.
   - **migrations**: schema changes.
2. **It changes rarely.** Count commits over the last six months. If the file
   is edited in most feature PRs for its area, a gate there is drag, not
   safety; the PR that added the file left `server.py` ungated for exactly
   this reason (21 commits/year, mostly router registration).
3. **CODEOWNERS is the right fix.** If the risk is "a check only runs in
   pre-commit" or "a workflow runs PR code with secrets", the fix is a CI step
   or a workflow change. If the risk is "nobody tests that X stays off", the
   fix is a test. Report those separately; do not gate a file to paper over
   them.

Two things that fail the bar on their own:

- **Renovate edits it.** Check `renovate.json` `enabledManagers` and
  `includePaths`. Gating a Renovate-managed file (e.g. `genai-engine/ui/
  package.json`, any `uv.lock`) stops automerge for every dependency bump.
  The un-gated overrides at the bottom of the file exist for this.
- **Any file could do the same thing.** `ui/src/lib/api.ts` attaches the bearer
  token, but so can any fetch call in the UI. Gate the thing that is actually
  unique (the token source, the config that picks the host), not one consumer.

## Audit procedure

Run this when asked to audit, after a large refactor, or roughly quarterly.
Work against `origin/dev` (`git fetch origin dev` first). Report facts with
file paths and line numbers; a finding without a verified line is a guess.

### 1. Syntax and owner resolution

```bash
gh api "repos/arthur-ai/arthur-engine/codeowners/errors?ref=<branch>"
```

Must return `[]`. `Unknown owner` on every line means the team is secret;
GitHub ignores secret teams.

### 2. Every pattern still matches a tracked file

A pattern that matches nothing is a path that moved. Find where it went and
re-point the line.

```bash
git ls-files > /tmp/tracked.txt
grep -E '^/' .github/CODEOWNERS | awk '{print $1}' | sed 's#^/##' | while read -r p; do
  case "$p" in
    */\*\*) n=$(grep -c "^${p%/**}/" /tmp/tracked.txt) ;;
    *)      n=$(grep -cx "$p" /tmp/tracked.txt) ;;
  esac
  [ "$n" = "0" ] && echo "NO MATCH: /$p"
done
```

### 3. Every comment is still true

Each `#` comment above a line states *why* that path is gated, as a factual
claim about the code ("builds the platform OAuth session", "sends
GITLAB_UNIFY_FRONTEND_TOKEN to the registry"). Code moves and the comment
stays. For each comment, grep for the thing it names and confirm it is still
in that file. When it has moved, gate the new location and fix the comment.

Example: #2381 moved the OAuth session out of `job_agent.py` and
`job_executor.py` into `tools/platform_api_client.py`; the two gated files kept
their "builds the OAuth session" comments for ten days while the real code was
ungated.

### 4. Sweep for new candidates, per section

Use these searches as a starting point, then apply the bar to each hit.

| Section | Search |
|---|---|
| secrets / config | `DatabaseSecretStorage`, `EncryptedJSON`, `client_secret`, `_SECRET\b`, `verify_ssl`, `verify=`, `ssl_verify`, `SSLContext`, `redact`; anything writing to the secret storage table the way `model_provider_repository.py` does |
| deploy / infra | `COPY` and `install -r` lines in every gated Dockerfile (what they pull in is as sensitive as the Dockerfile); READMEs under `integrations/` that tell customers to paste, upload, or install something; `LaunchDaemon`, `.plist`, `.pkg` |
| ci/cd | workflow steps that run a repo script with `secrets.` in `env:` or as a build arg; config files a release job reads (`openapitools.json`, `.yarnrc.yml`, `vite.config.ts`); hooks declared in `**/.claude/settings.json` or inline in a workflow's `settings:` |
| auth | `permission_checker`, `enforce_org_scope`, `lookup_org_id`, `demo_mode`, `CORSMiddleware`, `SessionMiddleware`; new files under `routers/` that are *not* just `@permission_checker` + handler |
| guardrails | `scorer/`, `rules_engine.py`, model repo ids in `utils/model_load.py`, `weights_only=False` |
| migrations | `alembic/` |

For each candidate, get the churn and who makes it:

```bash
git log --oneline --since="6 months ago" origin/dev -- <path> | wc -l
git log --format=%an --since="6 months ago" origin/dev -- <path> | sort | uniq -c
```

If `git rev-parse --is-shallow-repository` prints `true`, the counts are
truncated to the clone's history; say so in the report.

### 5. Write the report

A table per outcome. Keep entries carry the path, the section, the one-line
reason tied to criterion 1, and the churn. Drop entries say which criterion
failed and, where the original worry was real but mis-aimed, what the right
fix is (a test, a CI step, a workflow change). Include dropped candidates in
the report: the reasoning is what stops the same idea coming back next audit.

## Editing the file

- Patterns start with `/` (anchored to the repo root). The owner starts at
  column 67; pad the path with spaces to column 66. A path longer than that
  gets two spaces.
- Put the line in the matching `# --- section ---`. Keep the un-gated
  overrides block last; later lines win in CODEOWNERS.
- Every added line gets a comment above it stating *why*, as a claim the next
  audit can verify by grep (name the function, env var, token, or file that
  makes it sensitive). "Sensitive" on its own is not a reason.
- One line per file, not a glob over a directory, unless the whole directory
  meets the bar and changes rarely. `discovery/**` in ml-engine does not:
  fifteen commits in three months, so only the two log-scrubbing files from it
  are gated.
- Open the PR against `dev`. The PR body lists each added path with its
  reason and churn, and each considered-and-dropped path with why. Editing
  `.github/**` is itself gated, so a human reviews the change.

## Verifying a change

1. `gh api "repos/arthur-ai/arthur-engine/codeowners/errors?ref=<branch>"`
   returns `[]`.
2. The step-2 script prints no `NO MATCH`.
3. After merge, with the ruleset on: a throwaway PR touching a newly gated
   file gets a code-owner review request; a Renovate PR touching
   `genai-engine/ui/package.json` or `deployment/model-upload/uv.lock` does
   not.
