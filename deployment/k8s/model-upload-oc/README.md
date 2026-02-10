# Arthur Model Upload - Kubernetes/OpenShift PVC Version

An Kubernetes/OpenShift job that copies pre-downloaded ML models to a PersistentVolumeClaim for airgapped deployments.

> **Note**: For AWS S3, see `../../ecs/model-upload/`. For GCS, see `../../gcp/model-upload/`.

## Overview

This is the **OpenShift PVC version** that:
1. Downloads ML models from Hugging Face during Docker build
2. When run as a Kubernetes Job, copies all models to a PersistentVolumeClaim
3. Other pods (like genai-engine) can mount the same PVC to access models
4. Uses Kubernetes/OpenShift native storage

## Quick Start

### Build the Docker Image

First, regenerate the poetry.lock file:
```bash
rm -rf poetry.lock && poetry lock
```

Then build and push to Docker Hub:
```bash
# Build for Linux/AMD64 (required for Kubernetes/OpenShift)
docker build --platform linux/amd64 -t genai-engine-models-k8s:<genai_engine_models_version> .

# Tag for Docker Hub (arthurplatform organization)
docker tag genai-engine-models-k8s:<genai_engine_models_version> arthurplatform/genai-engine-models-k8s:<genai_engine_models_version>

# Push to Docker Hub (requires: docker login)
docker push arthurplatform/genai-engine-models-k8s:<genai_engine_models_version>
```

## Test the image locally
```bash
docker compose -f docker-compose.local.yml up
```

### Deploy to OpenShift

Update Apply the Kubernetes manifests in order:

```bash
oc apply -f 01-pvc.yaml
oc apply -f 02-serviceaccount.yaml
# Replace <genai_engine_models_version> with the version you want to deploy in 04-job.yaml
oc apply -f 04-job.yaml
oc apply -f 06-copy-config-job.yaml
```

### Monitor

```bash
oc logs -l app=arthur-genai-engine-models-k8s -f
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SOURCE_DIR` | `/models` | Source directory in container |
| `TARGET_DIR` | `/models-output` | PVC mount point |
| `LOG_LEVEL` | `INFO` | Logging level |

## Architecture

```
Docker Image (genai-engine-models-k8s)
  └── /models/ (pre-downloaded models)
       │
       │ Job runs: copy_models.py
       ▼
PersistentVolumeClaim
  └── /models-output/ (copied models)
       │
       │ Other pods mount PVC
       ▼
genai-engine Pods
  └── /home/nonroot/models-output/ (read models from PVC)
```

## GenAI Engine Configurations
Refer to the Docker Compose example below.
`MODEL_STORAGE_PATH` must be set to `/home/nonroot/{TARGET_DIR specified to model-upload container}`.
```
    environment:
      - MODEL_STORAGE_PATH=/home/nonroot/model-storage
      - HF_HUB_OFFLINE=1
    volumes:
      # Mount models directory to persist pre-downloaded models across container restarts
      - ../deployment/k8s/model-upload-oc/model-storage:/home/nonroot/model-storage
```
