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

1. Generate and Install GenAI Client
```bash
cd scripts
./openapi_client_utils.sh generate python
./openapi_client_utils.sh install python
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

### Run the ML Engine

Use this command to start the app:

```bash
poetry run python src/ml_engine/job_agent.py
```

If the app has started successfully, can communicate with the control plane, and is polling for jobs,
the logs should look as follows:
```INFO:root:Checking for jobs...```

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

### Manual Oracle Installation

**Note:** Oracle Instant Client requires manual installation due to license restrictions and download limitations.

#### Prerequisites
- macOS Intel x86-64 or Apple Silicon (ARM64)
- Oracle account (free registration required)

#### Installation Steps

1. **Visit Oracle Downloads**
   - Go to: https://www.oracle.com/database/technologies/instant-client/macos-intel-x86-downloads.html
   - Sign in with your Oracle account (or create one for free)

2. **Accept License Agreement**
   - Review and accept the Oracle Technology Network License Agreement

3. **Download Oracle Instant Client**
   - Download "Basic Package" for your macOS architecture:
     - **Intel Macs**: `instantclient-basic-macos.x64-21.12.0.0.0.zip` (~100MB)
     - **Apple Silicon**: `instantclient-basic-macos.arm64-21.12.0.0.0.zip` (~100MB)
   - **Optional**: Download "SDK Package" if you need development headers

4. **Install Oracle Instant Client**
   ```bash
   # Create Oracle directory
   mkdir -p ~/oracle

   # Extract the downloaded ZIP file
   unzip instantclient-basic-macos.x64-21.12.0.0.0.zip -d ~/oracle/

   # Verify installation
   ls ~/oracle/
   # Should show: instantclient_21_12/
   ```

5. **Set Environment Variables**
   ```bash
   # Add to your shell profile (~/.zshrc or ~/.bash_profile)
   echo 'export ORACLE_HOME=~/oracle/instantclient_21_12' >> ~/.zshrc
   echo 'export DYLD_LIBRARY_PATH=~/oracle/instantclient_21_12:$DYLD_LIBRARY_PATH' >> ~/.zshrc
   echo 'export PATH=~/oracle/instantclient_21_12:$PATH' >> ~/.zshrc

   # Reload your shell profile
   source ~/.zshrc
   ```

6. **Verify Installation**
   ```bash
   # Check if Oracle libraries are accessible
   ls $ORACLE_HOME
   # Should show: libclntsh.dylib, libociei.dylib, etc.
   ```

#### Troubleshooting

- **"Library not found" errors**: Ensure `DYLD_LIBRARY_PATH` is set correctly
- **Permission denied**: Check that the Oracle directory has proper read permissions
- **Python import errors**: Restart your Python environment after setting environment variables

#### Alternative: Homebrew (Limited Support)
Some users report success with:
```bash
brew install --cask oracle-instantclient
```
However, this method may not work consistently across all macOS versions.

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

## Running the ML Engine Locally in terminal [Recommended for Dev Work Only]
You may want to run the ML engine in your terminal instead of in a Docker container.

The most likely reason you're doing this is because you are a dev who wants to install a local version of the
arthur-client generated based on changes that haven't been released yet:

1. From the ml-engine directory, [set up your Python environment](#set-up-python-environment). All Python environment set ups
   MUST happen before step 3 (particularly `poetry install`) or the local version of the arthur-client that you install
   will get overwritten by the project dependency installation.
2. From the `arthur-scope` repository, run the OpenAPI Client generation & install steps in the [root README](https://gitlab.com/ArthurAI/arthur-scope#generate-client).
3. Run `./scripts/install_local_scope_packages.sh`. If you did not clone arthur-scope into your home directory, you
   will need to update the path referenced in the script that installs the client. Assuming you completed step 2 and
   your paths are set as expected, this will install your local version of the arthur client.
4. Follow the [Setup environment](#setup-environment) and [Run the ML Engine](#run-the-ml-engine) steps to finish
   running the ML engine locally. If you're running the arthur-scope stack locally, make sure you configure the
   environment variables to point to your local stack. This will require using `export ARTHUR_API_HOST="http://localhost:8000"`
   as well as setting the client secret.


## Common Issues
1. The version of arthur-client that you need has been released, but the engine dependency has not yet been bumped:

New versions of arthur-client will be picked up by the ML engine via RenovateBot. You may be developing against a version
of arthur-client that is newly released & hasn't been picked up yet. In that case, either look for a new RenovateBot PR,
or look here to update `pyproject.toml` to the latest version: https://pypi.org/project/arthur-client/
