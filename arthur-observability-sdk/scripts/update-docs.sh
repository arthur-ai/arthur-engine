#!/usr/bin/env bash
set -euo pipefail

# Accept an optional base branch argument (default: dev)
BASE_BRANCH="${1:-dev}"

# Check if the branch is up-to-date with its remote (only for local branches)
if git rev-parse --verify "$BASE_BRANCH" &>/dev/null && \
   ! git rev-parse --verify "origin/$BASE_BRANCH" &>/dev/null 2>&1; then
  : # local-only branch, no remote to compare against
elif git rev-parse --verify "$BASE_BRANCH" &>/dev/null && \
     git rev-parse --verify "origin/$BASE_BRANCH" &>/dev/null 2>&1; then
  LOCAL=$(git rev-parse "$BASE_BRANCH")
  REMOTE=$(git rev-parse "origin/$BASE_BRANCH")
  if [ "$LOCAL" != "$REMOTE" ]; then
    BEHIND=$(git rev-list --count "$BASE_BRANCH..origin/$BASE_BRANCH")
    if [ "$BEHIND" -gt 0 ]; then
      echo "Warning: '$BASE_BRANCH' is $BEHIND commit(s) behind 'origin/$BASE_BRANCH'."
      echo "  [f] Fetch origin/$BASE_BRANCH and continue"
      echo "  [c] Continue anyway"
      echo "  [s] Skip / cancel"
      read -r -p "Choice [f/c/s]: " CHOICE
      case "$CHOICE" in
        f|F)
          echo "Fetching origin/$BASE_BRANCH..."
          git fetch origin "$BASE_BRANCH:$BASE_BRANCH"
          ;;
        c|C)
          echo "Continuing with local '$BASE_BRANCH' as-is."
          ;;
        *)
          echo "Cancelled."
          exit 0
          ;;
      esac
    fi
  fi
fi

MERGE_BASE=$(git merge-base HEAD "$BASE_BRANCH")

PY_CHANGED=0
TS_CHANGED=0
git diff --quiet "$MERGE_BASE..HEAD" -- python/src/arthur_observability_sdk/ || PY_CHANGED=1
git diff --quiet "$MERGE_BASE..HEAD" -- typescript/src/ || TS_CHANGED=1

if [ "$PY_CHANGED" -eq 0 ] && [ "$TS_CHANGED" -eq 0 ]; then
  echo "No SDK source changes detected — skipping doc update."
  exit 0
fi

DIFF_FILE=$(mktemp /tmp/arthur-sdk-diff.XXXXXX)
trap 'rm -f "$DIFF_FILE"' EXIT      # always clean up, success or failure

# Collect diffs from both Python and TypeScript sources
{
  if [ "$PY_CHANGED" -eq 1 ]; then
    git diff "$MERGE_BASE..HEAD" -- python/src/arthur_observability_sdk/
  fi
  if [ "$TS_CHANGED" -eq 1 ]; then
    git diff "$MERGE_BASE..HEAD" -- typescript/src/
  fi
} > "$DIFF_FILE"

echo "SDK source changes detected (Python=$PY_CHANGED, TypeScript=$TS_CHANGED). Invoking Claude to update docs..."
claude -p "/update-docs $DIFF_FILE" --allowedTools "Read,Edit,Write" \
  --model claude-haiku-4-5-20251001

echo ""
echo "Review: git diff docs/"
echo "Commit: git add docs/ && git commit -m 'docs: update for recent changes'"
