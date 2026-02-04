# Model Upload - Unified Multi-Backend Image

This directory contains a **unified Docker image** for uploading ML models to different storage backends. Instead of maintaining 3 separate implementations, this single codebase supports:

- **S3** (AWS)
- **GCS** (Google Cloud Storage)
- **Filesystem** (Kubernetes PVC)

## Architecture

The unified approach uses:

1. **Single `upload_models.py`** - Runtime backend selection via `STORAGE_BACKEND` env var
2. **Single `Dockerfile`** - Build-time dependency selection via `--build-arg BACKEND=<s3|gcs|k8s>`
3. **Optimal image sizes** - Each variant includes only necessary dependencies
4. **Security-first** - Distroless runtime for S3/K8s, slim runtime only where required (GCS)

## Quick Start

### Build Images

Use the provided build script:

```bash
# Build all variants
./build.sh all

# Build specific backend
./build.sh s3
./build.sh gcs
./build.sh k8s

# Build with version tag
./build.sh --version 2.1.343 all

# Build and push to registry
./build.sh --push --version 2.1.343 all
```

Or build directly with Docker:

```bash
# S3 variant (distroless)
docker build --build-arg BACKEND=s3 --target runtime-distroless \
  -t arthurplatform/genai-engine-models:latest-s3 .

# GCS variant (slim, required for google-cloud-storage)
docker build --build-arg BACKEND=gcs --target runtime-slim \
  -t arthurplatform/genai-engine-models:latest-gcs .

# K8s variant (distroless)
docker build --build-arg BACKEND=k8s --target runtime-distroless \
  -t arthurplatform/genai-engine-models:latest-k8s .
```

### Run Containers

**S3 Backend:**
```bash
docker run --rm \
  -e STORAGE_BACKEND=s3 \
  -e S3_BUCKET=my-bucket \
  -e S3_PREFIX=models \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  arthurplatform/genai-engine-models:latest-s3
```

**GCS Backend:**
```bash
docker run --rm \
  -e STORAGE_BACKEND=gcs \
  -e GCS_BUCKET=my-bucket \
  -e GCS_PREFIX=models \
  -e GOOGLE_APPLICATION_CREDENTIALS=/path/to/creds.json \
  -v /path/to/creds.json:/path/to/creds.json:ro \
  arthurplatform/genai-engine-models:latest-gcs
```

**Filesystem Backend (K8s PVC):**
```bash
docker run --rm \
  -e STORAGE_BACKEND=filesystem \
  -e SOURCE_DIR=/models \
  -e TARGET_DIR=/models-output \
  -v /path/to/output:/models-output \
  arthurplatform/genai-engine-models:latest-k8s
```

## Environment Variables

### Required for All Backends

- `STORAGE_BACKEND` - Storage backend to use (`s3`, `gcs`, or `filesystem`)
- `LOG_LEVEL` - Logging level (default: `INFO`)

### S3 Backend

- `S3_BUCKET` - Target S3 bucket name (required)
- `S3_PREFIX` - Prefix for S3 keys (optional)
- `MODELS_DIR` - Local directory containing models (default: `/models`)
- AWS credentials via standard AWS environment variables or IAM role

### GCS Backend

- `GCS_BUCKET` - Target GCS bucket name (required)
- `GCS_PREFIX` - Prefix for GCS object names (optional)
- `MODELS_DIR` - Local directory containing models (default: `/models`)
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to service account JSON (optional, uses Workload Identity if unset)

### Filesystem Backend

- `SOURCE_DIR` - Source directory containing models (default: `/models`)
- `TARGET_DIR` - Target directory for PVC (default: `/models-output`)

## Docker Image Tags

Images are tagged with the following convention:

```
arthurplatform/genai-engine-models:<version>-<backend>
arthurplatform/genai-engine-models:latest-<backend>
```

Examples:
- `arthurplatform/genai-engine-models:2.1.343-s3`
- `arthurplatform/genai-engine-models:2.1.343-gcs`
- `arthurplatform/genai-engine-models:2.1.343-k8s`
- `arthurplatform/genai-engine-models:latest-s3`

## Deployment Examples

### AWS ECS Task Definition

```json
{
  "family": "arthur-model-upload",
  "containerDefinitions": [{
    "name": "model-upload",
    "image": "arthurplatform/genai-engine-models:2.1.343-s3",
    "environment": [
      { "name": "STORAGE_BACKEND", "value": "s3" },
      { "name": "S3_BUCKET", "value": "my-models-bucket" },
      { "name": "S3_PREFIX", "value": "models" }
    ]
  }]
}
```

### GCP Cloud Run Job

```yaml
apiVersion: run.googleapis.com/v1
kind: Job
metadata:
  name: arthur-model-upload
spec:
  template:
    spec:
      template:
        spec:
          containers:
            - image: arthurplatform/genai-engine-models:2.1.343-gcs
              env:
                - name: STORAGE_BACKEND
                  value: gcs
                - name: GCS_BUCKET
                  value: my-models-bucket
                - name: GCS_PREFIX
                  value: models
```

### Kubernetes Job

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: arthur-model-upload
spec:
  template:
    spec:
      containers:
      - name: model-upload
        image: arthurplatform/genai-engine-models:2.1.343-k8s
        env:
        - name: STORAGE_BACKEND
          value: filesystem
        - name: SOURCE_DIR
          value: /models
        - name: TARGET_DIR
          value: /models-output
        volumeMounts:
        - name: models-storage
          mountPath: /models-output
      volumes:
      - name: models-storage
        persistentVolumeClaim:
          claimName: arthur-models-pvc
```

## Image Sizes

Approximate image sizes by backend:

- **S3 (distroless)**: ~1.8 GB (models) + ~50 MB (runtime)
- **GCS (slim)**: ~1.8 GB (models) + ~150 MB (runtime, includes cryptography deps)
- **K8s (distroless)**: ~1.8 GB (models) + ~20 MB (runtime, no cloud deps)

## CI/CD Integration

### Check for Model Updates

Use `check_model_updates.py` to optimize your CI/CD pipeline by only rebuilding images when models are updated on Hugging Face Hub:

```bash
# Check if models have been updated
poetry run python check_model_updates.py

# Update manifest after rebuild
poetry run python check_model_updates.py --update

# Use in CI/CD (GitHub Actions format)
poetry run python check_model_updates.py --output github
# Outputs: has_updates=true/false, current_hash=..., existing_hash=...
```

Example GitHub Actions workflow:

```yaml
- name: Check for model updates
  id: check_models
  run: |
    cd deployment/model-upload
    poetry install
    poetry run python check_model_updates.py --output github >> $GITHUB_OUTPUT

- name: Build images
  if: steps.check_models.outputs.has_updates == 'true'
  run: |
    cd deployment/model-upload
    ./build.sh --version ${{ github.sha }} --push all

- name: Update manifest
  if: steps.check_models.outputs.has_updates == 'true'
  run: |
    cd deployment/model-upload
    poetry run python check_model_updates.py --update
    git add models-manifest.json
    git commit -m "chore: update models manifest to ${{ steps.check_models.outputs.current_hash }}"
```

## Development

### Local Testing

```bash
# Install dependencies
poetry install

# Check for model updates
poetry run python check_model_updates.py

# Download models locally
poetry run python download_models.py --output-dir ./models

# Test S3 upload (requires AWS credentials)
export STORAGE_BACKEND=s3
export S3_BUCKET=test-bucket
poetry run python upload_models.py

# Test GCS upload (requires GCP credentials)
export STORAGE_BACKEND=gcs
export GCS_BUCKET=test-bucket
poetry run python upload_models.py

# Test filesystem copy
export STORAGE_BACKEND=filesystem
export SOURCE_DIR=./models
export TARGET_DIR=./output
poetry run python upload_models.py
```

### Running Tests

```bash
poetry install --with dev
poetry run pytest
poetry run black .
poetry run isort .
poetry run mypy upload_models.py download_models.py
```

## Migration from Old Structure

The old structure had 3 separate directories:
- `deployment/ecs/model-upload/` → S3-specific
- `deployment/gcp/model-upload/` → GCS-specific
- `deployment/k8s/model-upload-oc/` → Filesystem-specific

This unified approach consolidates all three into a single codebase with:
- Single source of truth for model upload logic
- Easier maintenance and updates
- Consistent behavior across all backends
- Build-time optimization for image size and security

## Security

- **Distroless images** for S3/K8s backends (minimal attack surface, no shell)
- **Non-root user** (UID 65532) for all images
- **Minimal dependencies** - only includes required cloud provider SDKs
- **No secrets in images** - all credentials via environment variables or IAM/Workload Identity

## Models Included

The following models are pre-downloaded during build:

- `sentence-transformers/all-MiniLM-L12-v2` - Embeddings
- `ProtectAI/deberta-v3-base-prompt-injection-v2` - Prompt injection detection
- `s-nlp/roberta_toxicity_classifier` - Toxicity detection
- `microsoft/deberta-v2-xlarge-mnli` - Relevance/entailment
- `urchade/gliner_multi_pii-v1` - PII detection
- `microsoft/mdeberta-v3-base` - Base model for GLiNER
- `tarekziade/pardonmyai` - Additional classifier

Total size: ~1.8 GB

## Troubleshooting

### Build Issues

**Problem**: Poetry dependency resolution fails
```bash
# Solution: Delete lock file and regenerate
rm poetry.lock
poetry lock --no-update
```

**Problem**: Docker build fails on COPY poetry.lock
```bash
# Solution: Generate lock file first
poetry lock --no-update
docker build ...
```

### Runtime Issues

**Problem**: Import error for boto3/google-cloud-storage
```bash
# Solution: Ensure correct BACKEND build arg was used
docker build --build-arg BACKEND=gcs ...  # for GCS
docker build --build-arg BACKEND=s3 ...   # for S3
```

**Problem**: Permission denied writing to volume (K8s)
```bash
# Solution: Check PVC permissions and securityContext
# Ensure runAsUser matches volume ownership
```

## Contributing

When making changes:

1. Update the unified `upload_models.py` script
2. Test all three backends locally
3. Update this README if adding new features or env vars
4. Regenerate `poetry.lock` if dependencies change
5. Build and test all three image variants

## License

Copyright Arthur AI - All Rights Reserved
