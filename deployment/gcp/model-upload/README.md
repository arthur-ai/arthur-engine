# Arthur Model Upload - GCP (Cloud Run + GCS)

A Cloud Run Job that uploads pre-downloaded ML models to a Google Cloud Storage (GCS) bucket. Use this when running Arthur on GCP and you want models stored in GCS instead of S3 or a local PVC.

> **Note**: For AWS S3, see `../../ecs/model-upload/`. For OpenShift/Kubernetes with PVC, see `../../k8s/model-upload-oc/`.

## Overview

1. **Docker build**: Downloads ML models from Hugging Face into the image.
2. **Cloud Run Job**: Runs once (or on demand), uploading all models from the image to a GCS bucket.
3. **genai-engine**: Configure `MODEL_REPOSITORY_URL` to point at the GCS bucket (e.g. `gs://your-bucket/models`).

## Prerequisites

- GCP project with billing enabled
- **GCS bucket** for model storage (create in same or different project)
- **Service account** with:
  - `roles/storage.objectCreator` (or `roles/storage.admin`) on the bucket
  - For Cloud Run: used as the job’s service account
- **gcloud** CLI installed and authenticated

## Build and push image

Build the image (includes all default models):

```bash
docker build -t arthur-model-upload-gcp:latest .
```

Push to **Google Container Registry (GCR)** or **Artifact Registry**:

```bash
# GCR
docker tag arthur-model-upload-gcp:latest gcr.io/PROJECT_ID/arthur-model-upload-gcp:latest
docker push gcr.io/PROJECT_ID/arthur-model-upload-gcp:latest

# Or Artifact Registry
docker tag arthur-model-upload-gcp:latest REGION-docker.pkg.dev/PROJECT_ID/REPO_NAME/arthur-model-upload-gcp:latest
docker push REGION-docker.pkg.dev/PROJECT_ID/REPO_NAME/arthur-model-upload-gcp:latest
```

## Create and run the Cloud Run Job

### Option 1: gcloud

```bash
export PROJECT_ID=your-project-id
export REGION=us-central1
export BUCKET_NAME=your-models-bucket
export SA_EMAIL=arthur-model-upload@${PROJECT_ID}.iam.gserviceaccount.com

# Create the job
gcloud run jobs create arthur-model-upload \
  --image gcr.io/${PROJECT_ID}/arthur-model-upload-gcp:latest \
  --region ${REGION} \
  --set-env-vars "GCS_BUCKET=${BUCKET_NAME},GCS_PREFIX=models,MODELS_DIR=/models,LOG_LEVEL=INFO" \
  --service-account ${SA_EMAIL} \
  --cpu 2 \
  --memory 4Gi \
  --task-timeout 3600 \
  --max-retries 0

# Run the job
gcloud run jobs execute arthur-model-upload --region ${REGION}
```

### Option 2: YAML manifest

1. Copy `cloud-run-job.yaml` and replace:
   - `PROJECT_NUMBER`: project number (not project ID), from `gcloud projects describe PROJECT_ID --format='value(projectNumber)'`
   - `REGION`: e.g. `us-central1`
   - `BUCKET_NAME`: your GCS bucket name
   - `PROJECT_ID`: your GCP project ID (in image URL)
   - `SERVICE_ACCOUNT_EMAIL`: e.g. `arthur-model-upload@PROJECT_ID.iam.gserviceaccount.com`
2. Apply:

   ```bash
   gcloud run jobs replace cloud-run-job.yaml --region=REGION
   ```

3. Execute:

   ```bash
   gcloud run jobs execute arthur-model-upload --region=REGION
   ```

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GCS_BUCKET` | Yes | - | Target GCS bucket name |
| `GCS_PREFIX` | No | (empty) | Prefix for object names (e.g. `models`) |
| `MODELS_DIR` | No | `/models` | Local directory containing models in the image |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `GOOGLE_APPLICATION_CREDENTIALS` | No | - | Path to service account JSON; omit when using Workload Identity / default credentials |

## Authentication

- **Cloud Run**: Uses the job’s **service account**. Grant that account `roles/storage.objectCreator` (or broader) on the bucket. No key file needed.
- **Local / other environments**: Set `GOOGLE_APPLICATION_CREDENTIALS` to the path of a service account JSON key with access to the bucket.
- **GKE / Workload Identity**: Run the image as a Kubernetes Job with a K8s service account linked to a GCP service account; the client will use Workload Identity and no key file is required.

## Configure genai-engine to use GCS

Point genai-engine at the bucket (and optional prefix) where models were uploaded:

```bash
# GCS URL (genai-engine must support gs:// or you may need a custom loader)
MODEL_REPOSITORY_URL=gs://your-bucket/models
```

If your deployment uses a different mechanism (e.g. HTTP gateway in front of GCS), set `MODEL_REPOSITORY_URL` (or equivalent) to that URL.

## GCS bucket layout after upload

With `GCS_PREFIX=models` (default in the sample job):

```
gs://your-bucket/models/
├── sentence-transformers/
│   └── all-MiniLM-L12-v2/
│       ├── config.json
│       ├── model.safetensors
│       └── ...
├── ProtectAI/
│   └── deberta-v3-base-prompt-injection-v2/
│       └── ...
└── ...
```

## Included models

Same set as the ECS S3 version: sentence-transformers/all-MiniLM-L12-v2, ProtectAI/deberta-v3-base-prompt-injection-v2, s-nlp/roberta_toxicity_classifier, microsoft/deberta-v2-xlarge-mnli, urchade/gliner_multi_pii-v1, microsoft/mdeberta-v3-base, tarekziade/pardonmyai. Total size is on the order of several GB.

## Testing

### 1. Sanity check (no GCS)

Verify the script runs and fails as expected when `GCS_BUCKET` is missing:

```bash
cd deployment/gcp/model-upload
poetry install
poetry run python upload_models.py
# Expected: exit 1, "GCS_BUCKET environment variable is required"
```

### 2. Local upload to a real GCS bucket

Use a real bucket and service account (create a bucket and key in GCP Console if needed):

```bash
cd deployment/gcp/model-upload
poetry install

# Download one small model to keep test fast (optional: use --output-dir ./models and full default set)
poetry run python download_models.py --output-dir ./models --workers 2 --exclude-relevance

# Upload to GCS
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your-service-account.json
export GCS_BUCKET=your-test-bucket
export GCS_PREFIX=test-models
export MODELS_DIR=./models
poetry run python upload_models.py
```

Check the bucket in GCP Console (Storage → your bucket → `test-models/`).

### 3. Docker build + run (full flow)

Build the image and run the upload against a real bucket (same env vars as above):

```bash
cd deployment/gcp/model-upload
docker build -t arthur-model-upload-gcp:test .

docker run --rm \
  -e GCS_BUCKET=your-test-bucket \
  -e GCS_PREFIX=test-models \
  -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-sa.json \
  -v "$(pwd)/path/to/your-service-account.json:/tmp/gcp-sa.json:ro" \
  arthur-model-upload-gcp:test
```

Use a path that exists inside the container (e.g. `/tmp/gcp-sa.json`) for `GOOGLE_APPLICATION_CREDENTIALS` and mount your key file there with `-v`.

### 4. Application Default Credentials (no key file)

If you already ran `gcloud auth application-default login`:

```bash
# Local
export GCS_BUCKET=your-test-bucket
export GCS_PREFIX=models
export MODELS_DIR=./models
poetry run python upload_models.py

# Docker: mount ADC from host
docker run --rm \
  -e GCS_BUCKET=your-test-bucket \
  -e GCS_PREFIX=test-models \
  -v ~/.config/gcloud:/root/.config/gcloud:ro \
  arthur-model-upload-gcp:test
```

Note: the distroless image runs as `nonroot` (uid 65532), so the default `~/.config/gcloud` mount may not be readable. Prefer a service account key file for Docker unless you configure the image for ADC.

## Local development

```bash
poetry install

# Download models locally
poetry run python download_models.py --output-dir ./models --workers 4

# Upload to GCS (requires credentials)
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
export GCS_BUCKET=your-bucket
export GCS_PREFIX=models
export MODELS_DIR=./models
poetry run python upload_models.py
```

## Image registry

Prefer **Artifact Registry** for new projects; GCR is still supported. Use the same image URL in the Cloud Run Job (or K8s Job) that you push to.
