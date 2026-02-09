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
1. Mount the GCS bucket as a storage volume on the Cloud Run service: https://docs.cloud.google.com/run/docs/configuring/services/cloud-storage-volume-mounts
2. Adjust the below GenAI envars accordingly:
  ```
  # specify the mount location
  MODEL_STORAGE_PATH=/home/nonroot/gcs/models
  # set HF models to offline mode
  HF_HUB_OFFLINE=1
  ```

## Local testing
Use `docker-compose.local.yml`: See the comments in the script for the usage deatils.
```
docker compose -f docker-compose.local.yml up
```
