# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## GenAI Engine

A FastAPI-based service for LLM evaluation, guardrails, and monitoring. Provides evaluations for hallucination, prompt injection, toxicity, PII detection, sensitive data, and more.

### Common Commands

```bash
# Install dependencies
poetry install

# Run development server
poetry run serve
# or: uvicorn src.server:get_app --reload

# Run tests (unit tests only)
poetry run pytest -m "unit_tests"

# Run tests with coverage (79% minimum required)
poetry run pytest -m "unit_tests" --cov=src --cov-fail-under=79

# Run integration tests
./tests/test_remote.sh

# Linting and formatting
poetry run black src/
poetry run isort src/
poetry run mypy src/

# Database migrations
poetry run alembic upgrade head
poetry run alembic revision --autogenerate -m "description"

# Generate changelog
poetry run generate_changelog

# Performance testing (requires separate install)
poetry install --only performance
# See locust/README.md for details
```

### Architecture

**Tech Stack**: Python 3.12, FastAPI, SQLAlchemy, PostgreSQL + pgvector, Alembic, Uvicorn

**Core Components**:

- **Routers** (`src/routers/`): API endpoints organized into v1 and v2, separated by feature (tasks, traces, prompts, datasets, rules, evaluators)
- **Scorer** (`src/scorer/`): Check implementations (hallucination, toxicity, PII, prompt injection, etc.) - each check is a pluggable scorer
- **Rules Engine** (`src/rules_engine/`): Orchestrates rule evaluation and validation logic
- **Metrics Engine** (`src/metrics_engine/`): Performance tracking and metrics calculation
- **Repositories** (`src/repositories/`): Data access layer following repository pattern
- **DB Models** (`src/db/models/`): SQLAlchemy ORM models
- **Clients** (`src/clients/`): External service integrations (S3, Azure, Keycloak, LLM providers)

**Key Patterns**:

- **Dependency Injection**: Uses FastAPI's `Depends()` system extensively for database sessions, authentication, and service injection
- **JWT Authentication**: API key-based authentication with JWT tokens
- **Repository Pattern**: All database access goes through repository classes, not direct ORM access
- **Rule-Based Evaluation**: Rules define conditions and actions, executed by the rules engine
- **OpenTelemetry**: Distributed tracing instrumentation throughout the codebase
- **Async-First**: Most operations use async/await for I/O operations

**Database**:

- PostgreSQL with pgvector extension for embeddings
- Alembic for schema migrations
- Connection pooling via SQLAlchemy
- Separate read/write connections supported

**Testing**:

- pytest markers: `unit_tests`, `integration_tests`, `aws_live`, `azure_live`
- Minimum coverage requirement: 79%
- Integration tests run against deployed environments via `test_remote.sh`
- Locust for performance testing

**External Integrations**:

- OpenAI/Azure OpenAI for LLM-based evaluations
- S3/Azure Blob Storage for file storage
- Weaviate for RAG retrievals (optional)
- Keycloak for OAuth (optional)

### Development Notes

- The API has two versions (v1, v2) with different authentication and feature sets
- Task-based validation: traces are validated against task rules
- Agentic workflow support: multi-step agent trace evaluation
- Pre-commit hooks enforce black, isort, mypy - see CONTRIBUTING.md
- Database migrations should be reviewed before applying to ensure idempotency
