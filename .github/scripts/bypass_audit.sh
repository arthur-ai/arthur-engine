#!/usr/bin/env bash
# Open a tracking issue for every ruleset bypass made by a person, for
# .github/workflows/bypass-audit.yml.
#
# The bypass list on the `dev` and `main` rulesets is the break-glass path: it is the only
# way a PR touching a CODEOWNERS path merges without a second engineer, and it also lets a
# merge skip required checks and the merge queue. GitHub records every bypass in rule
# insights, but nobody is told and no reason is kept. This turns each one into an issue
# that stays open until someone other than the bypasser has looked at what shipped.
#
# The reason is read from a line starting `Emergency:` in the PR body. A bypass without
# one still gets its issue; the issue asks the bypasser for it.
#
# Not logged:
#   - The Automator App. It bypasses on every version bump and dev/main sync, which is
#     its job, and would bury the bypasses that matter.
#   - A bypass whose only failed rule is merge_queue: the PR already had its reviews and
#     green checks and only jumped the queue.
#
# Idempotent: each issue carries the rule suite id in an HTML comment, and a bypass that
# already has an issue (open or closed) is skipped, so overlapping windows are safe.
# Existing issues are read from the issues list rather than search, which lags behind
# writes by long enough to file a duplicate.
#
# Reading rule suites needs the "Administration: read" repository permission, which a
# workflow's GITHUB_TOKEN cannot be granted. RULES_TOKEN carries it (the Automator App's
# token in CI); everything else uses GH_TOKEN. Locally, a `gh auth` user token with repo
# admin covers both. DRY_RUN=1 prints the issues instead of opening them.
#
# Usage: bypass_audit.sh <hour|day|week|month>
#   (needs GH_TOKEN and GITHUB_REPOSITORY; RULES_TOKEN defaults to GH_TOKEN)
set -euo pipefail

PERIOD="${1:?usage: bypass_audit.sh <hour|day|week|month>}"
REPO="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY must be set}"
RULES_TOKEN="${RULES_TOKEN:-${GH_TOKEN:-}}"
DRY_RUN="${DRY_RUN:-0}"
LABEL="bypass-audit"
IGNORED_ACTOR="arthur-github-automator-app[bot]"

case "$PERIOD" in
  hour | day | week | month) ;;
  *) echo "time period must be hour, day, week or month, got: $PERIOD" >&2; exit 2 ;;
esac

ERR=$(mktemp)
trap 'rm -f "$ERR"' EXIT

# Sets RULES_OUT. Called directly rather than in $(...) so that the exit stops the
# script and the ::error:: line reaches the log. A 403 is the missing permission, not an
# outage, and says so: until the App has Administration: read this job is red on every
# run, which is the point — a green run that read nothing would look the same as a week
# with no bypasses.
rules_api() {
  if RULES_OUT=$(GH_TOKEN="$RULES_TOKEN" gh api "$@" 2>"$ERR"); then
    return 0
  elif grep -q 'HTTP 403' "$ERR"; then
    echo "::error::Reading rule suites on $REPO was refused. The token needs the \"Administration: read\" repository permission (grant it to the Arthur GitHub Automator App). GitHub said: $(cat "$ERR")"
  else
    echo "::error::Could not read rule suites on $REPO. Re-run the job. GitHub said: $(cat "$ERR")"
  fi
  exit 1
}

# Paging this endpoint repeats rows (a month on this repo: 242 rows, 142 distinct ids, at
# every page size), so dedupe by id or each repeat files its own issue.
rules_api --paginate \
  "repos/$REPO/rulesets/rule-suites?rule_suite_result=bypass&time_period=$PERIOD&per_page=100"
SUITES=$(jq -s --arg ignored "$IGNORED_ACTOR" \
  'add // [] | unique_by(.id) | map(select(.actor_name != $ignored))' <<<"$RULES_OUT")

if [ "$(jq 'length' <<<"$SUITES")" -eq 0 ]; then
  echo "No bypasses by a person in the last $PERIOD."
  exit 0
fi

LOGGED=$(gh api --paginate "repos/$REPO/issues?labels=$LABEL&state=all&per_page=100" \
  --jq '.[].body // ""' | grep -o 'bypass-audit rule-suite=[0-9]*' | cut -d= -f2 || true)

LABEL_READY=0
opened=0
for id in $(jq -r '.[].id' <<<"$SUITES"); do
  if grep -qx "$id" <<<"$LOGGED"; then
    echo "Rule suite $id already has an issue."
    continue
  fi

  rules_api "repos/$REPO/rulesets/rule-suites/$id"
  SUITE="$RULES_OUT"
  FAILED=$(jq '[.rule_evaluations[] | select(.result == "fail")]' <<<"$SUITE")
  if [ "$(jq 'map(select(.rule_type != "merge_queue")) | length' <<<"$FAILED")" -eq 0 ]; then
    echo "Rule suite $id only skipped the merge queue; not logged."
    continue
  fi

  ACTOR=$(jq -r '.actor_name' <<<"$SUITE")
  SHA=$(jq -r '.after_sha' <<<"$SUITE")
  REF=$(jq -r '.ref | sub("^refs/(heads|tags)/"; "")' <<<"$SUITE")
  WHEN=$(jq -r '.pushed_at' <<<"$SUITE")
  RULES=$(jq -r '.[] | "- **\(.rule_type)** (\(.rule_source.name)): \(.details // "failed")"' <<<"$FAILED")

  # The rulesets only let people bypass through a PR, so a commit without one is a tag or
  # a branch outside dev/main, and is reported as a push. A failed lookup is reported the
  # same way rather than dropping the bypass: the issue still names the commit.
  PR_JSON=$(gh api "repos/$REPO/commits/$SHA/pulls" --jq '.[0] // empty' 2>/dev/null) || PR_JSON=""
  if [ -n "$PR_JSON" ]; then
    PR=$(jq -r '.number' <<<"$PR_JSON")
    TITLE="Ruleset bypass: #$PR into $REF by @$ACTOR"
    WHAT="merged #$PR ($(jq -r '.title' <<<"$PR_JSON")) into \`$REF\`"
    REASON=$(jq -r '.body // ""' <<<"$PR_JSON" | tr -d '\r' \
      | sed -n 's/^[[:space:]]*[*_]*[Ee][Mm][Ee][Rr][Gg][Ee][Nn][Cc][Yy][*_]*:[*_]*[[:space:]]*//p' \
      | head -n 1)
  else
    PR=""
    TITLE="Ruleset bypass: push to $REF by @$ACTOR (${SHA:0:8})"
    WHAT="pushed ${SHA:0:8} to \`$REF\`"
    REASON=""
  fi
  if [ -z "$REASON" ]; then
    REASON="_None given. @$ACTOR, reply here with why this could not wait, and add an \`Emergency:\` line to the PR body next time._"
  fi

  # read rather than $(cat <<EOF): macOS's bash 3.2 cannot parse a heredoc containing a
  # ")" inside a command substitution, and the dry run is meant to work on a laptop.
  IFS= read -r -d '' BODY <<EOF || true
@$ACTOR $WHAT without meeting these rules:

$RULES

**Reason:** $REASON

| | |
|---|---|
| Commit | $SHA |
| When | $WHEN |
| Record | \`gh api repos/$REPO/rulesets/rule-suites/$id\` |

**To close this:** someone in @arthur-ai/arthur-engineers other than @$ACTOR reviews what shipped (\`git show $SHA\`${PR:+, or the Files tab on #$PR}), comments with what they found, and closes the issue. If it should not have shipped, revert it first.

Opened by [bypass-audit.yml](https://github.com/$REPO/blob/dev/.github/workflows/bypass-audit.yml).

<!-- bypass-audit rule-suite=$id -->
EOF

  if [ "$DRY_RUN" = "1" ]; then
    printf '=== %s\n%s\n\n' "$TITLE" "$BODY"
    opened=$((opened + 1))
    continue
  fi
  if [ "$LABEL_READY" -eq 0 ]; then
    gh label create "$LABEL" --repo "$REPO" --color B60205 --force \
      --description "A ruleset was bypassed; open until someone else reviews what shipped" >/dev/null
    LABEL_READY=1
  fi
  URL=$(gh issue create --repo "$REPO" --title "$TITLE" --label "$LABEL" --body-file - <<<"$BODY")
  echo "Logged rule suite $id: $URL"
  opened=$((opened + 1))
done

echo "$opened bypass issue(s) $([ "$DRY_RUN" = "1" ] && echo "would be opened" || echo "opened")."
