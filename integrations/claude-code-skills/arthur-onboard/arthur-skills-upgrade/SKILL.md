---
name: arthur-skills-upgrade
description: Upgrade locally installed arthur-onboard-*, arthur-insights*, and arthur-skills-upgrade skills to the latest version from GitHub main branch. Checks version fields, reports stale skills, and updates in place after confirmation.
allowed-tools: Bash
version: 1.1.0
---

# Upgrade Arthur Skills

Check locally installed `arthur-onboard-*`, `arthur-insights*`, and `arthur-skills-upgrade`
skills for updates and upgrade any that are behind the latest version on GitHub main.

---

## Step 1 — Find installed skills

```bash
echo "=== Global install (~/.claude/skills/) ==="
ls -d ~/.claude/skills/arthur-onboard-* ~/.claude/skills/arthur-insights* ~/.claude/skills/arthur-skills-upgrade 2>/dev/null || echo "(none)"

echo ""
echo "=== Project install (.claude/skills/) ==="
ls -d .claude/skills/arthur-onboard-* .claude/skills/arthur-insights* .claude/skills/arthur-skills-upgrade 2>/dev/null || echo "(none)"
```

Collect all found paths. If none are found in either location, tell the user no
`arthur-onboard-*`, `arthur-insights*`, or `arthur-skills-upgrade` skills are installed and show the install command from the README.

---

## Step 2 — Check versions

For each installed skill directory, extract the local version and compare against GitHub main.
Also load `~/.claude/arthur-skills-skip-versions.txt` (format: one `skill_name=version` per line)
to suppress prompts for versions the user has previously chosen to skip.

```bash
BASE="https://raw.githubusercontent.com/arthur-ai/arthur-engine/main/integrations/claude-code-skills/arthur-onboard"
SKIP_FILE="$HOME/.claude/arthur-skills-skip-versions.txt"

STALE=()
OK=()
SKIP=()
USER_SKIPPED=()

for skill_dir in ~/.claude/skills/arthur-onboard-* ~/.claude/skills/arthur-insights* ~/.claude/skills/arthur-skills-upgrade \
                 .claude/skills/arthur-onboard-* .claude/skills/arthur-insights* .claude/skills/arthur-skills-upgrade; do
  [ -f "$skill_dir/SKILL.md" ] || continue
  skill_name=$(basename "$skill_dir")

  local_version=$(grep "^version:" "$skill_dir/SKILL.md" 2>/dev/null | awk '{print $2}')
  local_version=${local_version:-"unknown"}

  remote_content=$(curl -sSLf "$BASE/$skill_name/SKILL.md" 2>/dev/null)
  if [ -z "$remote_content" ]; then
    SKIP+=("$skill_name")
    echo "SKIP    $skill_name (not found on main branch)"
    continue
  fi

  remote_version=$(echo "$remote_content" | grep "^version:" | awk '{print $2}')
  remote_version=${remote_version:-"unknown"}

  if [ "$local_version" = "$remote_version" ]; then
    OK+=("$skill_name ($local_version)")
    echo "OK      $skill_name ($local_version)"
  else
    # Check if the user previously chose to skip this exact remote version
    skipped_ver=$(grep "^$skill_name=" "$SKIP_FILE" 2>/dev/null | cut -d'=' -f2)
    if [ "$skipped_ver" = "$remote_version" ]; then
      USER_SKIPPED+=("$skill_name ($local_version → $remote_version, skipped)")
      echo "SKIPPED $skill_name ($local_version → $remote_version, user-skipped this version)"
    else
      STALE+=("$skill_dir|$skill_name|$local_version|$remote_version")
      echo "UPDATE  $skill_name: $local_version → $remote_version"
    fi
  fi
done

# Persist stale list so Step 3 can read it in a fresh shell
printf '%s\n' "${STALE[@]}" > /tmp/arthur-stale-skills.txt
```

Present the results clearly:
- `OK` — already up to date
- `UPDATE` — stale, update available
- `SKIPPED` — user previously chose to skip this version
- `SKIP` — not found on main (installed manually or removed upstream)

If all skills are `OK` or `SKIPPED`, tell the user everything is up to date and exit.

---

## Step 3 — Prompt and upgrade

Show the user the list of skills that have updates (from the `UPDATE` entries). Then ask:

> "Found N skill(s) with updates:
>   - `<skill-name>`: `<old>` → `<new>`
>   ...
>
> How would you like to proceed?
>   1. **Yes** — upgrade now
>   2. **Not now** — skip this time (you'll be asked again next run)
>   3. **Skip version** — don't ask about these versions again until a newer release"

**If the user chooses "Yes"** — download and replace each stale skill:

```bash
BASE="https://raw.githubusercontent.com/arthur-ai/arthur-engine/main/integrations/claude-code-skills/arthur-onboard"

while IFS= read -r entry; do
  [ -n "$entry" ] || continue
  skill_dir=$(echo "$entry" | cut -d'|' -f1)
  skill_name=$(echo "$entry" | cut -d'|' -f2)
  old_ver=$(echo "$entry" | cut -d'|' -f3)
  new_ver=$(echo "$entry" | cut -d'|' -f4)

  new_content=$(curl -sSLf "$BASE/$skill_name/SKILL.md" 2>/dev/null)
  if [ $? -eq 0 ] && [ -n "$new_content" ]; then
    echo "$new_content" > "$skill_dir/SKILL.md"
    echo "Updated: $skill_name ($old_ver → $new_ver)"

    # Some skills ship companion files — re-download them alongside SKILL.md
    if [ "$skill_name" = "arthur-onboard-instrument" ]; then
      examples=$(curl -sSLf "$BASE/arthur-onboard-instrument/EXAMPLES.md" 2>/dev/null)
      if [ -n "$examples" ]; then
        echo "$examples" > "$skill_dir/EXAMPLES.md"
        echo "Updated: $skill_name/EXAMPLES.md"
      fi
    fi
  else
    echo "FAILED:  $skill_name (could not fetch from GitHub)"
  fi
done < /tmp/arthur-stale-skills.txt
rm -f /tmp/arthur-stale-skills.txt
```

**If the user chooses "Not now"** — exit without upgrading. No file changes. The user will be prompted again on the next run.

```bash
rm -f /tmp/arthur-stale-skills.txt
```

**If the user chooses "Skip version"** — record the current remote version for each stale skill in the skip file so they are not prompted again until a newer version is released:

```bash
SKIP_FILE="$HOME/.claude/arthur-skills-skip-versions.txt"

while IFS= read -r entry; do
  [ -n "$entry" ] || continue
  skill_name=$(echo "$entry" | cut -d'|' -f2)
  new_ver=$(echo "$entry" | cut -d'|' -f4)

  # Remove any existing entry for this skill, then append the new skipped version
  grep -v "^$skill_name=" "$SKIP_FILE" 2>/dev/null > /tmp/arthur-skip-tmp && mv /tmp/arthur-skip-tmp "$SKIP_FILE" || true
  echo "$skill_name=$new_ver" >> "$SKIP_FILE"
  echo "Skipping: $skill_name (will not prompt again until a version newer than $new_ver is released)"
done < /tmp/arthur-stale-skills.txt
rm -f /tmp/arthur-stale-skills.txt
```

---

## Step 4 — Done

Report:
- How many skills were updated
- How many were already up to date
- Any that failed or were skipped

Remind the user to re-run `/arthur-onboard-oss`, `/arthur-onboard-platform`, or
`/arthur-insights` to pick up any new behaviour or steps from updated skills.
