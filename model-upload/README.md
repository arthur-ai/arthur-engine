# Model Upload - Unified Multi-Backend Image

This directory contains a **unified Docker image** for uploading ML models to different storage backends. A single image supports all three backends — the backend is selected at runtime via the `STORAGE_BACKEND` environment variable.

- **S3** (AWS)
- **GCS** (Google Cloud Storage)
- **Filesystem** (Kubernetes PVC)

## Quick Start

### Build

```bash
# Build the image
./build.sh

# Build with version tag
./build.sh --version 2.1.345

# Build and push to registry
./build.sh --push --version 2.1.345
```

Or build directly with Docker:

```bash
docker build -t arthurplatform/genai-engine-models:latest .
```

### Run

**S3 Backend:**
```bash
docker run --rm \
  -e STORAGE_BACKEND=s3 \
  -e S3_BUCKET=my-bucket \
  -e S3_PREFIX=models \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  arthurplatform/genai-engine-models:latest
```

**GCS Backend:**
```bash
docker run --rm \
  -e STORAGE_BACKEND=gcs \
  -e GCS_BUCKET=my-bucket \
  -e GCS_PREFIX=models \
  -e GOOGLE_APPLICATION_CREDENTIALS=/creds/sa.json \
  -v /path/to/creds.json:/creds/sa.json:ro \
  arthurplatform/genai-engine-models:latest
```

**Filesystem Backend (K8s PVC):**
```bash
docker run --rm \
  -e STORAGE_BACKEND=filesystem \
  -e SOURCE_DIR=/models \
  -e TARGET_DIR=/models-output \
  -v /path/to/output:/models-output \
  arthurplatform/genai-engine-models:latest
```

## Environment Variables

### Required

- `STORAGE_BACKEND` - Storage backend to use (`s3`, `gcs`, or `filesystem`)

### S3 Backend

- `S3_BUCKET` - Target S3 bucket name (required)
- `S3_PREFIX` - Prefix for S3 keys (optional)
- AWS credentials via standard environment variables or IAM role

### GCS Backend

- `GCS_BUCKET` - Target GCS bucket name (required)
- `GCS_PREFIX` - Prefix for GCS object names (optional)
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to service account JSON (optional, uses Workload Identity if unset)

### Filesystem Backend

- `SOURCE_DIR` - Source directory containing models (default: `/models`)
- `TARGET_DIR` - Target directory for PVC (default: `/models-output`)

### Common

- `MODELS_DIR` - Local directory containing models (default: `/models`)
- `LOG_LEVEL` - Logging level (default: `INFO`)

## Docker Image Tags

```
arthurplatform/genai-engine-models:<version>
arthurplatform/genai-engine-models:latest
```

Examples:
- `arthurplatform/genai-engine-models:2.1.345`
- `arthurplatform/genai-engine-models:latest`

## Deployment

### Helm (Kubernetes / OpenShift)

The Helm chart at `deployment/helm/model-upload/` supports all three backends via the `storageBackend` value:

```bash
# S3 backend (AWS/EKS)
helm install model-upload deployment/helm/model-upload/ \
  --set storageBackend=s3 \
  --set s3Bucket=my-bucket

# GCS backend (GKE)
helm install model-upload deployment/helm/model-upload/ \
  --set storageBackend=gcs \
  --set gcs.bucket=my-bucket

# Filesystem backend (OpenShift PVC)
helm install model-upload deployment/helm/model-upload/ \
  --set storageBackend=filesystem
```

### AWS ECS

See `deployment/ecs/model-upload/` for the ECS Fargate task definition.

### GCP Cloud Run

See `deployment/gcp/model-upload/` for the Cloud Run Job definition.

### Raw Kubernetes (OpenShift)

See `deployment/k8s/model-upload-oc/` for raw K8s manifests with PVC.

## CI/CD Integration

### Check for Model Updates

```bash
poetry run python check_model_updates.py
poetry run python check_model_updates.py --update
poetry run python check_model_updates.py --output github
```

## Development

```bash
# Install dependencies
poetry install

# Download models locally
poetry run python download_models.py --output-dir ./models

# Test S3 upload
STORAGE_BACKEND=s3 S3_BUCKET=test-bucket poetry run python upload_models.py

# Test GCS upload
STORAGE_BACKEND=gcs GCS_BUCKET=test-bucket poetry run python upload_models.py

# Test filesystem copy
STORAGE_BACKEND=filesystem SOURCE_DIR=./models TARGET_DIR=./output poetry run python upload_models.py
```

## Models Included

- `sentence-transformers/all-MiniLM-L12-v2` - Embeddings
- `ProtectAI/deberta-v3-base-prompt-injection-v2` - Prompt injection detection
- `s-nlp/roberta_toxicity_classifier` - Toxicity detection
- `microsoft/deberta-v2-xlarge-mnli` - Relevance/entailment
- `urchade/gliner_multi_pii-v1` - PII detection
- `microsoft/mdeberta-v3-base` - Base model for GLiNER
- `tarekziade/pardonmyai` - Additional classifier

Total size: ~1.8 GB

## Migration from Old Structure

The old structure had 3 separate directories with separate Dockerfiles:
- `deployment/ecs/model-upload/` → S3-specific
- `deployment/gcp/model-upload/` → GCS-specific
- `deployment/k8s/model-upload-oc/` → Filesystem-specific

This unified approach consolidates all three into:
- Single `upload_models.py` with runtime backend selection
- Single Docker image with all dependencies
- Single Helm chart supporting all backends
- Deployment-specific configs remain in their respective folders (ECS, GCP Cloud Run, raw K8s)

## License

Copyright Arthur AI - All Rights Reserved
