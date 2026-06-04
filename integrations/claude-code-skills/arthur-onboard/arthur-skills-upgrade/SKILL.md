---
name: arthur-skills-upgrade
description: Upgrade locally installed arthur-onboard-* and arthur-skills-upgrade skills to the latest version from GitHub main branch. Checks version fields, reports stale skills, and updates in place after confirmation.
allowed-tools: Bash
version: 1.0.0
---

# Upgrade Arthur Onboarding Skills

Check locally installed `arthur-onboard-*` and `arthur-skills-upgrade` skills for updates
and upgrade any that are behind the latest version on GitHub main.

---

## Step 1 — Find installed skills

```bash
echo "=== Global install (~/.claude/skills/) ==="
ls -d ~/.claude/skills/arthur-onboard-* ~/.claude/skills/arthur-skills-upgrade 2>/dev/null || echo "(none)"

echo ""
echo "=== Project install (.claude/skills/) ==="
ls -d .claude/skills/arthur-onboard-* .claude/skills/arthur-skills-upgrade 2>/dev/null || echo "(none)"
```

Collect all found paths. If none are found in either location, tell the user no
`arthur-onboard-*` or `arthur-skills-upgrade` skills are installed and show the install command from the README.

---

## Step 2 — Check versions

For each installed skill directory, extract the local version and compare against GitHub main.

```bash
BASE="https://raw.githubusercontent.com/arthur-ai/arthur-engine/main/integrations/claude-code-skills/arthur-onboard"

STALE=()
OK=()
SKIP=()

for skill_dir in ~/.claude/skills/arthur-onboard-* ~/.claude/skills/arthur-skills-upgrade \
                 .claude/skills/arthur-onboard-* .claude/skills/arthur-skills-upgrade; do
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
    STALE+=("$skill_dir|$skill_name|$local_version|$remote_version")
    echo "UPDATE  $skill_name: $local_version → $remote_version"
  fi
done

# Persist stale list so Step 3 can read it in a fresh shell
printf '%s\n' "${STALE[@]}" > /tmp/arthur-stale-skills.txt
```

Present the results clearly:
- `OK` — already up to date
- `UPDATE` — stale, will be upgraded
- `SKIP` — not found on main (installed manually or removed upstream)

If all skills are `OK`, tell the user everything is up to date and exit.

---

## Step 3 — Confirm and upgrade

Show the user the list of skills that have updates. Ask:

> "Found N skill(s) with updates. Upgrade now?"

Once confirmed, download and replace each stale skill:

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

---

## Step 4 — Done

Report:
- How many skills were updated
- How many were already up to date
- Any that failed or were skipped

Remind the user to re-run `/arthur-onboard-oss` or `/arthur-onboard-platform` to pick
up any new behaviour or steps from updated skills.
