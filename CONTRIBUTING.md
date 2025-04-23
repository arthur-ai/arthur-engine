# Make code contributions to the Arthur Engine

We welcome contributions to the Arthur Engine! Please follow the steps below to contribute.

## Make a pull request

All contributions to the Arthur Engine need to be made via pull requests.
1. Fork the repository
2. Clone a local version of your forked repository
3. Install the pre-commit hooks by following the instructions in [Install the pre-commit hooks before making your first commit](#install-the-pre-commit-hooks-before-making-your-first-commit)
4. Install the Python packages by following the developer setup instructions in each module
   1. [genai-engine](./genai-engine/README.md)
   2. [ml-engine](./ml-engine/README.md)
5. Create a new branch for your changes with an informative name
6. Commit your changes and make sure any issues raised by the pre-commit hook are addressed
7. Push the new branch to your forked repository
8. Create a pull request to the `dev` branch of the Arthur Engine repository with a description of your changes

## Install the pre-commit hooks before making your first commit

The pre-commit hooks run certain house-keeping tasks before a git commit can be made.
It ensures that your contributions will pass the CICD pipeline.
The pre-commit hook rules are defined [here](./.pre-commit-config.yaml).
Before making your first commit, please follow the instructions below to install the pre-commit hook.

1. Install [OASDiff](https://github.com/Tufin/oasdiff/releases/tag/v1.10.23) for auto-generating API changelog
2. Change directory to the module you are contributing to (i.e. `genai-engine` or `ml-engine`)
3. Install `pre-commit` package:
    ```
    poetry install --only dev
    ```
4. Install the git pre-commit hooks:
    ```
    poetry run pre-commit install
    ```
