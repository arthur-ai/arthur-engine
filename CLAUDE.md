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
- Tailwind CSS, TanStack Query/Table
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
poetry shell && poetry env use 3.12
poetry install --with dev,linters

# Start PostgreSQL (required)
docker compose up

# Database setup
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=changeme_pg_password
export POSTGRES_URL=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=arthur_genai_engine
export GENAI_ENGINE_SECRET_STORE_KEY="some_test_key"
poetry run alembic upgrade head

# Run development server
export PYTHONPATH="src:$PYTHONPATH"
poetry run serve
# Access at http://localhost:3030/docs

# Testing
poetry run pytest -m "unit_tests"
poetry run pytest -m "unit_tests" --cov=src --cov-fail-under=79
./tests/test_remote.sh  # Integration tests

# Database migrations
poetry run alembic revision --autogenerate -m "<message>"
poetry run alembic upgrade head

# Code quality
poetry run isort src --profile black
poetry run autoflake --remove-all-unused-imports --in-place --recursive src
poetry run black src
poetry run routes_security_check

# Generate API changelog
poetry run generate_changelog
```

### ML Engine

```bash
cd ml-engine
poetry env use 3.13

# Generate GenAI Engine client
cd scripts
./openapi_client_utils.sh generate python
./openapi_client_utils.sh install python
./install_db_dependencies.sh
cd ..

poetry install

# Run ML Engine
poetry run python src/ml_engine/job_agent.py

# Testing
poetry install --with dev
poetry run pytest tests/unit

# Code quality
poetry run isort src/ml_engine --profile black --check
poetry run black --check src/ml_engine
poetry run mypy src/ml_engine
```

### Frontend UI

```bash
cd genai-engine/ui
yarn install
yarn dev              # Development at localhost:5173
yarn build           # Production build
yarn type-check      # TypeScript checking
yarn lint            # ESLint
yarn format          # Prettier
yarn generate-api    # Generate API client from OpenAPI spec
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

## Development Workflow

### GenAI Engine Development

```bash
# Initial setup
cd genai-engine
poetry shell && poetry env use 3.12
poetry install --with dev,linters
poetry run pre-commit install

# Start PostgreSQL
docker compose up

# Set environment variables (see README.md)
# Run development server
poetry run serve

# Before committing
poetry run pytest -m "unit_tests"
poetry run black src
poetry run isort src

# Database schema changes
poetry run alembic revision --autogenerate -m "description"
poetry run alembic upgrade head

# API changes - generate changelog
poetry run generate_changelog
```

### ML Engine Development

```bash
cd ml-engine
poetry env use 3.13

# Generate GenAI client
cd scripts
./openapi_client_utils.sh generate python
./openapi_client_utils.sh install python
cd ..

poetry install --with dev,linters

# Set environment variables
export ARTHUR_API_HOST=https://platform.arthur.ai
export ARTHUR_CLIENT_SECRET=<secret>
export ARTHUR_CLIENT_ID=<id>

# Run
poetry run python src/ml_engine/job_agent.py

# Before committing
poetry run pytest tests/unit
poetry run mypy src/ml_engine
poetry run black --check src/ml_engine
```

### Frontend Development

```bash
cd genai-engine/ui
yarn install
yarn dev

# After OpenAPI spec changes
yarn generate-api

# Before committing
yarn type-check && yarn lint
```

## Testing

**GenAI Engine:**
- Unit tests: `poetry run pytest -m "unit_tests"`
- Coverage requirement: >= 79%
- Integration tests: `./tests/test_remote.sh`
- Performance tests: Locust-based (see [locust/README.md](genai-engine/locust/README.md))

**ML Engine:**
- Unit tests: `poetry run pytest tests/unit`
- Type checking: `poetry run mypy src/ml_engine`

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
- API changes require changelog generation via `poetry run generate_changelog`
- Model files are downloaded and cached on first use
- GPU support optional but improves performance for model-based checks
