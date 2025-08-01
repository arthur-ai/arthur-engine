# ML Engine

- [ML Engine](#ml-engine)
  - [Developer Setup (for Mac)](#developer-setup-for-mac)
    - [Install prerequisite](#install-prerequisite)
    - [Set Up Python Environment](#set-up-python-environment)
  - [Running the ML Engine](#running-the-ml-engine)
    - [Setup environment](#setup-environment)
    - [Running the linter](#running-the-linter)
    - [Run Tests](#run-tests)
  - [Database Dependencies](#database-dependencies)
    - [Automatic Installation](#automatic-installation)
  - [Using local Docker image](#using-local-docker-image)


## Developer Setup (for Mac)

### Install prerequisite
1. Install Poetry
```bash
pip install "poetry>=2,<3"
```

### Set Up Python Environment

1. Generate GenAI Client
```bash
cd scripts
./openapi_client_utils.sh generate python
```

2. Install system dependencies for database drivers (optional)
```bash
# Make the script executable
chmod +x install_db_dependencies.sh

# Run the installation script
./install_db_dependencies.sh
```

This script installs system dependencies for:
- **psycopg** (PostgreSQL) - PostgreSQL client libraries
- **cx-oracle** (Oracle) - Oracle Instant Client
- **pymysql** (MySQL) - MySQL client libraries
- **pyodbc** (ODBC) - ODBC driver manager

The script supports:
- **Linux (Debian/Ubuntu)** - Uses `apt-get`
- **Linux (RHEL/CentOS/Fedora)** - Uses `yum`
- **macOS** - Uses Homebrew

**Note:** This script is designed for local development installations. For Docker deployments, the database dependencies are automatically installed during the Docker build process.

3. Install Python dependencies
```bash
poetry install
```

## Running the ML Engine

These steps assume that you already login and added Engine on [Arthur Platform](https://platform.arthur.ai/)

### Setup environment

```bash
export ARTHUR_API_HOST=https://platform.arthur.ai
export ARTHUR_CLIENT_SECRET=<value given when engine is registered>
export ARTHUR_CLIENT_ID=<value given when engine is registered>
```

You should see the following output when the app is running:

```bash
poetry run python src/ml_engine/job_agent.py
```

### Running the linter

1. Install pre-commits, it will automatically run linters for you before you commit
2. [Optional] You can manually trigger the linters
```bash
poetry install --with linters
poetry run autoflake --remove-all-unused-imports --in-place --recursive src/ml_engine
poetry run isort src/ml_engine --profile black
poetry run black src/ml_engine
poetry run mypy src
```

Fix any mypy errors that come up to get your MR pipeline to pass and commit any linter changes.

### Run Tests

```bash
poetry install --with dev
poetry run pytest tests/
```

## Database Dependencies

The ML Engine supports multiple database connectors through the following Python packages:
- **psycopg** (PostgreSQL)
- **cx-oracle** (Oracle)
- **pymysql** (MySQL)
- **pyodbc** (ODBC)

### Automatic Installation

Use the provided script to install all required system dependencies:

```bash
# Make executable and run
chmod +x install_db_dependencies.sh
./install_db_dependencies.sh
```

**For Docker builds**, a simplified version is used automatically in the Dockerfile:
- `install_db_dependencies_docker.sh` - Optimized for Debian/Ubuntu containers
- No manual intervention needed - dependencies are installed during image build

## Using local Docker image
1. Generate GenAI Client
```bash
cd scripts
./openapi_client_utils.sh generate python
```
2. Build image
```bash
docker build . -t ml-engine:local
```
3. Run docker image
```bash
docker run -e ARTHUR_API_HOST=https://platform.arthur.ai -e ARTHUR_CLIENT_SECRET=<value given when engine is registered> -e ARTHUR_CLIENT_ID=<value given when engine is registered> -it ml-engine:local
```
