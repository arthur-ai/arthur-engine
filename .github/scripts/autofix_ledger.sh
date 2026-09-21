#!/usr/bin/env bash
# Attempt ledger for .github/workflows/renovate-autofix.yml.
#
# A retry budget has to survive the thing it counts. The budget used to be derived from
# [claude-autofix] commits reachable from HEAD, but only a SUCCESSFUL session leaves one —
# a session that declines, times out or is cancelled leaves nothing and costs nothing
# against the cap. On the GitLab sibling that runs this same reconciler on a 4h schedule,
# that turned into an unbounded loop: 184 sessions over 16 days, 4 of which produced a fix,
# one MR attempted 59 times with its budget reading 0/3 every time, 79 hours of
# Claude-running CI. See ArthurAI/unify-frontend!1518 for the measurements and the fix this
# is ported from.
#
# This workflow is event-driven rather than scheduled, so it cannot loop the same way: a
# second attempt on one commit lineage requires a new CI failure, which requires a push.
# The guards are still worth having, and two of them do real work here:
#   - `heavy` (handled in the workflow, not this script) skips a PR a human has marked as
#     unfixable in one session. That is this repo's actual exposure: Renovate rebases a
#     long-lived major every time the base branch moves, and each rebase is a fresh head,
#     a fresh CI failure and a fresh full-cost Opus session.
#   - Head-SHA dedupe stops a re-run of CI on an UNCHANGED commit from buying a second
#     identical session.
# The failure-counting budget is close to a no-op under the current trigger (a decline
# pushes nothing, so nothing re-triggers), but it stops being one the moment a schedule or
# any retry trigger is added — and it keeps the three copies of this reconciler behaving
# identically, which is worth more than the code it costs.
#
# State lives in a single PR comment — the only store that outlives the runner — carrying a
# machine-readable JSON block inside an HTML comment plus a table humans can read:
#
#   <!-- renovate-autofix-ledger
#   {"heads":{"<full sha>":{"attempts":N,"last":"<outcome>","at":"<utc>"}},"gave_up_head":"<sha>"}
#   -->
#
# Keyed by full head SHA, which gives both guards their meaning: attempts against THIS head
# (dedupe) and attempts across every head reachable from it (the branch budget, which a
# rebase resets because the abandoned SHAs stop being ancestors).
#
# An attempt is recorded BEFORE the session starts, so a run killed mid-flight still spends
# the budget instead of replaying for free. Reads and writes fail closed: an unreadable
# ledger or a rejected write means "do not proceed", because an uncounted attempt is the
# exact failure this prevents.
#
# Usage (both subcommands need GH_TOKEN and GITHUB_REPOSITORY, and run inside the checkout):
#   autofix_ledger.sh guard  <pr> <head_sha>   -> writes proceed=true|false to $GITHUB_OUTPUT
#   autofix_ledger.sh record <pr> <head_sha> <outcome>
set -euo pipefail

REPO="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY must be set}"
MAX_ATTEMPTS="${MAX_AUTOFIX_ATTEMPTS:-3}"
MAX_PER_HEAD="${MAX_ATTEMPTS_PER_HEAD:-1}"
LEDGER_KEEP="${LEDGER_KEEP_HEADS:-20}"
LEDGER_MARKER="renovate-autofix-ledger"
LEDGER_PAGES="${LEDGER_PAGES:-5}"

LEDGER_NOTE_ID=""
LEDGER_JSON='{"heads":{},"gave_up_head":null}'

# Returns non-zero if the comments could not be read at all. That has to be distinguished
# from "this PR has no ledger yet": mistaking a failed read for an empty one would both
# replay an already-attempted head and post a SECOND ledger comment beside the first.
#
# Every page is scanned rather than stopping at the newest: the issue-comments endpoint
# ignores sort/direction (verified against this repo — comments come back oldest-first
# whatever you ask for), so there is no cheap "our comment is near the top" shortcut.
ledger_load() { # ledger_load <pr>
  local pr="$1" page comments len hit=""
  LEDGER_NOTE_ID=""; LEDGER_JSON='{"heads":{},"gave_up_head":null}'
  for ((page = 1; page <= LEDGER_PAGES; page++)); do
    comments="$(gh api "repos/$REPO/issues/$pr/comments?per_page=100&page=$page" 2>/dev/null)" || return 1
    [ -n "$comments" ] || return 1
    len="$(printf '%s' "$comments" | jq 'if type == "array" then length else "err" end' 2>/dev/null || echo '"err"')"
    [ "$len" = '"err"' ] && return 1
    [ "$len" -gt 0 ] || break
    hit="$(printf '%s' "$comments" | jq -c --arg M "$LEDGER_MARKER" \
      '[.[] | select((.body // "") | contains("<!-- " + $M))] | first // empty' 2>/dev/null || true)"
    if [ -n "$hit" ]; then
      LEDGER_NOTE_ID="$(printf '%s' "$hit" | jq -r '.id')"
      # A human editing the comment is not a reason to lose the budget: on unparseable
      # content keep the empty ledger but hold on to the id, so the next write repairs it
      # in place rather than adding a second ledger.
      LEDGER_JSON="$(printf '%s' "$hit" | jq -r --arg M "$LEDGER_MARKER" \
        '.body | split("<!-- " + $M)[1] | split("-->")[0] | fromjson' 2>/dev/null \
        || echo '{"heads":{},"gave_up_head":null}')"
      [ -n "$LEDGER_JSON" ] || LEDGER_JSON='{"heads":{},"gave_up_head":null}'
      return 0
    fi
    [ "$len" -lt 100 ] && break
  done
  # Scanned every page we are willing to read and found no ledger: that is a first attempt,
  # not a failure.
  return 0
}

ledger_head_attempts() { # ledger_head_attempts <sha>
  printf '%s' "$LEDGER_JSON" | jq -r --arg s "$1" '.heads[$s].attempts // 0' 2>/dev/null || echo 0
}

ledger_head_last() { # ledger_head_last <sha>
  printf '%s' "$LEDGER_JSON" | jq -r --arg s "$1" '.heads[$s].last // "unknown"' 2>/dev/null || echo unknown
}

# Sum attempts over the heads this branch actually descends from. Must run inside the
# checkout, which the workflow does with fetch-depth: 0. A rebase abandons the old SHAs,
# which stop being ancestors and stop counting — the same reset the commit-counting version
# had, kept deliberately.
ledger_branch_attempts() {
  local total=0 sha n
  while read -r sha n; do
    [ -n "$sha" ] || continue
    git cat-file -e "${sha}^{commit}" 2>/dev/null || continue
    git merge-base --is-ancestor "$sha" HEAD 2>/dev/null || continue
    total=$((total + n))
  done < <(printf '%s' "$LEDGER_JSON" | jq -r '.heads | to_entries[] | "\(.key) \(.value.attempts // 0)"' 2>/dev/null || true)
  echo "$total"
}

# True once we have already told a human to take over at a head this branch descends from,
# so the hand-off comment is posted once rather than on every re-trigger.
ledger_gave_up() {
  local sha; sha="$(printf '%s' "$LEDGER_JSON" | jq -r '.gave_up_head // empty' 2>/dev/null || true)"
  [ -n "$sha" ] || return 1
  git cat-file -e "${sha}^{commit}" 2>/dev/null || return 1
  git merge-base --is-ancestor "$sha" HEAD 2>/dev/null
}

ledger_render() { # ledger_render <json> -> comment body
  jq -rn --argjson L "$1" --arg M "$LEDGER_MARKER" --arg max "$MAX_ATTEMPTS" '
    "<!-- " + $M + "\n" + ($L | tojson) + "\n-->\n"
    + "🤖 **Renovate auto-fix ledger** — maintained automatically, please do not edit.\n\n"
    + "| head | attempts | last outcome | last attempt (UTC) |\n| --- | --- | --- | --- |\n"
    + ([$L.heads | to_entries | sort_by(.value.at) | reverse | .[]
        | "| `\(.key[0:8])` | \(.value.attempts)/\($max) | \(.value.last) | \(.value.at) |"]
       | join("\n"))
    + "\n\nAn attempt is recorded before the session starts, so one that times out, declines, or"
    + " is cancelled still spends the budget. A head is attempted once: re-running against an"
    + " unchanged commit would feed identical inputs to an identical prompt. Renovate rebasing"
    + " this branch, or the auto-fix pushing a commit, produces a new head and a fresh attempt."'
}

# Record an attempt (or its outcome) against a head. Returns non-zero if GitHub did not
# accept the write.
ledger_write() { # ledger_write <pr> <sha> <outcome> [gave_up_sha]
  local pr="$1" sha="$2" outcome="$3" gave_up="${4:-}" next body resp
  next="$(printf '%s' "$LEDGER_JSON" | jq -c --arg s "$sha" --arg o "$outcome" --arg g "$gave_up" \
    --arg at "$(date -u +%Y-%m-%dT%H:%MZ)" --argjson keep "$LEDGER_KEEP" '
      .heads[$s] = {attempts: ((.heads[$s].attempts // 0) + (if $o == "started" then 1 else 0 end)),
                    last: $o, at: $at}
      | .heads |= (to_entries | sort_by(.value.at) | reverse | .[0:$keep] | from_entries)
      | if $g != "" then .gave_up_head = $g else . end' 2>/dev/null || true)"
  [ -n "$next" ] || { echo "::warning::Could not build the ledger entry."; return 1; }

  body="$(ledger_render "$next")" || { echo "::warning::Could not render the ledger comment."; return 1; }
  if [ -n "$LEDGER_NOTE_ID" ]; then
    resp="$(gh api --method PATCH "repos/$REPO/issues/comments/$LEDGER_NOTE_ID" -f body="$body" 2>/dev/null)" || resp=""
  else
    resp="$(gh api --method POST "repos/$REPO/issues/$pr/comments" -f body="$body" 2>/dev/null)" || resp=""
  fi
  # An empty body must be treated as failure explicitly: `jq -e` exits 0 on empty input,
  # so testing the response alone would read a dropped request as a successful write and
  # hand back a false "recorded", which is exactly the uncounted attempt this prevents.
  if [ -z "$resp" ] || ! printf '%s' "$resp" | jq -e 'has("id")' >/dev/null 2>&1; then
    echo "::warning::Could not write the attempt ledger on #$pr."
    return 1
  fi
  LEDGER_NOTE_ID="$(printf '%s' "$resp" | jq -r '.id')"
  LEDGER_JSON="$next"
}

out() { [ -n "${GITHUB_OUTPUT:-}" ] && echo "$1" >> "$GITHUB_OUTPUT" || echo "$1"; }

cmd_guard() { # cmd_guard <pr> <head_sha>
  local pr="$1" head="$2" prior attempts commit_attempts
  if ! ledger_load "$pr"; then
    echo "::warning::Could not read the attempt ledger on #$pr; not proceeding rather than risk an uncounted retry."
    out "proceed=false"; return 0
  fi

  prior="$(ledger_head_attempts "$head")"
  if [ "$prior" -ge "$MAX_PER_HEAD" ]; then
    echo "::notice::Head ${head:0:8} was already attempted ${prior}x (last: $(ledger_head_last "$head")); nothing has changed since, so not attempting again."
    out "proceed=false"; return 0
  fi

  # Branch budget: ledger attempts across every head this one descends from — successes,
  # declines and timeouts alike — floored by the [claude-autofix] commit count so PRs that
  # predate the ledger keep the history they have.
  commit_attempts="$(git log --format=%s | grep -cF '[claude-autofix]' || true)"
  attempts="$(ledger_branch_attempts)"
  [ "$attempts" -ge "$commit_attempts" ] || attempts="$commit_attempts"
  echo "Prior auto-fix attempts on this branch: ${attempts}/${MAX_ATTEMPTS} (head ${head:0:8}: ${prior}/${MAX_PER_HEAD})."

  if [ "$attempts" -ge "$MAX_ATTEMPTS" ]; then
    if ledger_gave_up; then
      echo "::notice::Already handed off to a human at this point in the branch; saying nothing further."
    else
      gh pr comment "$pr" --repo "$REPO" --body \
        "🤖 Auto-fix gave up after ${MAX_ATTEMPTS} attempts — CI is still failing on this dependency update. It needs a human. No further attempts will be made unless this branch is rebased." || true
      ledger_write "$pr" "$head" "gave-up" "$head" || true
    fi
    out "proceed=false"; return 0
  fi

  # Record BEFORE the session starts. Fail closed: if GitHub will not take the write, the
  # next trigger cannot learn that this head was tried.
  if ! ledger_write "$pr" "$head" "started"; then
    echo "::warning::Could not record the attempt; not proceeding rather than spend an unaccounted session."
    out "proceed=false"; return 0
  fi
  out "proceed=true"
}

cmd_record() { # cmd_record <pr> <head_sha> <outcome>
  local pr="$1" head="$2" outcome="$3"
  ledger_load "$pr" || { echo "::warning::Could not read the ledger to record '$outcome'."; return 0; }
  ledger_write "$pr" "$head" "$outcome" || true
}

case "${1:-}" in
  guard)  shift; cmd_guard "$@" ;;
  record) shift; cmd_record "$@" ;;
  *) echo "usage: $0 {guard|record} <pr> <head_sha> [outcome]" >&2; exit 2 ;;
esac
