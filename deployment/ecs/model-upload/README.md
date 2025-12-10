# Arthur Model Upload - ECS Task

An ECS task that uploads pre-downloaded ML models to an S3 bucket for airgapped deployments.

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

## Local Development

```bash
# Install dependencies with Poetry
poetry install

# Download models locally
poetry run python download_models.py --output-dir ./models --workers 4

# Test upload (requires AWS credentials)
S3_BUCKET=my-bucket S3_PREFIX=models MODELS_DIR=./models poetry run python upload_models.py
```
