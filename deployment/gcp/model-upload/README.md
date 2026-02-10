# Arthur Model Upload - GCP (Cloud Run + GCS)

A Cloud Run Job that uploads pre-downloaded ML models to a Google Cloud Storage (GCS) bucket. Use this when running Arthur on GCP and you want models stored in GCS instead of S3 or a local PVC.

> **Note**: For AWS S3, see `../../ecs/model-upload/`. For OpenShift/Kubernetes with PVC, see `../../k8s/model-upload-oc/`.

## Overview
This is the **GCS version** that:
1. Downloads ML models from Hugging Face during Docker build
2. When run as a Cloud Run job, copies all models to a GCS bucket
3. Cloud Run services (like genai-engine) can mount the GCS bucket as a storage volume to access models

## Prerequisites

- **GCS bucket** for model storage (create in same or different project)
- **Service account** with:
  - `roles/storage.objectCreator` (or `roles/storage.admin`) on the bucket
  - For Cloud Run: used as the job’s service account

## Build and push image
First, regenerate the poetry.lock file:
```bash
rm -rf poetry.lock && poetry lock
```

Then build and push to Docker Hub:
```bash
docker build --platform linux/amd64 -t genai-engine-models-gcp:<genai_engine_models_version> .

# Tag for Docker Hub (arthurplatform organization)
docker tag genai-engine-models-gcp:<genai_engine_models_version> arthurplatform/genai-engine-models-gcp:<genai_engine_models_version>

# Push to Docker Hub (requires: docker login)
docker push arthurplatform/genai-engine-models-gcp:<genai_engine_models_version>
```

## Create and run the Cloud Run Job
### Run genai-engine-models-gcp container
1. Mount the GCS bucket as a storage volume on the Cloud Run service: https://docs.cloud.google.com/run/docs/configuring/services/cloud-storage-volume-mounts
2. Run the model upload container with the below envars:
  ```
    GCS_PREFIX: /gcs/model-storage
  ```

### Run genai-engine container
Adjust the below GenAI envars accordingly:
  ```
  # specify the mount location
  # `MODEL_STORAGE_PATH` must be set to `/home/nonroot{GCS_PREFIX specified to model-upload container}`.
  MODEL_STORAGE_PATH=/home/nonroot/gcs/model-storage
  # set HF models to offline mode
  HF_HUB_OFFLINE=1
  ```

## Local testing
Use `docker-compose.local.yml`: See the comments in the script for the usage deatils.
```
docker compose -f docker-compose.local.yml up
```
