#!/usr/bin/env bash
#
# Fail if any uv.lock in the repo disagrees with the pyproject.toml beside it.
#
# `uv lock --check` re-resolves from the manifest and exits non-zero if the
# lockfile is not what that resolution produces. It catches both shapes of the
# drift Renovate can leave behind:
#
#   1. The manifest is unsatisfiable, so the lock could never have been
#      regenerated (openai==3.0.0 against litellm's openai<3.0.0, PR #2134).
#   2. The manifest resolves fine but the lock still pins the old version, so
#      the "upgrade" is absent from everything that installs with --frozen
#      (python-keycloak==7.1.1 with 5.12.0 locked, PR #2124).
#
# Projects are discovered rather than listed, so a new one is covered the day it
# is added instead of the day someone remembers to extend this script.
#
# Runs in CI via .github/workflows/arthur-engine-workflow.yml; safe to run
# locally from the repo root as well.

# No `set -e`: every failure below is inspected and reported deliberately rather
# than aborting the run, so a second broken project is still shown to whoever has
# to fix them.
set -uo pipefail

repo_root="$(git rev-parse --show-toplevel)" || {
  echo "::error::Not inside a git repository; cannot locate the projects to check." >&2
  exit 1
}
cd "$repo_root" || exit 1

# Populated with a read loop rather than `mapfile`, which macOS's bash 3.2 does
# not have — this script is meant to run locally as well as on the CI runner.
LOCKS=()
while IFS= read -r lock; do
  LOCKS+=("$lock")
done < <(
  find . -name uv.lock \
    -not -path '*/node_modules/*' \
    -not -path '*/.venv/*' \
    -not -path '*/.git/*' \
    | sort
)

if [ "${#LOCKS[@]}" -eq 0 ]; then
  echo "::error::No uv.lock files found. Either the repo layout moved or this script is looking in the wrong place."
  exit 1
fi

echo "Checking ${#LOCKS[@]} uv project(s) against their manifests."
echo

stale=()
unresolvable=()
diagnostics=""

for lock in "${LOCKS[@]}"; do
  proj="$(dirname "$lock")"
  proj="${proj#./}"

  if [ ! -f "$proj/pyproject.toml" ]; then
    echo "::error file=$lock::$lock has no pyproject.toml beside it."
    unresolvable+=("$proj")
    continue
  fi

  printf '%-42s ' "$proj"

  if uv lock --check --directory "$proj" >/dev/null 2>&1; then
    echo "ok"
    continue
  fi

  # --check only reports THAT the lock is wrong. Re-running the real resolve is
  # what separates the two causes, and they need opposite responses: a stale lock
  # just has to be regenerated, while an unsatisfiable manifest means the bump
  # itself cannot stand. `uv lock` leaves the file untouched when it fails, so the
  # restore below only matters on the stale path.
  if out=$(uv lock --directory "$proj" 2>&1); then
    echo "STALE — lock not regenerated for the manifest change"
    stale+=("$proj")
    diagnostics="${diagnostics}
--- ${proj}: regenerating the lock changes these pins ---
${out}
$(git --no-pager diff --stat -- "$proj/uv.lock" 2>/dev/null)
"
  else
    echo "UNRESOLVABLE — pyproject.toml has no valid resolution"
    unresolvable+=("$proj")
    diagnostics="${diagnostics}
--- ${proj}: the manifest cannot be resolved at all ---
${out}
"
  fi
  git checkout -- "$proj/uv.lock" 2>/dev/null || true
done

echo

if [ "${#stale[@]}" -eq 0 ] && [ "${#unresolvable[@]}" -eq 0 ]; then
  echo "All uv.lock files agree with their manifests."
  exit 0
fi

echo "$diagnostics"

# Written to the job summary as well as the log: this failure is nearly always a
# Renovate PR, and the person triaging it needs the decision tree, not a stack
# trace. Keep this in sync with the packageRules commentary in /renovate.json.
{
  echo
  echo "## Lockfile drift detected"
  echo
  echo "\`pyproject.toml\` and \`uv.lock\` disagree, so what the manifest declares is"
  echo "**not** what \`uv sync --frozen\` installs — not in CI, not in the Docker"
  echo "images, not in a teammate's checkout. If this is a Renovate PR, its lockfile"
  echo "step failed and it shipped the manifest edit on its own."
  echo

  if [ "${#stale[@]}" -gt 0 ]; then
    echo "### Stale lock: ${stale[*]}"
    echo
    echo "The manifest resolves fine; the lock simply was not regenerated, so the"
    echo "update is absent from everything that installs from it. Regenerate and"
    echo "commit:"
    echo
    for proj in "${stale[@]}"; do
      echo "    uv lock --directory $proj"
    done
    echo
  fi

  if [ "${#unresolvable[@]}" -gt 0 ]; then
    echo "### Unresolvable manifest: ${unresolvable[*]}"
    echo
    echo "No lockfile could satisfy this pyproject.toml, so regenerating will not"
    echo "help. The resolver output above names both sides of the conflict. Either:"
    echo
    echo "1. **Move the lagging constraint forward.** If the package blocking the"
    echo "   update has a release that accepts the new version, bump it in the same"
    echo "   PR. Never cap or downgrade the package the PR is updating — that turns"
    echo "   the PR into a no-op while making it look fixed."
    echo "2. **Cap it, if the blocker is upstream with no fix yet.** Close the PR and"
    echo "   add an \`allowedVersions\` rule for the package in \`/renovate.json\`,"
    echo "   naming the dependency that imposes the ceiling and the condition for"
    echo "   lifting it, so Renovate stops re-proposing an update that cannot land."
    echo "   The \`openai\`, \`transformers\` and \`importlib-metadata\` rules there are"
    echo "   existing examples."
    echo
  fi

  echo "Do not resolve this by hand-editing uv.lock."
} | tee -a "${GITHUB_STEP_SUMMARY:-/dev/null}"

exit 1
