# GenAI Engine

The GenAI Engine (formerly known as Arthur Shield) is **a tool for evaluating and benchmarking large language models (LLMs) and generative AI workflows**. It allows users to measure and monitor response relevance, hallucination rates, token counts, latency, and more. The engine also provides a simple way to **add guardrails to your LLM applications and generative AI workflows**. It has configurable metrics for real-time detection of PII or Sensitive Data leakage, Hallucination, Prompt Injection attempts, Toxic language, and other quality metrics. Arthur Engine can prevent these risks from causing bad user experience in production and negatively impacting your organization's reputation.

## Table of Contents

- [GenAI Engine](#genai-engine)
  - [Table of Contents](#table-of-contents)
  - [Getting Started](#getting-started)
    - [Quickstart](#quickstart)
    - [Usage Examples](#usage-examples)
  - [Documentation](#documentation)
  - [⚠️ Important Note for Intel Users](#️-important-note-for-intel-users)
  - [Developer Setup (for Mac)](#developer-setup-for-mac)
    - [Install the Python dependencies with Poetry](#install-the-python-dependencies-with-poetry)
    - [Run Postgres](#run-postgres)
    - [Alembic](#alembic)
      - [Set up variables for Alembic](#set-up-variables-for-alembic)
      - [Populate the Database Schema with Alembic](#populate-the-database-schema-with-alembic)
      - [Autogenerate script with changes](#autogenerate-script-with-changes)
    - [Run the app with an IDE (Visual Studio Code / Cursor example)](#run-the-app-with-an-ide-visual-studio-code--cursor-example)
    - [Run the app via the terminal](#run-the-app-via-the-terminal)
  - [Making your first commit](#making-your-first-commit)
    - [The git pre-commit hooks](#the-git-pre-commit-hooks)
    - [Pytest](#pytest)
    - [Security check for endpoints](#security-check-for-endpoints)
  - [Unit Tests](#unit-tests)
  - [Integration Tests](#integration-tests)
  - [Performance Tests](#performance-tests)
  - [Generate Changelog](#generate-changelog)
  - [Generate a new Alembic Migration](#generate-a-new-alembic-migration)

## Getting Started

There are a several ways to run the GenAI Engine:

- [Docker Compose](docker-compose/README.md)
- [Cloudformation](cloudformation/README.md) for AWS deployment with Elastic Container Service (ECS)
- [Helm Chart](helm/README.md) for Kubernetes

Note: The GenAI Engine is currently limited to providing you with the guardrail features. The rest of the features are coming soon!

### Quickstart

1. Follow the [Docker Compose](../deployment/docker-compose/README.md) instructions to deploy the engine on your local machine
2. Once your `genai-engine` is up and running, navigate to its interactive API documentation at `/docs` via a browser
3. Create an API key by referring to [the API Authentication Guide](https://shield.docs.arthur.ai/docs/api-authentication-guide). Your admin key is the `GENAI_ENGINE_ADMIN_KEY` in the [docker-compose.yml](../deployment/docker-compose/genai-engine/docker-compose.yml) file. In the Docker Compose deployment, the admin key is also enabled to interact with all the API endpoints to quickly get started with exploring the capability.
4. Provide `/docs` the access to use the API endpoints by entering your new API key, via the "Authorize" button, located at the top right of the page
5. Create a new task (use case/LLM application) by expanding the `POST /api/v2/task` endpoint on the `/docs` page. Click on "Try it out", provide a task name, and click "Execute".
6. Configure evaluation rules in the newly created task with the `POST /api/v2/tasks/{task_id}/rules` endpoint
7. Run LLM prompt and generated response evaluations by using the "Task Based Validation" endpoints. For the response validation endpoint, "context" must be provided for the hallucination rule if it's enabled. Hallucinations are generated responses characterized as incorrect or unfaithful responses given a user input and source knowledge (context). The context is often the Retrieval-Augmented Generation(RAG) data from your LLM application.
8. Try the default rules, which are global rules that are automatically applied to every task

![Arthur GenAI Engine API](../docs/images/arthur-genai-api.png)

For more information, refer to the [User Guide](https://shield.docs.arthur.ai).

### Usage Examples

- [GenAI Engine client example notebooks](https://github.com/arthur-ai/example-shield-notebooks)
- [An example of protecting an Agentic Application with GenAI Engine](https://github.com/arthur-ai/shield-autogen-agent-demo)

## Documentation

- [User Guide](https://shield.docs.arthur.ai)
- API Documentation - (`/docs` on your GenAI Engine instance)

## ⚠️ Important Note for Intel Users

**If you're using an Intel-based Mac or Windows/Linux system, please do NOT attempt to run the GenAI Engine locally.** The current setup is optimized for Apple Silicon (M1/M2/M3) Macs and may not work properly on Intel systems.

**Instead, please use the Vagrant development environment:**

1. See the [VAGRANT_README.md](../VAGRANT_README.md) in the root directory for detailed setup instructions
2. The Vagrant environment provides a Linux VM with all necessary dependencies
3. All services will be accessible from your local browser via port forwarding

This ensures a consistent development experience across all platforms.

## Developer Setup (for Mac)

### Install the Python dependencies with Poetry

1. Git clone the repo
2. Install Poetry: Poetry is a Python dependency management framework. `pyproject.toml` is the descriptor.
   ```bash
   pip install poetry
   ```
3. Set the proper Python version: Currently developed and tested with `3.12.8`

   ```bash
   cd genai-engine

   poetry self add poetry-plugin-shell
   poetry shell && poetry env use 3.12
   ```

4. Install dependencies/packages
   ```bash
   poetry install
   ```
   To add (or upgrade) a dependency, use the following command:
   ```bash
   poetry add <package_name>==<package_version>
   ```
   To add (or upgrade) a dev dependency, use the following command:
   ```bash
   poetry add --group dev <package_name>==<package_version>
   ```

### Run Postgres

A Postgres database is required to run the GenAI Engine. The easiest way to get started is to run Postgres using Docker.

1. Install and run Docker for Mac
2. `cd` to the `genai-engine` folder
3. Run `docker compose up`
4. Login with `postgres/changeme_pg_password`

### Alembic
#### Set up variables for Alembic

Make sure the Poetry install is complete and you have a running Postgres instance first. After that setup the variables
(example contains default valuse)

Example:
```bash
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=changeme_pg_password
export POSTGRES_URL=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=arthur_genai_engine
export POSTGRES_USE_SSL=false
export PYTHONPATH="src:$PYTHONPATH"
export GENAI_ENGINE_SECRET_STORE_KEY=changeme_secret_store_key
```

#### Populate the Database Schema with Alembic
After setting up variables you could run a migration scripts. To do it go to `genai-engine` directory and execute following command:

```bash
poetry run alembic upgrade head
```

This command will apply newest migration scripts

#### Autogenerate script with changes
If you made some changes to DB models you should create migration script. You could use alembic to generate such script. If you create
a new file that contains DB changes import this file to [DB Modelse init file](src/db_models/__init__.py).

After that run following command:
```bash
poetry run alembic revision --autogenerate -m "<commit message>"
```

**Keep the message short, avoid special characters.**

### Run the app with an IDE (Visual Studio Code / Cursor example)

1. Install the IDE
2. Install the recommended extensions
   - Python
   - Docker
   - CloudFormation
   - Kubernetes
   - Markdown All in One
3. Open a new window and select the `genai-engine` folder
4. Find the path to the interpreter used by the Poetry environment
   ```bash
   poetry env info --path
   ```
5. Open a Python file (e.g. `src/server.py`) and make sure you have the Python interpreter looked up in the previous step selected
6. Create a new launch configuration: `Run` -> `Add Configurations` -> `Python Debugger` -> `Python File `. Add the below configuration and adjust the values according to your environment. Please reference the `.env` file.

   ```json
   {
     "name": "GenAI Engine",
     "type": "python",
     "request": "launch",
     "module": "uvicorn",
     "args": ["src.server:get_app", "--reload"],
     "jinja": true,
     "justMyCode": false,
     "env": {
       "PYTHONPATH": "src",

       "POSTGRES_USER": "postgres",
       "POSTGRES_PASSWORD": "changeme_pg_password",
       "POSTGRES_URL": "localhost",
       "POSTGRES_PORT": "5435",
       "POSTGRES_DB": "arthur_genai_engine",
       "POSTGRES_USE_SSL": "false",
       "GENAI_ENGINE_ENABLE_PERSISTENCE": "enabled",

       "GENAI_ENGINE_ENVIRONMENT": "local",
       "GENAI_ENGINE_ADMIN_KEY": "changeme123",
       "GENAI_ENGINE_INGRESS_URI": "http://localhost:3030",

       "GENAI_ENGINE_OPENAI_PROVIDER": "Azure",
       "GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS": "model_name::https://my_service.openai.azure.com/::my_api_key",
       "GENAI_ENGINE_SECRET_STORE_KEY": "some_test_key"
     }
   }
   ```

7. `Run` -> `Run Without Debugging` / `Start Debugging`
8. Open `http://localhost:3030/docs` in your web browser and start building!

### Run the app via the terminal

1. Load a dedicated Python environment with a compatible Python version (i.e. `3.12`)
2. [Install the Python dependencies with Poetry](#install-the-python-dependencies-with-poetry)
3. Set the following environment variables:

   ```
   export POSTGRES_USER=postgres
   export POSTGRES_PASSWORD=changeme_pg_password
   export POSTGRES_URL=localhost
   export POSTGRES_PORT=5432
   export POSTGRES_DB=arthur_genai_engine
   export POSTGRES_USE_SSL=false
   export GENAI_ENGINE_ENABLE_PERSISTENCE=enabled

   export GENAI_ENGINE_ENVIRONMENT=local
   export GENAI_ENGINE_ADMIN_KEY=changeme123
   export GENAI_ENGINE_INGRESS_URI=http://localhost:3030

   export GENAI_ENGINE_OPENAI_PROVIDER=Azure
   export OPENAI_API_VERSION=2023-07-01-preview
   export GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS=model_name::https://my_service.openai.azure.com/::my_api_key
   export GENAI_ENGINE_SECRET_STORE_KEY="some_test_key"
   ```

4. Run the server
   ```bash
   export PYTHONPATH="src:$PYTHONPATH"
   poetry run serve
   ```

## Making your first commit

### The git pre-commit hooks

Review the [CONTRIBUTE.MD](../CONTRIBUTING.md) document carefully.
Make sure the git pre-commit hooks are installed properly.

### Pytest

As part of the pre-commit hook, Pytest unit tests are executed.
You can disable it with following command when making a commit that's not ready for testing:

```bash
SKIP=genai-engine-pytest-check git commit -m "<your message>"
```

### Security check for endpoints

The pre-commit hook also runs a check to make sure that all endpoints have been evaluated for access control
using the below script.

```bash
poetry run python routes_security_check.py
```

Script accepts the following arguments:

- `--log-level`: Set the logging level. The default is `INFO`.
- `--short`: Print only the summary
- `--files-summary`: Print the summary of each file

## Unit Tests

Setup variables:
```bash
export GENAI_ENGINE_SECRET_STORE_KEY="some_test_key"
```

Run the unit tests with the following command:

```bash
poetry run pytest -m "unit_tests"
```

Run the unit tests with coverage:

```bash
poetry run pytest -m "unit_tests" --cov=src --cov-fail-under=79
```

## Integration Tests

1. Make sure you have a running instance of genai-engine on your local machine
2. Set the below envars
   ```bash
   export REMOTE_TEST_URL=http://localhost:3030
   export REMOTE_TEST_KEY=changeme123
   ```
3. Run the below shell script from the `genai-engine` directory
   ```bash
   ./tests/test_remote.sh
   ```

## Performance Tests

For running performance tests, we use [Locust](https://locust.io/).

Follow the steps below to run performance tests:

1. Install Locust
   ```bash
   poetry install --only performance
   ```
2. Run performance tests by referring to the [Locust README](locust/README.md)

## Generate Changelog

Prerequisites in terminal:
```bash
brew install oasdiff
export PYTHONPATH="src:$PYTHONPATH"
```

`poetry run generate_changelog` from the genai-engine directory when making changes to routes and request/response schemas.

If you can't install torch on your computer and want to generate the changelog from a container, run
`docker compose up -d changelog-generator` from the genai-engine directory instead.
