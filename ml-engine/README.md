# ML Engine

- [ML Engine](#ml-engine)
  - [Developer Setup (for Mac)](#developer-setup-for-mac)
    - [Install prerequisite](#install-prerequisite)
    - [Set Up Python Environment](#set-up-python-environment)
  - [Running the ML Engine](#running-the-ml-engine)
    - [Setup environment](#setup-environment)
    - [Running the linter](#running-the-linter)
    - [Run Tests](#run-tests)
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
2. Install dependencies
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
