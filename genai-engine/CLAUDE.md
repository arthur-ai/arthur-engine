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

---

## Coding Standards

### Code Formatting

| Tool | Purpose | Config |
|------|---------|--------|
| **Black** | Code formatting | `target-version = ["py312"]` |
| **isort** | Import sorting | `profile = "black"` |
| **autoflake** | Remove unused imports | `--remove-all-unused-imports` |
| **MyPy** | Type checking | `strict = true` |

Run before committing:
```bash
poetry run isort src --profile black
poetry run black src
poetry run mypy src
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Files | lowercase_underscore | `api_key_repository.py` |
| Database models | `Database{Entity}` | `DatabaseTask`, `DatabaseSpan` |
| Repositories | `{Entity}Repository` | `TaskRepository` |
| Services | `{Name}Service` | `TraceIngestionService` |
| Exceptions | `{Condition}Exception` | `BadCredentialsException` |
| Pydantic schemas | `{Entity}Request/Response` | `TaskResponse` |
| Functions | snake_case | `get_task_by_id()` |
| Private methods | `_` prefix | `_validate_input()` |
| Constants | UPPER_SNAKE_CASE | `MAX_PAGE_SIZE` |

### Type Annotations

Required on all functions. Use Python 3.10+ syntax:

```python
# GOOD - modern syntax
def get_task(task_id: str, include_rules: bool = False) -> Task | None:
    pass

def query_tasks(ids: list[str] | None = None) -> tuple[list[Task], int]:
    pass

# AVOID - older style
from typing import Optional, Union, List
def get_task(task_id: str) -> Optional[Task]:  # Use Task | None instead
    pass
```

### API Router Pattern

```python
@router.get("/{task_id}", response_model=TaskResponse)
@permission_checker(permissions=PermissionLevelsEnum.READ.value)
def get_task(
    task_id: UUID = Path(description="The task ID"),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> TaskResponse:
    try:
        repo = TaskRepository(db_session)
        task = repo.get_task_by_id(str(task_id))
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task.to_response_model()
    finally:
        db_session.close()
```

### Repository Pattern

All database access goes through repository classes:

```python
class TaskRepository:
    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session

    @tracer.start_as_current_span("query_tasks")
    def query_tasks(
        self,
        ids: list[str] | None = None,
        page: int = 0,
        page_size: int = 10,
    ) -> tuple[list[DatabaseTask], int]:
        stmt = self.db_session.query(DatabaseTask)
        if ids:
            stmt = stmt.where(DatabaseTask.id.in_(ids))
        count = stmt.count()
        results = stmt.offset(page * page_size).limit(page_size).all()
        return results, count
```

### Pydantic Schemas

Use Field descriptions for OpenAPI docs:

```python
class CreateTaskRequest(BaseModel):
    name: str = Field(description="Name of the task", min_length=1, max_length=100)
    description: str | None = Field(default=None, description="Optional description")

    @model_validator(mode="before")
    @classmethod
    def strip_name(cls, values: dict) -> dict:
        if "name" in values and values["name"]:
            values["name"] = values["name"].strip()
        return values
```

### Import Order

Sorted by isort with black profile:

```python
# 1. Standard library
import logging
from datetime import datetime
from typing import Any

# 2. Third-party
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# 3. Local imports
from config import Config
from repositories.task_repository import TaskRepository
```

### OpenTelemetry Tracing

Add spans to significant operations:

```python
from opentelemetry import trace
tracer = trace.get_tracer(__name__)

class TaskRepository:
    @tracer.start_as_current_span("query_tasks")
    def query_tasks(self, ...) -> tuple[list[DatabaseTask], int]:
        pass
```

### Error Handling

- Use HTTPException for API errors with appropriate status codes
- Always close database sessions in `finally` blocks
- Log errors before raising exceptions

### Testing Requirements

- Minimum 79% coverage: `poetry run pytest -m "unit_tests" --cov=src --cov-fail-under=79`
- Use pytest markers: `@pytest.mark.unit_tests`, `@pytest.mark.integration_tests`
- Fixtures should clean up after themselves
