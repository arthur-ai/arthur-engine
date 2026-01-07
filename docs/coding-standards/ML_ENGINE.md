# ML Engine - Coding Standards

This document defines the coding standards and patterns for the ML Engine Python application (job processing engine).

## Technology Stack

- **Python** 3.13
- **Poetry** for dependency management
- **simple-settings** for configuration
- **Pandas** for data processing
- **Connectors** for BigQuery, Snowflake, S3, GCS, etc.

---

## Code Formatting & Linting

### Tools

| Tool | Purpose | Config |
|------|---------|--------|
| **Black** | Code formatting | `target-version = ["py313"]` |
| **isort** | Import sorting | `profile = "black"` |
| **MyPy** | Type checking | `strict = true` |

### Pre-Commit Workflow

```bash
poetry run isort src/ml_engine --profile black --check
poetry run black --check src/ml_engine
poetry run mypy src/ml_engine
```

---

## Project Structure

```
src/ml_engine/
├── job_agent.py           # Main agent polling for jobs
├── job_runner.py          # Job execution orchestration
├── job_executor.py        # Individual job execution
├── dataset_loader.py      # Data loading abstraction
├── config/                # Configuration management
│   └── config.py
├── connectors/            # Data source connectors
│   ├── connector.py       # Abstract base class
│   ├── bigquery/
│   ├── snowflake/
│   ├── postgres/
│   ├── mysql/
│   ├── s3/
│   └── gcs/
├── job_executors/         # Job type handlers
│   ├── backtest_executor.py
│   └── multi_model_eval_executor.py
├── metric_calculators/    # Metric computation
├── tools/                 # Utility tools
└── health_check/          # Health monitoring
```

---

## Naming Conventions

### Files

- Lowercase with underscores: `job_agent.py`, `dataset_loader.py`
- Connector directories: lowercase (e.g., `bigquery/`, `snowflake/`)

### Classes

| Type | Convention | Example |
|------|------------|---------|
| Executors | `{Type}Executor` | `MetricsCalculationExecutor` |
| Connectors | `{Source}Connector` | `S3Connector`, `BigQueryConnector` |
| Data classes | PascalCase | `RunningJob`, `JobRun` |

### Functions & Methods

- snake_case: `get_job()`, `run_job()`, `calculate_metrics()`
- Private: prefix with `_`: `_signal_handler()`, `_extract_config()`

### Constants

- UPPER_SNAKE_CASE: `MAX_CONCURRENT_JOBS`, `DEFAULT_TIMEOUT`

---

## Type Annotations

### Required Everywhere

```python
def allocated_memory_mb(self) -> int:
    pass

def run_job(
    self,
    job: Job,
    timeout: int = 3600,
) -> JobResult | None:
    pass
```

### Union Types

Use Python 3.10+ syntax:

```python
# GOOD
runner: JobRunner | None = None
dataset: Dataset | AvailableDataset

# AVOID
from typing import Optional, Union
runner: Optional[JobRunner] = None
```

### Generic Types

```python
def read(self) -> list[dict[str, Any]] | pd.DataFrame:
    pass
```

---

## Dataclasses

Use dataclasses for data containers:

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class RunningJob:
    job_id: str
    runner: JobRunner
    memory_requirements: int
    job_run: JobRun

@dataclass
class ConnectorConfig:
    endpoint: Optional[str] = None
    region: Optional[str] = None
    access_key_id: Optional[str] = None
    duration_seconds: int = 3600
```

### Private Dataclasses

Prefix with `_` for internal use:

```python
@dataclass
class _S3ConnectorConfigFields:
    endpoint: Optional[str]
    region: Optional[str]
```

---

## Abstract Base Classes

### Connector Interface

```python
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import pandas as pd

class Connector(ABC):
    @abstractmethod
    def __init__(
        self,
        connector_config: ConnectorSpec,
        logger: Logger,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def read(
        self,
        dataset: Dataset | AvailableDataset,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]] | pd.DataFrame:
        raise NotImplementedError
```

### Concrete Implementation

```python
class S3Connector(BucketBasedConnector):
    def __init__(
        self,
        connector_config: ConnectorSpec,
        logger: Logger,
    ) -> None:
        self.fs = self._construct_s3fs_with_auth(connector_config)
        super().__init__(logger, connector_config)

    def read(
        self,
        dataset: Dataset | AvailableDataset,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]] | pd.DataFrame:
        # Implementation
        pass
```

---

## Pattern Matching

Use `match` statements for control flow:

```python
match job.kind:
    case JobKind.METRICS_CALCULATION:
        executor = MetricsCalculationExecutor(config)
    case JobKind.CONNECTOR_TEST:
        executor = ConnectorTestExecutor(config)
    case JobKind.BACKTEST:
        executor = BacktestExecutor(config)
    case _:
        raise ValueError(f"Unknown job kind: {job.kind}")
```

### Signal Handling

```python
def _signal_handler(self, signum: int, _: FrameType | None) -> None:
    match signum:
        case signal.SIGTERM:
            logger.info("Received SIGTERM, initiating graceful shutdown...")
            self.shutting_down = True
        case signal.SIGINT:
            logger.info("Received SIGINT, initiating graceful shutdown...")
            self.shutting_down = True
        case _:
            logger.warning(f"Received unexpected signal {signum}")
```

---

## Configuration Management

### Using simple-settings

```python
from simple_settings import LazySettings

settings = LazySettings(
    f"{directory}/settings.yaml",
    ".environ",  # Environment overrides
)

class Config:
    settings = settings

    @classmethod
    def get_bool(cls, key: str, default: bool = False) -> bool:
        settings_dict = cls.settings.as_dict()
        value = settings_dict.get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return default

    @classmethod
    def get_int(cls, key: str, default: int = 0) -> int:
        value = cls.settings.as_dict().get(key, default)
        return int(value)

    @classmethod
    def get_str(cls, key: str, default: str = "") -> str:
        return cls.settings.as_dict().get(key, default)
```

### YAML Configuration

```yaml
# settings.yaml
max_concurrent_jobs: 5
polling_interval_seconds: 10
job_timeout_seconds: 3600
```

---

## Signal Handling & Lifecycle

### Graceful Shutdown

```python
import signal
from types import FrameType

class JobAgent:
    def __init__(self) -> None:
        self.shutting_down = False
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum: int, _: FrameType | None) -> None:
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.shutting_down = True

    def run(self) -> None:
        while not self.shutting_down:
            self._poll_for_jobs()
            time.sleep(self.polling_interval)

        self._cleanup()
```

---

## Async Patterns

Use asyncio for specific I/O operations:

```python
import asyncio

# AWS role assumption
session = asyncio.run(
    assume_role(
        session=base_session,
        role_arn=role_arn,
        duration=duration_seconds,
    )
)
```

---

## Context Managers

### Job Logging Context

```python
from contextlib import contextmanager

@contextmanager
def job_logging_context(job_id: str, logger: Logger):
    logger.info(f"Starting job {job_id}")
    try:
        yield
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        raise
    finally:
        logger.info(f"Job {job_id} completed")

# Usage
with job_logging_context(job.id, self.logger):
    executor.run(job)
```

### Export Context

```python
with ExportContextedLogger(self.logger, scope_export_handler):
    self.logger.info(f"Starting job {job.id}")
    # Logs are automatically exported
```

---

## Logging

### Per-Job Logger

```python
import logging
from uuid import uuid4

class JobRunner:
    def __init__(self, job: Job) -> None:
        self.logger = logging.getLogger(str(uuid4()))
        self.logger.setLevel(logging.INFO)

    def run(self) -> None:
        self.logger.info(f"Running job {self.job.id}")
```

### Structured Logging

```python
logger.info(f"Total memory MB: {self.total_memory_mb}")
logger.error(f"Failed to set job state: {str(e)}")
logger.warning(f"Job {job_id} did not complete in time")
```

---

## Error Handling

### Custom Exceptions

```python
class InvalidConnectorException(Exception):
    """Raised when connector configuration is invalid."""
    pass

class JobExecutionException(Exception):
    """Raised when job execution fails."""
    def __init__(self, job_id: str, reason: str) -> None:
        self.job_id = job_id
        self.reason = reason
        super().__init__(f"Job {job_id} failed: {reason}")
```

### Try-Except Patterns

```python
try:
    self.jobs_client.put_job_state(job_id, JobState.RUNNING)
except ApiException as e:
    logger.error(f"Failed to set job state: {str(e)}")
    # Continue or raise based on severity
```

### Recoverable vs Fatal Errors

```python
def run_job(self, job: Job) -> JobResult:
    try:
        return self._execute_job(job)
    except RecoverableError as e:
        # Log and retry
        logger.warning(f"Recoverable error: {e}, retrying...")
        return self._retry_job(job)
    except FatalError as e:
        # Log and fail
        logger.error(f"Fatal error: {e}")
        raise JobExecutionException(job.id, str(e))
```

---

## Testing

### Test Structure

```
tests/
├── unit/
│   ├── test_connectors/
│   ├── test_executors/
│   └── test_job_agent.py
└── integration/
```

### Fixtures

```python
import pytest

@pytest.fixture()
def test_user() -> User:
    return random_dataplane_user()

@pytest.fixture
def mock_bigquery_client():
    with patch("google.cloud.bigquery.Client") as mock_client:
        yield mock_client.return_value
```

### Parameterized Tests

```python
@pytest.mark.parametrize(
    "dataset_spec,expected_rows,should_error",
    [
        (valid_spec, 20, False),
        (invalid_spec, 0, True),
        (empty_spec, 0, False),
    ],
)
def test_s3_connector(
    dataset_spec: DatasetSpec,
    expected_rows: int,
    should_error: bool,
):
    if should_error:
        with pytest.raises(InvalidConnectorException):
            connector.read(dataset_spec)
    else:
        result = connector.read(dataset_spec)
        assert len(result) == expected_rows
```

---

## Import Organization

```python
# 1. Standard library
import asyncio
import logging
import signal
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Generator

# 2. Third-party
import pandas as pd
from simple_settings import LazySettings

# 3. Local imports
from config import Config
from connectors.connector import Connector
from job_executors.base_executor import BaseExecutor
```

---

## Dependency Injection

### Constructor Injection

```python
class DatasetLoader:
    def __init__(
        self,
        connector_constructor: ConnectorConstructor,
        datasets_client: DatasetsV1Api,
        logger: Logger,
    ) -> None:
        self.connector_constructor = connector_constructor
        self.datasets_client = datasets_client
        self.logger = logger

    def load(self, dataset_spec: DatasetSpec) -> pd.DataFrame:
        connector = self.connector_constructor(dataset_spec.connector_config)
        return connector.read(dataset_spec)
```

### Factory Pattern

```python
class ConnectorFactory:
    @staticmethod
    def create(
        connector_type: ConnectorType,
        config: ConnectorConfig,
        logger: Logger,
    ) -> Connector:
        match connector_type:
            case ConnectorType.S3:
                return S3Connector(config, logger)
            case ConnectorType.BIGQUERY:
                return BigQueryConnector(config, logger)
            case _:
                raise InvalidConnectorException(f"Unknown type: {connector_type}")
```

---

## Memory Management

### Tracking Allocation

```python
class JobAgent:
    def __init__(self) -> None:
        self.total_memory_mb = self._get_total_memory()
        self.running_jobs: list[RunningJob] = []

    def allocated_memory_mb(self) -> int:
        return sum(job.memory_requirements for job in self.running_jobs)

    def available_memory_mb(self) -> int:
        return self.total_memory_mb - self.allocated_memory_mb()

    def can_run_job(self, job: Job) -> bool:
        return job.memory_requirements <= self.available_memory_mb()
```

---

## API Client Usage

### Generated Client

```python
from arthur_api_client import JobsV1Api, DatasetsV1Api

class JobAgent:
    def __init__(self) -> None:
        self.jobs_client = JobsV1Api()
        self.datasets_client = DatasetsV1Api()

    def poll_for_jobs(self) -> list[Job]:
        try:
            return self.jobs_client.list_pending_jobs()
        except ApiException as e:
            logger.error(f"Failed to poll jobs: {e}")
            return []
```

---

## Key Differences from GenAI Engine

| Aspect | ML Engine | GenAI Engine |
|--------|-----------|--------------|
| **Python Version** | 3.13 | 3.12 |
| **Paradigm** | Job-driven, imperative | API-driven, service-oriented |
| **Configuration** | YAML + env overrides | Environment variables |
| **Database Access** | Direct (no abstraction) | Repository pattern |
| **API** | None (consumer only) | FastAPI REST API |
| **Async** | asyncio for specific tasks | FastAPI async throughout |
| **Data Classes** | Heavily used | Pydantic preferred |

---

## Best Practices

1. **Type Safety**: All functions must have type annotations
2. **Error Handling**: Distinguish recoverable from fatal errors
3. **Logging**: Use structured logging with job context
4. **Memory**: Track and respect memory limits
5. **Graceful Shutdown**: Handle SIGTERM/SIGINT properly
6. **Testing**: Use pytest fixtures and parameterized tests
7. **Configuration**: Use Config class methods, not direct settings access
