# CLAUDE.md

Arthur Engine is an AI/ML monitoring and governance platform. Each component has its own CLAUDE.md with commands and gotchas:

- [genai-engine/](genai-engine/CLAUDE.md) — FastAPI REST API for LLM evaluation and guardrailing (Python 3.12, PostgreSQL + pgVector)
- [genai-engine/ui/](genai-engine/ui/CLAUDE.md) — React 19 + TypeScript + Vite frontend
- [ml-engine/](ml-engine/CLAUDE.md) — job-based evaluation engine for ML model monitoring (Python 3.13)
- [arthur-observability-sdk/](arthur-observability-sdk/CLAUDE.md) — Python SDK for tracing and prompt management

## Workflow

- `dev` is the default branch: feature branches come from `dev` and PRs target it. `main` is production releases.
- Pre-commit hooks format code and run the unit test suites — a slow or failing commit is usually them, not git.
- GenAI Engine API changes require a changelog entry: `uv run generate_changelog` from `genai-engine/`.
- Repo skills cover environment setup and running the stack: `setup-genai-dev`, `start-genai-backend`, `start-genai-frontend`.
- Full-stack local deployment: [deployment/docker-compose/genai-engine/](deployment/docker-compose/genai-engine/) (`cp .env.template .env`, then `docker compose up`).

## Dependencies

Every Python project here is `pyproject.toml` + `uv.lock`, and the two must never disagree. CI installs
with `uv sync --frozen`, which replays the lockfile and never looks at the manifest — so a manifest-only
change is invisible at runtime while still looking merged. Change a pin, then `uv lock --directory <project>`
and commit both files together. Never hand-edit `uv.lock`.

`check-dependency-automation` in [the CI workflow](.github/workflows/arthur-engine-workflow.yml) enforces
this across all four uv projects via
[`.github/scripts/check-lockfile-drift.sh`](.github/scripts/check-lockfile-drift.sh), which you can run
locally from the repo root. It reports one of two states:

- **STALE** — the manifest resolves but the lock was not regenerated. Run `uv lock` and commit.
- **UNRESOLVABLE** — nothing can satisfy the manifest, usually because a *transitive* constraint of
  another pinned dependency caps the package being bumped (`litellm` caps `openai<3.0.0`; `gliner` caps
  `transformers`; `presidio-anonymizer` caps `cryptography`). Move the lagging dependency forward — never
  cap or downgrade the one being updated. If nothing upstream lifts the ceiling yet, add an
  `allowedVersions` rule in [renovate.json](renovate.json) so Renovate stops re-proposing it, naming the
  blocker and the condition for removing the cap.

Renovate opens PRs that edit the manifest without the lock whenever its lockfile step fails, and offers no
way to fail closed — that gate is the only thing that catches it. See the `description` at the top of
[renovate.json](renovate.json).

## Code style

Write code that reads like the surrounding code: match its comment density, naming, and idiom.

## Frontend

All UI work uses MUI components styled via `sx` with theme tokens — see [genai-engine/ui/CLAUDE.md](genai-engine/ui/CLAUDE.md) for the rules.
