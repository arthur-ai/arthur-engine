# Arthur Model Upload - OpenShift PVC Version

An OpenShift/Kubernetes job that copies pre-downloaded ML models to a PersistentVolumeClaim for airgapped deployments.

## Overview

This is the **OpenShift PVC version** that:
1. Downloads ML models from Hugging Face during Docker build
2. When run as a Kubernetes Job, copies all models to a PersistentVolumeClaim
3. Other pods (like genai-engine) can mount the same PVC to access models
4. **No S3 required** - uses OpenShift native storage

## Differences from S3 Version

| Feature | S3 Version (`model-upload`) | PVC Version (`model-upload-oc`) |
|---------|---------------------------|--------------------------------|
| Storage | AWS S3 | PersistentVolumeClaim |
| Script | `upload_models.py` | `copy_models.py` |
| Dependencies | boto3, AWS credentials | Python stdlib only |
| Network | Requires S3 access | No external network needed |
| Use Case | AWS/cloud deployments | Airgapped OpenShift |

## Quick Start

### Build the Docker Image

**First, regenerate the poetry.lock file** (since dependencies changed):
```bash
poetry lock --no-update
```

Then build and push to Docker Hub:
```bash
# Build
docker build -t arthur-model-upload-oc:latest .

# Tag for Docker Hub (arthurplatform organization)
docker tag arthur-model-upload-oc:latest arthurplatform/arthur-model-upload-oc:latest

# Push to Docker Hub (requires: docker login)
docker push arthurplatform/arthur-model-upload-oc:latest
```

### Deploy to OpenShift

```bash
oc apply -f k8s-job-pvc.yaml
```

### Monitor

```bash
oc logs -l app=arthur-model-upload-oc -f
```

## Documentation

- **`AIRGAPPED_DEPLOYMENT.md`** - Complete guide for airgapped deployments
- **`PVC_DEPLOYMENT.md`** - Detailed PVC deployment instructions
- **`BUILD_INSTRUCTIONS.md`** - Image build instructions
- **`QUICK_REFERENCE.md`** - Quick reference guide

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SOURCE_DIR` | `/models` | Source directory in container |
| `TARGET_DIR` | `/models-output` | PVC mount point |
| `LOG_LEVEL` | `INFO` | Logging level |

## Architecture

```
Docker Image (arthur-model-upload-oc)
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
  └── /models/ (read models from PVC)
```

## See Also

For the S3 version, see `../model-upload/README.md`
