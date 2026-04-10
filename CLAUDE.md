# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Arthur Engine is a Python-based AI/ML monitoring and governance platform with three main components:

- **GenAI Engine**: FastAPI-based REST API for LLM evaluation and guardrailing
- **ML Engine**: Job-based evaluation engine for ML model monitoring
- **Frontend UI**: React + TypeScript + Vite web application

## Technologies

**Backend:**

- Python 3.12 (GenAI Engine), Python 3.13 (ML Engine)
- FastAPI, SQLAlchemy, PostgreSQL with pgVector
- OpenAI/Azure LLMs, LangChain, LiteLLM
- ML Models: Transformers, Sentence Transformers, Spacy
- NER/PII: Presidio, GLiNER
- Alembic for database migrations

**Frontend:**

- React 19, TypeScript, Vite
- **MUI (Material UI) v7** - Primary component library (`@mui/material`, `@mui/icons-material`, `@mui/x-date-pickers`)
- Emotion (`@emotion/react`, `@emotion/styled`) - Styling engine for MUI
- Tailwind CSS - Utility classes for layout supplementing MUI
- TanStack Query/Table, Material React Table
- Zustand for state management

**Infrastructure:**

- Docker, Docker Compose, Helm, AWS ECS
- OpenTelemetry, NewRelic
- Pytest, Coverage, Locust

## Common Commands

### GenAI Engine

```bash
# Setup
cd genai-engine
uv sync --group dev --group linters

# Start PostgreSQL (required)
docker compose up

# Database setup
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=changeme_pg_password
export POSTGRES_URL=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=arthur_genai_engine
export GENAI_ENGINE_SECRET_STORE_KEY="some_test_key"
uv run alembic upgrade head

# Run development server
export PYTHONPATH="src:$PYTHONPATH"
uv run serve
# Access at http://localhost:3030/docs

# Testing
uv run pytest -m "unit_tests"
uv run pytest -m "unit_tests" --cov=src --cov-fail-under=79
./tests/test_remote.sh  # Integration tests

# Database migrations
uv run alembic revision --autogenerate -m "<message>"
uv run alembic upgrade head

# Code quality
uv run isort src --profile black
uv run autoflake --remove-all-unused-imports --in-place --recursive src
uv run black src
uv run routes_security_check

# Generate API changelog
uv run generate_changelog
```

### ML Engine

```bash
cd ml-engine

# Generate GenAI Engine client
cd scripts
./openapi_client_utils.sh generate python
./openapi_client_utils.sh install python
./install_db_dependencies.sh
cd ..

uv sync

# Run ML Engine
uv run python src/ml_engine/job_agent.py

# Testing
uv sync --group dev
uv run pytest tests/unit

# Code quality
uv run isort src/ml_engine --profile black --check
uv run black --check src/ml_engine
uv run mypy src/ml_engine
```

### Frontend UI

```bash
cd genai-engine/ui
yarn install
yarn dev              # Development at localhost:5173
yarn build           # Production build
yarn type-check      # TypeScript checking
yarn lint            # ESLint
yarn format          # Prettier (auto-fix)
yarn format:check    # Prettier (check only)
yarn generate-api    # Generate API client from OpenAPI spec

# Before committing (REQUIRED - CI enforced)
yarn check           # Runs type-check, lint, and format:check
```

### Docker Compose (Full Stack)

```bash
cd deployment/docker-compose/genai-engine
cp .env.template .env
# Edit .env with your configuration
docker compose up
# Access at http://localhost:3030/docs
```

## Architecture

### GenAI Engine Structure

```
src/
├── server.py              # FastAPI app initialization
├── dependencies.py        # Dependency injection (DB, auth, clients)
├── config/                # Configuration management
├── auth/                  # Authentication & OAuth (Keycloak, JWT)
├── db_models/             # SQLAlchemy models (19 entity types)
│   ├── task_models.py            # Task/use-case definitions
│   ├── rule_models.py            # Rule configurations
│   ├── rule_result_models.py     # Rule evaluation results
│   ├── inference_models.py       # Span/trace data storage
│   └── dataset_models.py         # Dataset management
├── repositories/          # Data access layer (24 repositories)
│   ├── tasks_repository.py
│   ├── rules_repository.py
│   ├── inference_repository.py
│   └── span_repository.py        # Trace data queries
├── routers/               # API route handlers
│   ├── v1/                # Legacy API endpoints
│   │   ├── trace_api_routes.py
│   │   ├── llm_eval_routes.py
│   │   └── rag_routes.py
│   └── v2/                # Current API version
│       ├── task_management_routes.py
│       ├── rule_management_routes.py
│       ├── validate_routes.py
│       └── feedback_routes.py
├── scorer/                # Evaluation engine
│   ├── scorer.py          # Main scorer orchestration
│   ├── llm_client.py      # OpenAI/Azure/LiteLLM integration
│   └── checks/            # Evaluation implementations
│       ├── hallucination/         # Claim-based LLM judge
│       ├── prompt_injection/      # DebertaV3 model
│       ├── toxicity/              # RoBERTa classifier
│       ├── pii/                   # Presidio + GLiNER
│       ├── sensitive_data/        # Few-shot LLM judge
│       └── regex/                 # Pattern-based checks
├── schemas/               # Pydantic request/response models
├── utils/                 # Utility modules
│   ├── model_load.py      # Download & cache models
│   └── classifiers.py     # GPU/device detection
└── validation/            # Input validation logic
```

### ML Engine Structure

```
src/ml_engine/
├── job_agent.py           # Main agent polling for jobs
├── job_runner.py          # Job execution orchestration
├── job_executor.py        # Individual job execution
├── dataset_loader.py      # Load data from various sources
├── connectors/            # Data source connectors
│   ├── bigquery/
│   ├── snowflake/
│   ├── postgres/
│   ├── mysql/
│   ├── s3/
│   └── gcs/
├── job_executors/         # Job type handlers
│   ├── backtest_executor.py
│   └── multi_model_eval_executor.py
└── metric_calculators/    # Metric computation
```

### Database Schema (Key Entities)

- **tasks** - Use cases/LLM applications
- **rules** - Evaluation rules configuration
- **rule_results** - Results of rule evaluations
- **spans/inferences** - Trace data (prompts, responses, metadata)
- **datasets** - User data for evaluations
- **feedback** - User feedback on evaluations
- **api_keys** - Authentication credentials
- **secrets** - Encrypted credential storage
- **metrics** - Calculated metrics per task

## Key Evaluation Types

The scorer system in [src/scorer/checks/](src/scorer/checks/) implements:

- **Hallucination Detection**: Claim-based LLM judge technique
- **Prompt Injection**: DebertaV3 model-based detection
- **Toxicity**: RoBERTa toxicity classifier
- **PII Detection**: Presidio + GLiNER for Named Entity Recognition
- **Sensitive Data**: Few-shot LLM judge
- **Regex Checks**: Pattern-based validation
- Custom rules support via extensible plugin system

## Frontend UI Guidelines (MANDATORY)

### Always Use MUI Components

**All frontend UI work MUST use Material UI (MUI) components.** Do NOT use plain HTML elements or custom-styled replacements when an MUI component exists. This applies to every new component, feature, and bugfix.

**Required:** Use MUI components from `@mui/material` for all UI elements:

| Instead of...            | Always use...                                       |
| ------------------------ | --------------------------------------------------- |
| `<button>`               | `<Button>` from `@mui/material`                     |
| `<input>`, `<textarea>`  | `<TextField>` from `@mui/material`                   |
| `<select>`               | `<Select>` or `<Autocomplete>` from `@mui/material` |
| `<table>`                | `<Table>` components or Material React Table         |
| `<div>` for layout       | `<Box>`, `<Stack>`, `<Paper>`, `<Card>`             |
| `<p>`, `<h1>`-`<h6>`     | `<Typography>` with appropriate `variant`           |
| `<a>`                    | `<Link>` from `@mui/material`                        |
| `<ul>/<li>` for menus    | `<List>`, `<ListItem>`, `<Menu>`, `<MenuItem>`      |
| `<dialog>`, custom modal | `<Dialog>` with `DialogTitle`, `DialogContent`, `DialogActions` |
| Custom alert/banner      | `<Alert>` from `@mui/material`                       |
| Custom tooltip           | `<Tooltip>` from `@mui/material`                     |
| Custom chip/badge        | `<Chip>`, `<Badge>` from `@mui/material`            |
| Custom icon              | Icons from `@mui/icons-material`                     |
| Custom date picker       | Components from `@mui/x-date-pickers`               |

### Styling Rules

1. **Use the MUI `sx` prop** as the primary styling method for MUI components. This is the established pattern across the codebase.
2. **Use MUI theme color tokens** — never use raw hex/rgb colors. Use semantic tokens:
   - `primary.main`, `primary.light`, `primary.dark`, `primary.50`
   - `secondary.main`, `secondary.light`, `secondary.dark`
   - `error.main`, `error.50`, `success.main`, `success.light`
   - `warning.main`, `info.main`
   - `text.primary`, `text.secondary`, `text.disabled`
   - `divider`, `action.hover`
3. **Tailwind CSS is only for supplementary layout utilities** (e.g., `min-h-screen`, `flex`, spacing). Never use Tailwind for colors, typography, or component styling that MUI handles.
4. **Use `styled()` from `@mui/material/styles`** only when creating reusable custom-styled components that need to extend MUI components.

### Component Patterns

- **Buttons**: Use `variant="contained"` for primary actions, `variant="outlined"` for secondary, `variant="text"` for tertiary.
- **Typography**: Use semantic variants — `h5`/`h6` for headings, `subtitle1`/`body1`/`body2` for body text, `caption` for helper text.
- **Text Fields**: Use `variant="filled"` as the default text field style.
- **Layout**: Use `<Stack>` for flex layouts, `<Box>` for general containers, `<Card>`/`<Paper>` for elevated surfaces.
- **Icons**: Always source from `@mui/icons-material`. Size with `sx={{ fontSize: N }}` and color with theme tokens.
- **Feedback**: Use `<Alert>` for inline messages, notistack's `enqueueSnackbar` for toast notifications, `<Tooltip>` for hover hints.

### What NOT to Do

- **Do NOT create custom-styled `<div>`, `<span>`, or `<button>` elements** when MUI provides an equivalent component.
- **Do NOT use inline CSS styles** (`style={{ }}`) — use the `sx` prop instead.
- **Do NOT use hardcoded color values** (`#ff0000`, `rgb(...)`) — use MUI theme tokens.
- **Do NOT use Tailwind for colors or typography** — those are handled by MUI's design system.
- **Do NOT introduce new UI libraries** that duplicate MUI functionality.

## Development Workflow

### GenAI Engine Development

```bash
# Initial setup
cd genai-engine
uv sync --group dev --group linters
uv run pre-commit install

# Start PostgreSQL
docker compose up

# Set environment variables (see README.md)
# Run development server
uv run serve

# Before committing
uv run pytest -m "unit_tests"
uv run black src
uv run isort src

# Database schema changes
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head

# API changes - generate changelog
uv run generate_changelog
```

### ML Engine Development

```bash
cd ml-engine

# Generate GenAI client
cd scripts
./openapi_client_utils.sh generate python
./openapi_client_utils.sh install python
cd ..

uv sync --group dev --group linters

# Set environment variables
export ARTHUR_API_HOST=https://platform.arthur.ai
export ARTHUR_CLIENT_SECRET=<secret>
export ARTHUR_CLIENT_ID=<id>

# Run
uv run python src/ml_engine/job_agent.py

# Before committing
uv run pytest tests/unit
uv run mypy src/ml_engine
uv run black --check src/ml_engine
```

### Frontend Development

```bash
cd genai-engine/ui
yarn install
yarn dev

# After OpenAPI spec changes
yarn generate-api

# Before committing (REQUIRED - CI enforced)
yarn check  # Runs type-check, lint, and format:check
```

## Testing

**GenAI Engine:**

- Unit tests: `uv run pytest -m "unit_tests"`
- Coverage requirement: >= 79%
- Integration tests: `./tests/test_remote.sh`
- Performance tests: Locust-based (see [locust/README.md](genai-engine/locust/README.md))

**ML Engine:**

- Unit tests: `uv run pytest tests/unit`
- Type checking: `uv run mypy src/ml_engine`

**Pre-commit Hooks:**

- Trailing whitespace & end-of-file fixes
- YAML validation
- isort (import sorting)
- autoflake (unused imports removal)
- black (code formatting)
- Routes security validation
- Unit tests execution

## Key Configuration

**Environment Variables (GenAI Engine):**

```bash
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=changeme_pg_password
POSTGRES_URL=localhost
POSTGRES_PORT=5432
POSTGRES_DB=arthur_genai_engine

# GenAI Engine
GENAI_ENGINE_ADMIN_KEY=<admin-key>
GENAI_ENGINE_SECRET_STORE_KEY=<encryption-key>
GENAI_ENGINE_ENVIRONMENT=local|staging|production
GENAI_ENGINE_ENABLE_PERSISTENCE=enabled|disabled
GENAI_ENGINE_OPENAI_PROVIDER=Azure|OpenAI
GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS=<json-config>

# Observability
NEWRELIC_LICENSE_KEY=<key>
OTEL_EXPORTER_OTLP_ENDPOINT=<endpoint>
```

**Environment Variables (ML Engine):**

```bash
ARTHUR_API_HOST=https://platform.arthur.ai
ARTHUR_CLIENT_ID=<client-id>
ARTHUR_CLIENT_SECRET=<client-secret>
GENAI_ENGINE_INTERNAL_API_KEY=<api-key>
```

## Deployment

- **Docker**: Multi-stage builds with CPU and GPU variants
- **Docker Compose**: Full stack deployment in [deployment/docker-compose/genai-engine/](deployment/docker-compose/genai-engine/)
- **Helm**: Kubernetes deployment charts
- **CloudFormation**: AWS ECS deployment templates
- **CI/CD**: GitHub Actions ([.github/workflows/arthur-engine-workflow.yml](.github/workflows/arthur-engine-workflow.yml))

## Key Branches

- `main` - Production releases
- `dev` - Development/staging
- Feature branches created from `dev`

## Important Notes

- GenAI Engine uses Python 3.12, ML Engine uses Python 3.13
- PostgreSQL with pgVector extension required for vector similarity
- Pre-commit hooks enforce code quality and run tests
- API changes require changelog generation via `uv run generate_changelog`
- Model files are downloaded and cached on first use
- GPU support optional but improves performance for model-based checks
- **Frontend: Always use MUI components** — never use plain HTML elements when MUI provides an equivalent. See "Frontend UI Guidelines" section above for full details.
