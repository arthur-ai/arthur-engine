# Release Process

## Prerequisites
- Ensure all necessary commits are merged to the `dev` branch
- Verify integration tests are passing for the ML engine by running them locally
- Verify integration tests are passing for the GenAI engine by running them locally

## Dev Release
1. In GitHub Actions, manually run the **Version Management** workflow with the default inputs (`dev` branch, patch bump)
2. This will create a dev release and trigger the Arthur Engine CI workflow

## Production Release
1. After the dev release pipeline has succeeded, create a PR to merge `dev` into `main`
2. **Important**: The version bump commit must be the most recent commit in this PR, or the release won't be triggered
3. Merge the PR to trigger the production release
4. Let Madeleine know to publish the release notes on GitHub.

> **Note**: The version bump commit requirement prevents unintended commits from being included in the release.
