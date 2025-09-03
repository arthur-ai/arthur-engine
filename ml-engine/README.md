# ML Engine
This is the repository for the Arthur ML Engine, which computes evals over user-configured datasets in the Arthur Platform.

# Table of Contents
- [Developer Setup (for Mac)](#developer-setup-for-mac)
  - [Running ML Engine in Docker](#running-ml-engine-in-docker)
    - [Prerequisites](#prerequisites)
    - [Running Local ML Engine Build in Docker](#running-local-ml-engine-build-in-docker)
  - [Running ML Engine in Terminal](#running-ml-engine-in-terminal-window)
    - [Install Prerequisites](#install-prerequisite)
    - [Set Up Python Environment](#set-up-python-environment)
    - [Configure Environment](#setup-environment-configuration)
    - [Run ML Engine](#run-the-ml-engine)
  - [Running the Linter](#running-the-linter)
  - [Running the Unit tests](#run-unit-tests)
  - [Running the Integration tests](#run-integration-tests)
  - [Running the ML Engine with Local Arthur-Client](#running-the-ml-engine-with-a-local-version-of-the-arthur-client-optional-dev-only)
  - [Running the ML Engine with Local Arthur-Common](#running-the-ml-engine-with-a-local-version-of-arthur-common-optional-dev-only)


## Developer Setup (for Mac)

### Running ML Engine in Docker
This guide assumes you are running the ML engine against a hosted Arthur Platform (likely dev or prod).
If you are trying to run the ML engine against a local Arthur stack, you should follow the [arthur-scope README](https://gitlab.com/ArthurAI/arthur-scope/-/tree/main/scope/app_plane?ref_type=heads)
to do so. As part of standing up the full Arthur stack, you will stand up an ML engine in Docker via the arthur-scope guide.

#### Prerequisites
1. Install docker via [Docker for Mac](https://docs.docker.com/desktop/setup/install/mac-install/)
2. Acquire Credentials for the ML Engine to authenticate with a hosted Arthur Platform (dev or prod):
   1. Credentials for Prod: Go to the Engines Management screen in your workspace (or you can follow the engine onboarding
      workflow at https://platform.arthur.ai/onboarding if you're a new tenant) and add a new engine.
   2. Credentials for Dev: The same as above, but go to https://scope-v4.dev.arthur.ai/onboarding.
      You must be behind Arthur VPN for this.
   3. You have two options to run the ML Engine:
      1. If you're testing or running an already-released, hosted ML engine images, then follow the directions in the
         UI to run the ML engine and pull the hosted image. This will also run a GenAI Engine locally.
      2. If you're trying to run a local build of the ML engine, follow the [steps below](#running-local-ml-engine-build-in-docker).
         Pull the `--arthur-client-id`, `--arthur-client-secret`, and `--arthur-api-host` secrets from the UI.

#### Running Local ML Engine Build in Docker
1. Generate fresh GenAI Client to be used in the Docker build.

From `/arthur-engine/ml-engine`:
```bash
cd scripts
./openapi_client_utils.sh generate python
```
2. Build image based on local code
```bash
cd ..
docker build . -t ml-engine:local
```
3. Run docker image
```bash
docker run -e ARTHUR_API_HOST=https://platform.arthur.ai -e ARTHUR_CLIENT_SECRET=<value given when engine is registered> -e ARTHUR_CLIENT_ID=<value given when engine is registered> -it ml-engine:local
```

### Running ML Engine in Terminal Window

#### Install prerequisite
1. Install Poetry
```bash
pip install "poetry>=2,<3"
```

#### Set Up Python Environment
Assume all commands are run from `arthur-engine/ml-engine`path:

1. Use poetry environment with Python 3.13
```bash
poetry env use 3.13
```

2. Generate and Install GenAI Client
```bash
cd scripts
./openapi_client_utils.sh generate python
./openapi_client_utils.sh install python
```

3. Install system dependencies for database drivers
This must happen before Step 4 (install the Python dependencies) because some of the Python packages depend on these
system libraries.

```bash
# Run the installation script (still in the scripts directory)
./install_db_dependencies.sh
```

This script installs system dependencies for:
- **psycopg** (PostgreSQL) - PostgreSQL client libraries
- **pymysql** (MySQL) - MySQL client libraries
- **pyodbc** (ODBC) - ODBC driver manager

The script supports Mac systems only.

**Note:** This script is designed for local development installations. For Docker deployments, the database dependencies are automatically installed during the Docker build process.

4. Install Oracle Manually for database drivers (optional, for running the engine locally only—not currently needed for unit tests)

**NOTE**: This is only required if you are doing work with an ODBC Connector that is connecting to an Oracle database.
If that doesn't apply to you you can skip this step and come back to it when it's needed. Oracle is still built into
the ML engine, so if it does apply to you but you don't want to have to do this, just run the ML engine you're using
in Docker instead of in your Python environment.

For Intel Macs, follow the instructions here: https://www.oracle.com/database/technologies/instant-client/macos-intel-x86-downloads.html.
You need to install both the Basic and the ODBC package linked on that page.

For ARM Macs, follow the installation instructions here: https://www.oracle.com/database/technologies/instant-client/macos-arm64-downloads.html
You need to install both the Basic and the ODBC package linked on that page.

5. Install Python dependencies
```bash
poetry install
```

#### Setup environment Configuration

If you're trying to run the arthur-scope integration tests, use the admin key in the "Engine Development" item in 1pass
as your `GENAI_ENGINE_INTERNAL_API_KEY` so the ML engine can authenticate with the GenAI Dev Engine. If you want the
ML engine to be communicating with a different GenAI engine, set the `GENAI_ENGINE_INTERNAL_*` secrets accordingly.

```bash
export ARTHUR_API_HOST=https://platform.arthur.ai
export ARTHUR_CLIENT_SECRET=<value given when engine is registered>
export ARTHUR_CLIENT_ID=<value given when engine is registered>
export GENAI_ENGINE_INTERNAL_API_KEY=<fill-in-here>
export GENAI_ENGINE_INTERNAL_HOST=https://engine.development.arthur.ai
export GENAI_ENGINE_INTERNAL_INGRESS_HOST=https://engine.development.arthur.ai
```

#### Run the ML Engine

Use this command to start the app:

```bash
poetry run python src/ml_engine/job_agent.py
```

If the app has started successfully, can communicate with the control plane, and is polling for jobs,
the logs should look as follows:
```INFO:root:Checking for jobs...```

**NOTE**: The ML engine only picks up jobs when it's running in an environment with enough available memory that it
thinks it will be able to complete the jobs. If your computer is low on memory, your ML engine might not dequeue
all job kinds (some require less memory availability than others). If you run into this issue, either free up some memory
or alter this function in the ML engine code: https://github.com/arthur-ai/arthur-engine/blob/dev/ml-engine/src/ml_engine/job_agent.py#L73
to always return `4000`. This will trick your ML engine into thinking it has enough memory to dequeue every currently
existing job kind.

### Running the linter

Prerequisite: [Set up your Python environment](#set-up-python-environment).

You have two options to run the linter:

1. Install pre-commits, it will automatically run linters for you before you commit.
   See [CONTRIBUTING.MD](../CONTRIBUTING.md#install-the-pre-commit-hooks-before-making-your-first-commit) for how.
2. You can manually trigger the linters
```bash
cd scripts
./lint.sh
```

Commit any linter changes.

### Run Unit Tests

Prerequisite: [Set up your Python environment](#set-up-python-environment).

```bash
poetry install --with dev
poetry run pytest tests/
```

**NOTE**: If your computer is low on resources (specifically available memory), you may see failures in the
test_job_agent_parallellism.py test that don't have to do with your changes. If you see unexpected failures to do with
a lower available memory than expected, try freeing up some memory to get the tests to pass.

### Run Integration Tests
Integration tests are run from arthur-scope: https://gitlab.com/ArthurAI/arthur-scope/-/tree/main/scope/app_plane?ref_type=heads#run-integration-tests

Just make sure you've checked out the branch in this repo with the code changes you want to test.

**NOTE**: If you've made changes to the ML engine image requirements, you'll need to delete any existing `ml-engine` image
tagged as `latest` in your local Docker image repository. If you've only made code changes, this isn't necessary;
the docker-compose in arthur-scope mounts your local ML engine source code as a volume in the data-plane service so that it picks up
any of your local code changes without requiring a rebuild.

### Running the ML Engine with a Local Version of the Arthur-Client (Optional, Dev only)
The most likely reason you're doing this is because you are a dev doing testing who wants to install a local version of
the arthur-client generated based on changes that haven't been released yet. These instructions will include how to run
the integration tests locally. The easiest way to do this is outside of Docker so you don't have to build the local
version of the arthur-client into the Docker image.

1. From the ml-engine directory, [set up your Python environment](#set-up-python-environment). All Python environment set up steps
   MUST happen before step 3 in this guide (particularly `poetry install`) or the local version of the arthur-client that you install
   will get overwritten by the project dependency installation.
2. From the `arthur-scope` repository, run the OpenAPI Client generation & install steps in the [root README](https://gitlab.com/ArthurAI/arthur-scope#generate-client).
3. From this repository, run `./scripts/install_local_scope_packages.sh`. If you did not clone arthur-scope into your home directory, you
   will need to update the path referenced in the script that installs the client. Assuming you completed step 2 and
   your paths are set as expected (ie arthur-scope is cloned into your root directory), this will install your local
   version of the arthur client. Make sure you run this in the same environment you are going to run the ML engine in
   and just set up in step 1.
4. Run the full stack in the arthur-scope repository. For now, you will not want to run the control plane or integration tests in Docker,
   because it will complicate the current docker-compose set up by also standing up a new ml-engine service without your
   local arthur-client install. Follow the following steps instead:
   1. Follow directions [here](https://gitlab.com/ArthurAI/arthur-scope/-/tree/main/scope/app_plane?ref_type=heads#set-up-python-environment) to set up an environment to run the control plane in.
   2. Follow directions [here](https://gitlab.com/ArthurAI/arthur-scope/-/tree/main/scope/app_plane?ref_type=heads#running-the-app) to run the control plane.
5. Follow the [Setup environment](#setup-environment-configuration) and [Run the ML Engine](#run-the-ml-engine) steps to finish
   running the ML engine locally. Make sure you configure the environment variables to point to your local stack.
   Do this by copying the [environment setup](https://gitlab.com/ArthurAI/arthur-scope/-/blob/main/docker-compose.yaml#L372)
   that would be used if you were running the ML engine in docker. These environment variables should all be exported
   as in the linked configuration to the environment you're running the ML engine is. The only difference is that,
   assuming you're running the arthur-scope stack as in step 4, you'll need to use `export ARTHUR_API_HOST="http://localhost:8000"`
   instead because you aren't running the ML-engine in the same Docker network as the control plane.
6. Once the ML engine is running locally, you can follow directions [here](https://gitlab.com/ArthurAI/arthur-scope/-/tree/main/scope/app_plane?ref_type=heads#option-2-run-integration-tests-locally) to run the integration tests.

### Running the ML Engine with a Local Version of Arthur-Common (Optional, Dev only)
The arthur-common package is hosted in [Github](https://github.com/arthur-ai/arthur-common).

The most likely reason you're doing this is because you are a dev doing testing who wants to install a local version of
the arthur-common package with changes that haven't been released yet. These instructions will include how to run
the integration tests locally. The easiest way to do this is outside of Docker so you don't have to build the local
version of the arthur-client into the Docker image.

1. From the ml-engine directory, [set up your Python environment](#set-up-python-environment). This MUST happen before
   step 2 or the local arthur-common package you install will get overwritten by the one in the ml-engine pyproject.toml.
2. In the same environment you just configured, go to arthur-common and run `pip install .`
3. Complete steps 4-6 [above](#running-the-ml-engine-with-a-local-version-of-arthur-common-optional-dev-only).
