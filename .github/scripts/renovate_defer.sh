#!/usr/bin/env bash
# Add every dependency a 'heavy'-labelled Renovate PR wanted to update to the defer
# list in renovate.json, so Renovate stops proposing it.
#
# 'heavy' means the update is a migration, not a bump: it needs its own ticket and its
# own PR. Labelling alone only takes the PR out of the auto-fixer's scope
# (.github/workflows/renovate-autofix.yml) — Renovate keeps rebasing the branch, and
# ships a fresh PR on the next release. A defer rule is what actually stops it.
#
# Package names come from the manifest diff, never the PR body: Renovate truncates that
# table on large groups (#2307, the material-ui v9 monorepo update, lost most of its rows
# to the platform limit).
#
# The extractor covers every manager in enabledManagers, but it can always fall behind
# what Renovate proposes. It exits 4 rather than silently emitting a short list when a PR
# yields nothing, so the caller can say so instead of reporting success.
#
# Appends one rule per PR rather than editing a shared list, so each entry carries the PR
# that produced it and removing a deferral is deleting one block.
#
# Usage: renovate_defer.sh <pr-number>   (needs gh authenticated for this repo)
set -euo pipefail

PR="${1:?usage: renovate_defer.sh <pr-number>}"
CONFIG="${RENOVATE_CONFIG:-renovate.json}"

# Version-bearing lines in manifests Renovate edits. Lockfiles are excluded: a yarn.lock
# hunk names every transitive package, which would defer half the tree.
DEPS=$(gh pr diff "$PR" | awk '
  /^\+\+\+ b\// {
    path = substr($2, 3)
    manifest = (path ~ /(^|\/)package\.json$/ || path ~ /(^|\/)pyproject\.toml$/ ||
                path ~ /(^|\/)[Dd]ockerfile(_[a-zA-Z]+)?$/ ||
                path ~ /(^|\/)docker-compose[^\/]*\.ya?ml$/)
    next
  }
  !manifest { next }
  /^[-+]/ {
    # package.json:   "@mui/material": "7.3.11",
    if (match($0, /"[^"]+"[[:space:]]*:[[:space:]]*"[~^]?[0-9]/)) {
      s = substr($0, RSTART + 1); print substr(s, 1, index(s, "\"") - 1); next
    }
    # pyproject.toml / Dockerfile:   "psycopg[binary]==3.3.5"   uv==0.9.9
    # The extras group is optional and stripped: matchPackageNames wants the bare name.
    # Brackets are spelled [[] and []] because a backslash-escaped [ outside a bracket
    # expression is undefined in POSIX ERE, and CI runs mawk rather than the BWK awk a
    # developer laptop is likely to have.
    if (match($0, /[A-Za-z][A-Za-z0-9._-]*([[][A-Za-z0-9._,-]+[]])?[[:space:]]*(==|>=|~=)[[:space:]]*[0-9]/)) {
      s = substr($0, RSTART, RLENGTH); sub(/[[:space:]]*([[]|==|>=|~=).*$/, "", s); print s; next
    }
    # Dockerfile FROM / compose image:. The tag is what makes a token an image reference,
    # so internal stage refs (FROM preinstall AS cpu-install, FROM ${TORCH_DEVICE}-install)
    # carry none and fall through, as do variable-interpolated tags. depName is the image
    # minus its tag, which keeps registry-qualified names whole the way Renovate does:
    # postgres, node, gcr.io/distroless/python3-debian12.
    if (match($0, /(^[-+]FROM[[:space:]]|[[:space:]]image:[[:space:]]*)/)) {
      n = split($0, f, /[[:space:]]+/)
      for (i = 1; i <= n; i++) {
        if (f[i] ~ /^--/ || f[i] == "AS" || f[i] !~ /:/) continue
        if (f[i] ~ /\$/ || f[i] ~ /^image:/) continue
        sub(/:.*$/, "", f[i]); print f[i]; break
      }
    }
  }
' | sort -u)

# Exit 4 = nothing to defer (a lockfile-only PR, say). Distinct from a real failure so
# the caller can treat it as a no-op rather than a red run.
[ -n "$DEPS" ] || { echo "No manifest dependency changes found in PR #$PR." >&2; exit 4; }

# Skip anything already deferred, so re-labelling a rebased PR is a no-op.
NEW=$(jq -n --argjson deps "$(printf '%s\n' "$DEPS" | jq -R . | jq -s .)" \
  --slurpfile cfg "$CONFIG" '
    ($cfg[0].packageRules // [])
    | map(select(.description? // "" | startswith("Deferred by PR ")) | .matchPackageNames[]?)
    | . as $deferred | $deps - $deferred')

if [ "$(jq 'length' <<<"$NEW")" -eq 0 ]; then
  echo "Every dependency in PR #$PR is already deferred; nothing to do." >&2
  exit 3
fi

TITLE=$(gh pr view "$PR" --json title --jq .title)
jq --indent 2 --argjson deps "$NEW" --arg pr "$PR" --arg title "$TITLE" '
  .packageRules += [{
    description: ("Deferred by PR #" + $pr + " (" + $title + "), labelled heavy: this update is a migration, not a bump, and is tracked on its own ticket. Delete this rule to let Renovate propose it again."),
    matchPackageNames: $deps,
    enabled: false
  }]' "$CONFIG" > "$CONFIG.tmp" && mv "$CONFIG.tmp" "$CONFIG"

# jq prints one array element per line; the config is prettier-formatted, so a bare jq
# write reflows every short array in the file and buries the one real change. The width
# is pinned because it is what the committed file was formatted at — prettier's default
# 80 would reflow unrelated lines just as badly.
npx --yes prettier --print-width 100 --write "$CONFIG" >/dev/null

echo "Deferred from PR #$PR:"
jq -r '.[] | "  " + .' <<<"$NEW"

if [ -n "${GITHUB_OUTPUT:-}" ]; then
  {
    echo "deps=$(jq -r 'join(", ")' <<<"$NEW")"
    echo "title=$TITLE"
  } >> "$GITHUB_OUTPUT"
fi
