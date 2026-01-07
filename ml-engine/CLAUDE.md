# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ML Engine

Job-based evaluation engine that executes dataset evaluations and metric calculations for the Arthur Platform. Polls for jobs, loads data from various sources (S3, GCS, BigQuery, Snowflake, databases), and computes ML metrics.

### Common Commands

```bash
# Install dependencies
poetry install

# Generate GenAI Engine client
cd scripts
./openapi_client_utils.sh generate python
./openapi_client_utils.sh install python

# Install database dependencies (ODBC, Oracle drivers)
./install_db_dependencies.sh

# Run ML Engine
poetry run python src/ml_engine/job_agent.py

# Linting
cd scripts
./lint.sh

# Tests
poetry run pytest tests/
```

### Architecture

**Tech Stack**: Python 3.13, Poetry, arthur-client, PostgreSQL/MySQL/Oracle/Snowflake/BigQuery connectors, Pandas, NumPy, PyArrow

**Job Processing Flow**:

```
JobAgent (polling) → JobRunner (threading/multiprocessing) → JobExecutor (execution logic) → Job-specific executors
```

**Core Components**:

- **job_agent.py**: Main entry point - polls Arthur Platform for jobs, manages health checks
- **job_runner.py**: Executes jobs using thread or process runners based on job type
- **job_executor.py**: Core job execution logic and orchestration
- **job_executors/**: Specific implementations for different job types
- **connectors/**: Abstracted data source access (S3, GCS, BigQuery, Snowflake, ODBC, PostgreSQL, MySQL, Oracle)
- **metric_calculators/**: ML metric computation logic
- **dataset_loader.py**: Loads and processes datasets from various sources
- **config/**: Configuration management and environment variables

**Key Patterns**:

- **Job Agent Pattern**: Continuously polls Arthur Platform API for new jobs to execute
- **Connector Pattern**: Each data source has a dedicated connector class with a common interface
- **Strategy Pattern**: Different job executor types handle different evaluation types
- **Health Check Pattern**: Exposes health endpoints for monitoring service availability
- **Generated Client**: Uses auto-generated Python client for GenAI Engine integration

**Data Source Support**:

- Cloud Storage: S3, Google Cloud Storage, Azure Blob Storage
- Databases: PostgreSQL, MySQL, Oracle, Snowflake, BigQuery, ODBC-compatible databases
- Local files for development/testing

**Integration Points**:

- **Arthur Platform**: Main control plane - provides jobs and receives results via arthur-client
- **GenAI Engine**: Optional integration for LLM evaluations via generated Python client
- **Databases**: Direct connections for loading training/inference data

**Configuration**:

- Environment variables control all external connections
- Supports multiple database connection strings
- Configurable job polling intervals and retry logic
- Health check endpoints for container orchestration

### Development Notes

- The GenAI Engine client (`scripts/openapi_client_utils.sh`) must be regenerated when the GenAI Engine API changes
- Database drivers (ODBC, Oracle Instant Client) are installed via `install_db_dependencies.sh` and included in the Docker image
- Job executors should be stateless and idempotent where possible
- The job agent uses long polling to minimize API load on the Arthur Platform
- Health checks should always respond quickly to avoid container restarts

---

## Coding Standards

### Code Formatting

| Tool | Purpose | Config |
|------|---------|--------|
| **Black** | Code formatting | `target-version = ["py313"]` |
| **isort** | Import sorting | `profile = "black"` |
| **MyPy** | Type checking | `strict = true` |

Run before committing:
```bash
cd scripts && ./lint.sh
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Files | lowercase_underscore | `job_agent.py` |
| Classes | PascalCase | `JobAgent`, `S3Connector` |
| Executors | `{Type}Executor` | `MetricsCalculationExecutor` |
| Connectors | `{Source}Connector` | `S3Connector`, `BigQueryConnector` |
| Functions | snake_case | `run_job()`, `calculate_metrics()` |
| Private | `_` prefix | `_signal_handler()`, `_extract_config()` |
| Constants | UPPER_SNAKE_CASE | `MAX_CONCURRENT_JOBS` |

### Type Annotations

Required on all functions. Use Python 3.10+ syntax:

```python
# GOOD - modern syntax
def run_job(self, job: Job, timeout: int = 3600) -> JobResult | None:
    pass

runner: JobRunner | None = None
dataset: Dataset | AvailableDataset

# AVOID - older style
from typing import Optional
runner: Optional[JobRunner] = None  # Use JobRunner | None
```

### Dataclasses

Use dataclasses for data containers:

```python
from dataclasses import dataclass

@dataclass
class RunningJob:
    job_id: str
    runner: JobRunner
    memory_requirements: int
    job_run: JobRun

@dataclass
class ConnectorConfig:
    endpoint: str | None = None
    region: str | None = None
    duration_seconds: int = 3600
```

### Abstract Base Classes

Define interfaces with ABC:

```python
from abc import ABC, abstractmethod

class Connector(ABC):
    @abstractmethod
    def __init__(self, config: ConnectorSpec, logger: Logger) -> None:
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

### Pattern Matching

Use `match` statements for control flow:

```python
match job.kind:
    case JobKind.METRICS_CALCULATION:
        executor = MetricsCalculationExecutor(config)
    case JobKind.CONNECTOR_TEST:
        executor = ConnectorTestExecutor(config)
    case _:
        raise ValueError(f"Unknown job kind: {job.kind}")
```

### Signal Handling

Handle graceful shutdown:

```python
import signal
from types import FrameType

class JobAgent:
    def __init__(self) -> None:
        self.shutting_down = False
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum: int, _: FrameType | None) -> None:
        match signum:
            case signal.SIGTERM | signal.SIGINT:
                self.logger.info("Initiating graceful shutdown...")
                self.shutting_down = True
```

### Configuration

Use Config class with classmethod accessors:

```python
from simple_settings import LazySettings

class Config:
    settings = LazySettings("settings.yaml", ".environ")

    @classmethod
    def get_bool(cls, key: str, default: bool = False) -> bool:
        value = cls.settings.as_dict().get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return default
```

### Import Order

```python
# 1. Standard library
import asyncio
import logging
import signal
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# 2. Third-party
import pandas as pd
from simple_settings import LazySettings

# 3. Local imports
from config import Config
from connectors.connector import Connector
```

### Logging

Use per-job loggers with UUID:

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

### Error Handling

Distinguish recoverable from fatal errors:

```python
class InvalidConnectorException(Exception):
    """Raised when connector configuration is invalid."""
    pass

# Usage
try:
    self.jobs_client.put_job_state(job_id, JobState.RUNNING)
except ApiException as e:
    logger.error(f"Failed to set job state: {str(e)}")
    # Continue or raise based on severity
```

### Context Managers

Use for resource cleanup:

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

### Testing

Use pytest fixtures and parameterized tests:

```python
import pytest

@pytest.fixture
def mock_bigquery_client():
    with patch("google.cloud.bigquery.Client") as mock:
        yield mock.return_value

@pytest.mark.parametrize(
    "dataset_spec,expected_rows,should_error",
    [(valid_spec, 20, False), (invalid_spec, 0, True)],
)
def test_connector(dataset_spec, expected_rows, should_error):
    if should_error:
        with pytest.raises(InvalidConnectorException):
            connector.read(dataset_spec)
    else:
        assert len(connector.read(dataset_spec)) == expected_rows
```
