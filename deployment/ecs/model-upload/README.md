# Arthur Model Upload - ECS Task (S3 Version)

An ECS task that uploads pre-downloaded ML models to an S3 bucket for airgapped deployments.

> **Note**: This is the **S3 version**. For OpenShift/Kubernetes deployments using PersistentVolumes (no S3), see `../../k8s/model-upload-oc/`.

## Overview

This task:
1. Downloads ML models from Hugging Face during Docker build
2. When run as an ECS task, uploads all models to a specified S3 bucket
3. The genai-engine can then fetch models from S3 using `MODEL_REPOSITORY_URL`

## Architecture

```
┌──────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Docker Build    │────▶│   ECS Task       │────▶│    S3 Bucket    │
│  (download from  │     │  (upload to S3)  │     │   /models/...   │
│   Hugging Face)  │     │                  │     │                 │
└──────────────────┘     └──────────────────┘     └─────────────────┘
                                                           │
                                                           ▼
                                                  ┌─────────────────┐
                                                  │  genai-engine   │
                                                  │  MODEL_REPO_URL │
                                                  └─────────────────┘
```

## Quick Start

### Build the Docker Image

The Dockerfile uses a multi-stage distroless build for minimal attack surface:

```bash
# Build the image (includes all models: relevance, PII v2, etc.)
docker build -t arthur-model-upload:latest .
```

### Run Locally (for testing)

```bash
# Set AWS credentials
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_REGION=us-east-1

# Run the upload task
docker run --rm \
  -e S3_BUCKET=my-models-bucket \
  -e S3_PREFIX=models \
  -e AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY \
  -e AWS_REGION \
  arthur-model-upload:latest
```

## ECS Deployment

### 1. Push Image to ECR

```bash
# Authenticate with ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com

# Tag and push
docker tag arthur-model-upload:latest ${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/arthur-model-upload:latest
docker push ${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/arthur-model-upload:latest
```

### 2. Create IAM Roles

**Task Execution Role** (for ECR/CloudWatch access):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

**Task Role** (for S3 access):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:HeadObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-models-bucket",
        "arn:aws:s3:::my-models-bucket/*"
      ]
    }
  ]
}
```

### 3. Register Task Definition

```bash
# Replace variables in task-definition.json
export ECR_IMAGE_URI=${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/arthur-model-upload:latest
export EXECUTION_ROLE_ARN=arn:aws:iam::${ACCOUNT_ID}:role/ecsTaskExecutionRole
export TASK_ROLE_ARN=arn:aws:iam::${ACCOUNT_ID}:role/arthur-model-upload-role
export S3_BUCKET=my-models-bucket
export S3_PREFIX=models
export AWS_REGION=us-east-1

envsubst < task-definition.json > task-definition-resolved.json

# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition-resolved.json
```

### 4. Run the Task

```bash
aws ecs run-task \
  --cluster my-cluster \
  --task-definition arthur-model-upload \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `S3_BUCKET` | Yes | - | Target S3 bucket name |
| `S3_PREFIX` | No | `` | Prefix for S3 keys (e.g., `models`) |
| `MODELS_DIR` | No | `/models` | Local directory containing models |
| `LOG_LEVEL` | No | `INFO` | Logging level |

## Included Models

| Model | Size | Description |
|-------|------|-------------|
| `sentence-transformers/all-MiniLM-L12-v2` | ~134MB | Embedding model |
| `ProtectAI/deberta-v3-base-prompt-injection-v2` | ~370MB | Prompt injection detection |
| `s-nlp/roberta_toxicity_classifier` | ~500MB | Toxicity classification |
| `microsoft/deberta-v2-xlarge-mnli` | ~1.8GB | Relevance scoring |
| `urchade/gliner_multi_pii-v1` | ~450MB | PII detection (v2) |
| `tarekziade/pardonmyai` | ~150MB | Profanity detection |

**Total image size: ~3-4GB**

## S3 Bucket Structure

After upload, the S3 bucket will contain:

```
s3://my-bucket/models/
├── sentence-transformers/
│   └── all-MiniLM-L12-v2/
│       ├── config.json
│       ├── model.safetensors
│       └── ...
├── ProtectAI/
│   └── deberta-v3-base-prompt-injection-v2/
│       └── ...
├── s-nlp/
│   └── roberta_toxicity_classifier/
│       └── ...
└── ...
```

## Configure genai-engine

After running the upload task, configure genai-engine to use the S3 bucket:

```bash
# If using S3 HTTP endpoint (public bucket or via CloudFront)
MODEL_REPOSITORY_URL=https://my-bucket.s3.amazonaws.com/models

# Or use presigned URLs / S3 API directly depending on your setup
```

## Model Update Detection

The `check_model_updates.py` script detects when Hugging Face models have been updated by comparing commit hashes against a stored manifest.

### How It Works

1. **Fetches current commits**: Queries the HuggingFace Hub API for the latest commit SHA of each model
2. **Computes combined hash**: Creates a deterministic SHA-256 hash from all model commits
3. **Compares with manifest**: Checks if the current hash differs from `models-manifest.json`
4. **Reports changes**: Outputs which models changed and whether a rebuild is needed

### Usage

```bash
# Check for updates (read-only)
poetry run python check_model_updates.py

# Check and update the manifest file
poetry run python check_model_updates.py --update

# Output in different formats
poetry run python check_model_updates.py --output json    # JSON output
poetry run python check_model_updates.py --output github  # GitHub Actions format
poetry run python check_model_updates.py --output text    # Human-readable (default)

# Use a custom manifest path
poetry run python check_model_updates.py --manifest /path/to/manifest.json
```

### Command-Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--manifest` | `-m` | Path to manifest file (default: `models-manifest.json` in script dir) |
| `--update` | `-u` | Update the manifest file with current model commits |
| `--output` | `-o` | Output format: `text`, `json`, or `github` |

### Output Formats

**Text (default)**:
```
Result: BUILD REQUIRED
```
or
```
Result: NO BUILD NEEDED
```

**JSON**:
```json
{
  "has_updates": true,
  "current_hash": "8ecf33fa686a2a29",
  "existing_hash": "abc123...",
  "model_commits": { ... }
}
```

**GitHub Actions**:
```
has_updates=true
current_hash=8ecf33fa686a2a29
existing_hash=abc123...
```

### Manifest File

The `models-manifest.json` stores the last known state:

```json
{
  "combined_hash": "8ecf33fa686a2a29",
  "model_commits": {
    "sentence-transformers/all-MiniLM-L12-v2": "c004d8e3e901...",
    "ProtectAI/deberta-v3-base-prompt-injection-v2": "e6535ca4ce3b...",
    ...
  }
}
```

## CI/CD Integration

The `check_model_updates.py` script is integrated into the GitHub Actions workflow (`arthur-engine-workflow.yml`) to automatically rebuild the models Docker image when upstream models change.

### Workflow Steps

1. **Check for updates** (`check-models-updates` job):
   ```yaml
   - name: Check for model updates on HuggingFace
     id: check-updates
     run: |
       cd deployment/ecs/model-upload
       python check_model_updates.py --output github >> $GITHUB_OUTPUT
   ```
   This outputs `has_updates`, `current_hash`, and `existing_hash` for use by subsequent jobs.

2. **Conditional build** (`build-genai-engine-models-docker-image` job):
   - Only runs when `has_updates == 'true'`
   - Builds and pushes the models Docker image to Docker Hub
   - Tags with version number and `latest-dev`/`latest`

3. **Update manifest**:
   ```yaml
   - name: Update models manifest
     run: |
       cd deployment/ecs/model-upload
       python check_model_updates.py --update
   ```

4. **Commit manifest**:
   ```yaml
   - name: Commit updated manifest
     run: |
       git add deployment/ecs/model-upload/models-manifest.json
       git diff --staged --quiet || git commit -m "Update models manifest [skip ci]"
       git push origin ${{ github.ref_name }}
   ```

### Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          GitHub Actions Workflow                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────┐                                                   │
│  │ check-models-updates │                                                   │
│  │  ┌────────────────┐  │                                                   │
│  │  │ HuggingFace    │  │    has_updates=true?                              │
│  │  │ Hub API        │──┼──────────────────────────┐                        │
│  │  └────────────────┘  │                          │                        │
│  │          │           │                          ▼                        │
│  │          ▼           │              ┌───────────────────────────────┐    │
│  │  ┌────────────────┐  │              │ build-genai-engine-models-    │    │
│  │  │ Compare with   │  │              │ docker-image                  │    │
│  │  │ manifest.json  │  │              │  ┌─────────────────────────┐  │    │
│  │  └────────────────┘  │              │  │ 1. Build Docker image   │  │    │
│  └──────────────────────┘              │  │ 2. Push to Docker Hub   │  │    │
│                                        │  │ 3. Update manifest      │  │    │
│                                        │  │ 4. Commit & push        │  │    │
│                                        │  └─────────────────────────┘  │    │
│                                        └───────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

This ensures:
- Models Docker image is only rebuilt when HuggingFace models actually change
- The manifest is always up-to-date after a successful build
- Unnecessary rebuilds are avoided, saving CI time and resources

## Local Development

```bash
# Install dependencies with Poetry
poetry install

# Download models locally
poetry run python download_models.py --output-dir ./models --workers 4

# Test upload (requires AWS credentials)
S3_BUCKET=my-bucket S3_PREFIX=models MODELS_DIR=./models poetry run python upload_models.py
```
