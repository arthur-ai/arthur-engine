# GenAI Engine Backend - Coding Standards

This document defines the coding standards and patterns for the GenAI Engine Python backend (FastAPI).

## Technology Stack

- **Python** 3.12
- **FastAPI** for REST API
- **SQLAlchemy** for ORM
- **Pydantic** v2 for validation
- **PostgreSQL** with pgVector
- **Alembic** for migrations
- **Poetry** for dependency management

---

## Code Formatting & Linting

### Tools

| Tool | Purpose | Config |
|------|---------|--------|
| **Black** | Code formatting | `target-version = ["py312"]` |
| **isort** | Import sorting | `profile = "black"` |
| **autoflake** | Remove unused imports | `--remove-all-unused-imports` |
| **MyPy** | Type checking | `strict = true` |

### Pre-Commit Workflow

```bash
poetry run isort src --profile black
poetry run autoflake --remove-all-unused-imports --in-place --recursive src
poetry run black src
poetry run mypy src
```

### MyPy Configuration

```toml
[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true
implicit_reexport = true
mypy_path = "src"
```

---

## Project Structure

```
src/
├── server.py              # FastAPI app initialization
├── dependencies.py        # Dependency injection (singletons, DI)
├── config/                # Configuration management
├── auth/                  # Authentication & authorization
├── routers/               # API route handlers
│   ├── v1/               # Legacy API (deprecated)
│   └── v2/               # Current API version
├── repositories/          # Data access layer
├── db_models/             # SQLAlchemy ORM models
├── schemas/               # Pydantic models
│   ├── request_schemas.py
│   ├── response_schemas.py
│   ├── internal_schemas.py
│   └── enums.py
├── scorer/                # Evaluation engine
│   └── checks/           # Evaluation implementations
├── services/              # Business logic
├── clients/               # External service integrations
├── utils/                 # Utility modules
└── validation/            # Input validation logic
```

---

## Naming Conventions

### Files

- Lowercase with underscores: `api_key_repository.py`
- Suffixes indicate type:
  - `*_repository.py` - Data access
  - `*_routes.py` - API endpoints
  - `*_schemas.py` - Pydantic models
  - `*_models.py` - Database models

### Classes

| Type | Convention | Example |
|------|------------|---------|
| Database models | `Database{Entity}` | `DatabaseTask`, `DatabaseSpan` |
| Repositories | `{Entity}Repository` | `TaskRepository` |
| Services | `{Name}Service` | `TraceIngestionService` |
| Exceptions | `{Condition}Exception` | `BadCredentialsException` |
| Pydantic schemas | `{Entity}Request/Response` | `TaskResponse` |

### Functions & Methods

- snake_case: `get_task_by_id()`, `query_tasks()`
- Private methods: prefix with `_`: `_validate_input()`
- Query methods: `query_{entity}()`, `get_{entity}_by_id()`

### Constants

- UPPER_SNAKE_CASE: `GENAI_ENGINE_ADMIN_KEY_ENV_VAR`
- Module-level only

---

## Type Annotations

### Required Everywhere

```python
def get_task_by_id(
    self,
    task_id: str,
    include_rules: bool = False,
) -> Task | None:
    pass

def query_tasks(
    self,
    ids: list[str] | None = None,
    page_size: int = 10,
) -> tuple[list[DatabaseTask], int]:
    pass
```

### Union Types

Use Python 3.10+ syntax:

```python
# GOOD
def process(data: str | None) -> Task | None:
    pass

# AVOID (older style)
from typing import Optional, Union
def process(data: Optional[str]) -> Union[Task, None]:
    pass
```

### Generic Types

Use lowercase built-in generics:

```python
# GOOD
def get_items() -> list[dict[str, Any]]:
    pass

# AVOID
from typing import List, Dict
def get_items() -> List[Dict[str, Any]]:
    pass
```

---

## API Router Patterns

### Route Definition

```python
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/api/v2/tasks",
    tags=["Tasks"],
)

@router.get(
    "/{task_id}",
    description="Get task by ID",
    response_model=TaskResponse,
)
@permission_checker(permissions=PermissionLevelsEnum.READ.value)
def get_task(
    task_id: UUID = Path(description="The task ID"),
    include_rules: bool = Query(default=False, description="Include rules"),
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

### Error Handling in Routes

Always use try/finally for session cleanup:

```python
@router.post("/")
def create_resource(
    request: CreateRequest,
    db_session: Session = Depends(get_db_session),
) -> Response:
    try:
        repo = Repository(db_session)
        result = repo.create(request)
        return result
    finally:
        db_session.close()
```

---

## Repository Pattern

### Structure

```python
from sqlalchemy.orm import Session
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

class TaskRepository:
    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session

    @tracer.start_as_current_span("query_tasks")
    def query_tasks(
        self,
        ids: list[str] | None = None,
        name: str | None = None,
        page: int = 0,
        page_size: int = 10,
    ) -> tuple[list[DatabaseTask], int]:
        stmt = self.db_session.query(DatabaseTask)

        if ids:
            stmt = stmt.where(DatabaseTask.id.in_(ids))
        if name:
            stmt = stmt.where(DatabaseTask.name.ilike(f"%{name}%"))

        count = stmt.count()
        results = stmt.offset(page * page_size).limit(page_size).all()

        return results, count

    def get_task_by_id(self, task_id: str) -> Task | None:
        db_task = self.db_session.query(DatabaseTask).filter(
            DatabaseTask.id == task_id
        ).first()

        if not db_task:
            return None

        return Task._from_database_model(db_task)
```

### Return Patterns

- Single entity: Return `Entity | None`
- List with pagination: Return `tuple[list[Entity], int]` (results + total count)
- Always convert DB models to internal schemas

---

## Pydantic Schemas

### Request Schema

```python
from pydantic import BaseModel, Field, model_validator

class CreateTaskRequest(BaseModel):
    """Request to create a new task."""

    name: str = Field(
        description="Name of the task",
        min_length=1,
        max_length=100,
    )
    description: str | None = Field(
        default=None,
        description="Optional description",
        max_length=500,
    )
    is_agentic: bool = Field(
        default=False,
        description="Whether this is an agentic task",
    )

    @model_validator(mode="before")
    @classmethod
    def strip_name(cls, values: dict) -> dict:
        if "name" in values and values["name"]:
            values["name"] = values["name"].strip()
        return values
```

### Response Schema

```python
class TaskResponse(BaseModel):
    """Task response model."""

    id: str = Field(description="Unique task ID")
    name: str = Field(description="Task name")
    created_at: datetime = Field(description="Creation timestamp")
    rules_count: int = Field(default=0, description="Number of rules")

    model_config = {"from_attributes": True}
```

### Internal Schema

```python
class Task(BaseModel):
    """Internal task representation."""

    id: str
    name: str
    created_at: datetime

    @classmethod
    def _from_database_model(cls, db_model: DatabaseTask) -> "Task":
        return cls(
            id=str(db_model.id),
            name=db_model.name,
            created_at=db_model.created_at,
        )

    def to_response_model(self) -> TaskResponse:
        return TaskResponse(
            id=self.id,
            name=self.name,
            created_at=self.created_at,
        )
```

---

## Dependency Injection

### FastAPI Depends()

```python
from fastapi import Depends

def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def get_scorer_client() -> ScorerClient:
    global SINGLETON_SCORER_CLIENT
    if SINGLETON_SCORER_CLIENT is None:
        SINGLETON_SCORER_CLIENT = ScorerClient()
    return SINGLETON_SCORER_CLIENT

@router.get("/")
def endpoint(
    db_session: Session = Depends(get_db_session),
    scorer: ScorerClient = Depends(get_scorer_client),
):
    pass
```

### Singleton Pattern

For expensive resources:

```python
# dependencies.py
SINGLETON_DB_ENGINE: Engine | None = None
SINGLETON_SCORER_CLIENT: ScorerClient | None = None

def get_db_engine() -> Engine:
    global SINGLETON_DB_ENGINE
    if SINGLETON_DB_ENGINE is None:
        SINGLETON_DB_ENGINE = create_engine(Config.database_url())
    return SINGLETON_DB_ENGINE
```

---

## Exception Handling

### Custom Exceptions

```python
from fastapi import HTTPException

class GenaiEngineException(Exception):
    """Base exception for GenAI Engine."""
    pass

class BadCredentialsException(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=401, detail="Invalid credentials")

class PermissionDeniedException(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=403, detail="Permission denied")

class LLMExecutionException(GenaiEngineException):
    """LLM execution failed."""
    pass
```

### Error Response Pattern

```python
@router.get("/{id}")
def get_resource(id: UUID) -> Response:
    resource = repo.get_by_id(str(id))
    if not resource:
        raise HTTPException(
            status_code=404,
            detail=f"Resource {id} not found"
        )
    return resource
```

---

## Configuration Management

### Pattern

```python
from utils.utils import get_env_var
import constants

class Config:
    @classmethod
    def database_url(cls) -> str:
        return get_env_var(constants.DATABASE_URL_ENV_VAR, required=True)

    @classmethod
    def max_page_size(cls) -> int:
        value = get_env_var(constants.MAX_PAGE_SIZE_ENV_VAR, default="100")
        return int(value)

    @classmethod
    def is_production(cls) -> bool:
        env = get_env_var(constants.ENVIRONMENT_ENV_VAR, default="local")
        return env == "production"
```

### Usage

```python
from config import Config

page_size = min(requested_size, Config.max_page_size())
```

---

## OpenTelemetry Tracing

Add spans to significant operations:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

class TaskRepository:
    @tracer.start_as_current_span("query_tasks")
    def query_tasks(self, ...) -> tuple[list[DatabaseTask], int]:
        # Automatically traced
        pass

    @tracer.start_as_current_span("create_task")
    def create_task(self, ...) -> Task:
        pass
```

---

## Testing

### Test Structure

```
tests/
├── conftest.py          # Shared fixtures
├── unit/
│   ├── test_repositories/
│   ├── test_routers/
│   └── test_services/
└── integration/
    └── test_api/
```

### Fixtures

```python
import pytest
from sqlalchemy.orm import Session

@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

@pytest.fixture(scope="function")
def test_task(db_session: Session) -> DatabaseTask:
    task = DatabaseTask(name="Test Task")
    db_session.add(task)
    db_session.commit()
    return task
```

### Test Markers

```python
@pytest.mark.unit_tests
def test_create_task():
    pass

@pytest.mark.integration_tests
def test_api_endpoint():
    pass
```

### Coverage Requirement

Minimum 79% coverage:

```bash
poetry run pytest -m "unit_tests" --cov=src --cov-fail-under=79
```

---

## Import Organization

Sorted by isort with black profile:

```python
# 1. Standard library
import logging
import uuid
from datetime import datetime
from typing import Any, Generator

# 2. Third-party
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# 3. Local imports
from config import Config
from db_models import DatabaseTask
from repositories.task_repository import TaskRepository
from schemas.response_schemas import TaskResponse
```

---

## Database Migrations

### Creating Migrations

```bash
# Auto-generate from model changes
poetry run alembic revision --autogenerate -m "add column to tasks"

# Apply migrations
poetry run alembic upgrade head

# Rollback
poetry run alembic downgrade -1
```

### Migration Best Practices

- Always review auto-generated migrations
- Include both upgrade and downgrade paths
- Test migrations on a copy of production data

---

## Logging

```python
import logging

logger = logging.getLogger(__name__)

class TaskRepository:
    def create_task(self, request: CreateTaskRequest) -> Task:
        logger.info(f"Creating task: {request.name}")
        try:
            # creation logic
            logger.debug(f"Task created with ID: {task.id}")
            return task
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            raise
```

---

## Async Patterns

### FastAPI Async Routes

```python
@router.get("/")
async def list_resources() -> list[Response]:
    # Use async for I/O-bound operations
    pass
```

### Database Sessions

For async database operations (if using async SQLAlchemy):

```python
from sqlalchemy.ext.asyncio import AsyncSession

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

---

## API Versioning

- `v1/` - Legacy endpoints (deprecated, maintain for backwards compatibility)
- `v2/` - Current API version (all new development)

New features should only be added to v2. Breaking changes require a new version.

---

## Security

### Input Validation

- Always use Pydantic models for request validation
- Validate path parameters with `Path()`
- Validate query parameters with `Query()`

### SQL Injection Prevention

- Never use string interpolation in queries
- Always use SQLAlchemy parameterized queries

```python
# GOOD
stmt = select(Task).where(Task.id == task_id)

# BAD
stmt = text(f"SELECT * FROM tasks WHERE id = '{task_id}'")
```

### Authentication

Use dependency injection for auth:

```python
@router.get("/")
@permission_checker(permissions=PermissionLevelsEnum.READ.value)
def protected_endpoint(
    current_user: User = Depends(validate_auth),
):
    pass
```
