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
