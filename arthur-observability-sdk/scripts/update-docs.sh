#!/usr/bin/env bash
set -euo pipefail

# Detect the remote default branch (main, master, etc.) without hardcoding
REMOTE_HEAD=$(git rev-parse --abbrev-ref origin/HEAD 2>/dev/null || echo "origin/main")
MERGE_BASE=$(git merge-base HEAD "$REMOTE_HEAD")

if git diff --quiet "$MERGE_BASE..HEAD" -- 'src/arthur_observability_sdk/'; then
  echo "No SDK source changes detected — skipping doc update."
  exit 0
fi

DIFF_FILE=$(mktemp /tmp/arthur-sdk-diff.XXXXXX)
trap 'rm -f "$DIFF_FILE"' EXIT      # always clean up, success or failure

git diff "$MERGE_BASE..HEAD" -- src/arthur_observability_sdk/ > "$DIFF_FILE"

echo "SDK source changes detected. Invoking Claude to update docs..."
claude -p "/update-docs $DIFF_FILE" --allowedTools "Read,Edit,Write" \
  --model claude-haiku-4-5-20251001

echo ""
echo "Review: git diff docs/"
echo "Commit: git add docs/ && git commit -m 'docs: update for recent changes'"
