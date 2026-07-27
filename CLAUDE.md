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

## Code style

Write code that reads like the surrounding code: match its comment density, naming, and idiom.

## Frontend

All UI work uses MUI components styled via `sx` with theme tokens — see [genai-engine/ui/CLAUDE.md](genai-engine/ui/CLAUDE.md) for the rules.
