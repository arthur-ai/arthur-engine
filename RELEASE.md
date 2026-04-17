# Releasing to Production

## 1. Merge your feature branch to `dev`

Open a PR from your feature branch into `dev` and merge it.

## 2. Wait for the Version Management workflow

After the merge lands, the [Version Management](https://github.com/arthur-ai/arthur-engine/actions/workflows/version-workflow.yml) workflow runs automatically. It syncs any divergence from `main` and commits a version bump (`"Increment arthur-engine version to X.Y.Z"`) directly to `dev`. This also triggers a dev build (Docker images, Helm charts, etc.). After the dev resources are created, it will trigger a workflow in the arthur-scope GitLab repository to release the engine to the sts-arthur-dev account.

## 3. Create the release PR

Once the version bump has landed on `dev`, trigger the [Create Release PR](https://github.com/arthur-ai/arthur-engine/actions/workflows/create-release-pr.yml) workflow via **Run workflow**.

This creates a PR from `dev` → `main` with the correct title to trigger the production pipeline. Review and merge it — all production artifacts are built and published automatically when it lands on `main`.

## What gets published and from where

All production publishing is triggered by the version bump commit landing on `main`. Two workflows fire in parallel:

**[Arthur Engine CI](https://github.com/arthur-ai/arthur-engine/actions/workflows/arthur-engine-workflow.yml)**
- GenAI Engine Docker images (CPU + GPU) → Docker Hub
- ML Engine Docker images → Docker Hub + Artifactory
- Models Docker images → Docker Hub
- CloudFormation templates → S3
- Helm charts → GHCR + Docker Hub
- Git tag for the release
- Triggers the GitLab deployment pipeline

**[Arthur Observability SDK Release](https://github.com/arthur-ai/arthur-engine/actions/workflows/arthur-observability-sdk-release.yml)**
- Python observability SDK → PyPI (stable release)
- SDK git tag (`sdk-vX.Y.Z`)

No extra release steps are needed for the SDK — it picks up the same trigger automatically.
