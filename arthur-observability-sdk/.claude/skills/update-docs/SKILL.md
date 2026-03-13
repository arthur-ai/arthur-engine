## Changes to review
Read the git diff from the file path provided as the first argument: $0

## Target docs
- docs/getting-started.md   — Arthur init, session/user/attributes helpers, instrumentation
- docs/prompt-management.md — get_prompt, render_prompt, span attributes

## Update rules
- Changes to arthur.py (session/user/attributes, instrument_* methods) → getting-started.md
- Changes to _client.py or arthur.py prompt methods → prompt-management.md
- Pure refactors with no behaviour change → skip both
- Changes to telemetry.py → getting-started.md (init/shutdown section)

## When to create a NEW doc file (Write tool)
Only create a new file in docs/ when ALL of these are true:
  1. The change introduces a major new user-facing feature (not a refinement of existing behaviour).
  2. The content does not fit naturally into either existing guide.
  3. The new file would be at least 200 words of meaningful content.
Otherwise, edit the most relevant existing file.

## Instructions
1. Read the diff file at path $0.
2. Decide which docs (if any) need updating using the rules above.
3. Read the affected doc file(s).
4. Edit only the sections that describe the changed behaviour, or create a new file
   only if the three criteria above are all met.
5. Preserve existing structure, tone, and code-example style.
6. If no update is needed, output "No documentation update required." and stop.
