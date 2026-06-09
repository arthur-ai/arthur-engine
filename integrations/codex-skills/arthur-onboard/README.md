# Arthur Onboarding Skills for Codex

Use the Arthur onboarding skill sets with Codex to onboard agentic applications
to either self-hosted Arthur GenAI Engine or Arthur Platform.

The source skills are stored in this repository under:

```text
claude-code-skills/arthur-onboard/
```

Codex loads user-installed skills from `$CODEX_HOME/skills`. If `CODEX_HOME` is
not set, Codex uses `~/.codex`, so the default skill directory is:

```text
~/.codex/skills
```

After installing or updating skills, restart Codex so it can load the new skill
metadata.

## Skill Sets

Install the skill set for the Arthur workflow you want to use.

### OSS GenAI Engine

Use this set to onboard to a self-hosted Arthur GenAI Engine, either local
Docker or a remote OSS deployment:

- `arthur-onboard-oss`
- `arthur-onboard-oss-engine`
- `arthur-onboard-task`
- `arthur-onboard-analyze`
- `arthur-onboard-instrument`
- `arthur-onboard-prompts`
- `arthur-onboard-verify`
- `arthur-onboard-eval-provider`
- `arthur-onboard-evals`

### Arthur Platform

Use this set to onboard to Arthur Platform SaaS:

- `arthur-onboard-platform`
- `arthur-onboard-platform-access`
- `arthur-onboard-platform-workspace`
- `arthur-onboard-platform-engine`
- `arthur-onboard-platform-model`
- `arthur-onboard-platform-token`
- `arthur-onboard-analyze`
- `arthur-onboard-instrument`
- `arthur-onboard-prompts`
- `arthur-onboard-verify`
- `arthur-onboard-eval-provider`
- `arthur-onboard-evals`

## Install by Prompt

You can ask Codex to install either skill set for you.

### OSS GenAI Engine Prompt

Paste this into a Codex thread:

```text
Install the Arthur OSS onboarding Codex skills from arthur-ai/arthur-engine.

Install these skill folders into ${CODEX_HOME:-~/.codex}/skills:
- arthur-onboard-oss
- arthur-onboard-oss-engine
- arthur-onboard-task
- arthur-onboard-analyze
- arthur-onboard-instrument
- arthur-onboard-prompts
- arthur-onboard-verify
- arthur-onboard-eval-provider
- arthur-onboard-evals

Fetch each SKILL.md from:
https://raw.githubusercontent.com/arthur-ai/arthur-engine/main/integrations/claude-code-skills/arthur-onboard/<skill-name>/SKILL.md

Also fetch the instrumentation examples reference:
https://raw.githubusercontent.com/arthur-ai/arthur-engine/main/integrations/claude-code-skills/arthur-onboard/arthur-onboard-instrument/EXAMPLES.md
Save it to ${CODEX_HOME:-~/.codex}/skills/arthur-onboard-instrument/EXAMPLES.md.

Create each directory as needed. After installation, remind me to restart Codex.
```

### Arthur Platform Prompt

Paste this into a Codex thread:

```text
Install the Arthur Platform onboarding Codex skills from arthur-ai/arthur-engine.

Install these skill folders into ${CODEX_HOME:-~/.codex}/skills:
- arthur-onboard-platform
- arthur-onboard-platform-access
- arthur-onboard-platform-workspace
- arthur-onboard-platform-engine
- arthur-onboard-platform-model
- arthur-onboard-platform-token
- arthur-onboard-analyze
- arthur-onboard-instrument
- arthur-onboard-prompts
- arthur-onboard-verify
- arthur-onboard-eval-provider
- arthur-onboard-evals

Fetch each SKILL.md from:
https://raw.githubusercontent.com/arthur-ai/arthur-engine/main/integrations/claude-code-skills/arthur-onboard/<skill-name>/SKILL.md

Also fetch the instrumentation examples reference:
https://raw.githubusercontent.com/arthur-ai/arthur-engine/main/integrations/claude-code-skills/arthur-onboard/arthur-onboard-instrument/EXAMPLES.md
Save it to ${CODEX_HOME:-~/.codex}/skills/arthur-onboard-instrument/EXAMPLES.md.

Create each directory as needed. After installation, remind me to restart Codex.
```

To install from a branch or tag instead of `main`, add this line to either
prompt:

```text
Use ref <branch-or-tag> instead of main.
```

## Install From a Local Checkout

Run this from the `integrations` directory of this repository. Set `SKILLS` to
the workflow you want to install.

```bash
OSS_SKILLS="arthur-onboard-oss arthur-onboard-oss-engine arthur-onboard-task arthur-onboard-analyze arthur-onboard-instrument arthur-onboard-prompts arthur-onboard-verify arthur-onboard-eval-provider arthur-onboard-evals"
PLATFORM_SKILLS="arthur-onboard-platform arthur-onboard-platform-access arthur-onboard-platform-workspace arthur-onboard-platform-engine arthur-onboard-platform-model arthur-onboard-platform-token arthur-onboard-analyze arthur-onboard-instrument arthur-onboard-prompts arthur-onboard-verify arthur-onboard-eval-provider arthur-onboard-evals"

SKILLS="$OSS_SKILLS"
# SKILLS="$PLATFORM_SKILLS"

SKILL_DEST="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$SKILL_DEST"

for skill in $SKILLS; do
  rm -rf "$SKILL_DEST/$skill"
  cp -R "claude-code-skills/arthur-onboard/$skill" "$SKILL_DEST/$skill"
done
# Also install the instrumentation examples reference
cp "claude-code-skills/arthur-onboard/arthur-onboard-instrument/EXAMPLES.md" \
   "$SKILL_DEST/arthur-onboard-instrument/EXAMPLES.md"
```

## Install From GitHub

Use this if you do not have a local checkout. Set `SKILLS` to the workflow you
want to install.

```bash
OSS_SKILLS="arthur-onboard-oss arthur-onboard-oss-engine arthur-onboard-task arthur-onboard-analyze arthur-onboard-instrument arthur-onboard-prompts arthur-onboard-verify arthur-onboard-eval-provider arthur-onboard-evals"
PLATFORM_SKILLS="arthur-onboard-platform arthur-onboard-platform-access arthur-onboard-platform-workspace arthur-onboard-platform-engine arthur-onboard-platform-model arthur-onboard-platform-token arthur-onboard-analyze arthur-onboard-instrument arthur-onboard-prompts arthur-onboard-verify arthur-onboard-eval-provider arthur-onboard-evals"

SKILLS="$OSS_SKILLS"
# SKILLS="$PLATFORM_SKILLS"

ARTHUR_ENGINE_REF="${ARTHUR_ENGINE_REF:-main}"
BASE="https://raw.githubusercontent.com/arthur-ai/arthur-engine/$ARTHUR_ENGINE_REF/integrations/claude-code-skills/arthur-onboard"
SKILL_DEST="${CODEX_HOME:-$HOME/.codex}/skills"

for skill in $SKILLS; do
  mkdir -p "$SKILL_DEST/$skill"
  curl -sSLf "$BASE/$skill/SKILL.md" > "$SKILL_DEST/$skill/SKILL.md" \
    || { echo "FAILED: $skill"; rm -f "$SKILL_DEST/$skill/SKILL.md"; }
done
# Also install the instrumentation examples reference
curl -sSLf "$BASE/arthur-onboard-instrument/EXAMPLES.md" > "$SKILL_DEST/arthur-onboard-instrument/EXAMPLES.md" \
  || { echo "FAILED: arthur-onboard-instrument/EXAMPLES.md"; rm -f "$SKILL_DEST/arthur-onboard-instrument/EXAMPLES.md"; }
```

To install from a branch or tag instead of `main`, set `ARTHUR_ENGINE_REF`
before running the script.

Restart Codex after either install path completes.

## Use the Skills

Open Codex in the root of the agentic application repository you want to
onboard.

For OSS GenAI Engine, ask Codex:

```text
Use the arthur-onboard-oss skill to onboard this repository to Arthur GenAI Engine.
```

For Arthur Platform, ask Codex:

```text
Use the arthur-onboard-platform skill to onboard this repository to Arthur Platform.
```

## Prerequisites

For both workflows:

- Git repository recommended
- Docker Desktop for local Docker or Docker Compose engine deployment

For OSS GenAI Engine:

- Local Docker install or remote Arthur GenAI Engine URL and API key

For Arthur Platform:

- Arthur Platform account
- Permission to create or use service accounts
- Existing engines must be deployed with platform-issued data plane credentials,
  not OSS credentials

## State File

The onboarding workflow creates `.arthur-engine.env` in the target application
repository. It stores values such as:

- `ARTHUR_ENGINE_URL`
- `ARTHUR_API_KEY`
- `ARTHUR_TASK_ID`

This file contains project-specific connection details and credentials. The
skill should add `.arthur-engine.env` to `.gitignore`; do not commit it.
