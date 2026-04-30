# Release Process

## Prerequisites
- Ensure all necessary commits are merged to the `dev` branch
- Verify integration tests are passing for the ML engine by running them locally
- Verify integration tests are passing for the GenAI engine by running them locally

## Dev Release
1. In GitHub Actions, manually run the **Version Management** workflow with the default inputs (`dev` branch, patch bump)
2. This will create a dev release and trigger the Arthur Engine CI workflow

## Production Release
1. After the dev release pipeline has succeeded, in GitHub Actions, manually run the **Create Release PR** workflow (no inputs required).
   - This will sanity-check that `dev` is ahead of `main` and that no existing release PR is open, then open the PR automatically with the correct title.
2. Merge the PR to trigger the production release. **Important**: the merge commit title must match the version bump commit title (GitHub's default when squash-merging), or the release won't be triggered.
3. Let Madeleine know to publish the release notes on GitHub.

> **Note**: Always use the **Create Release PR** workflow instead of opening the PR manually — it enforces the title format and version checks that prevent common release papercuts.
