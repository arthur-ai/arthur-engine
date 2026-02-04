# GCP Cloud Run Model Upload Deployment

This directory contains GCP Cloud Run-specific deployment configuration for the unified model upload job.

## About

The model upload code is located at `/model-upload/` (repository root). This directory only contains GCP deployment configuration.

## Files

- `cloud-run-job.yaml` - Cloud Run Job definition for GCS model upload

## Usage

### Prerequisites

1. Build and push the unified GCS image:
   ```bash
   cd ../../model-upload
   ./build.sh --version <VERSION> --push gcs
   ```

2. Push image to GCP Container Registry or Artifact Registry:
   ```bash
   # For Artifact Registry
   docker tag arthurplatform/genai-engine-models:<VERSION>-gcs \
     <REGION>-docker.pkg.dev/<PROJECT_ID>/<REPOSITORY>/arthur-model-upload:<VERSION>

   docker push <REGION>-docker.pkg.dev/<PROJECT_ID>/<REPOSITORY>/arthur-model-upload:<VERSION>
   ```

### Deploy Cloud Run Job

1. Replace placeholders in `cloud-run-job.yaml`:
   - `PROJECT_NUMBER` - Your GCP project number
   - `REGION` - GCP region (e.g., `us-central1`)
   - `VERSION` - Image version tag
   - `BUCKET_NAME` - Target GCS bucket name
   - `SERVICE_ACCOUNT_EMAIL` - Service account email with GCS write permissions

2. Deploy the job:
   ```bash
   gcloud run jobs replace cloud-run-job.yaml --region=<REGION>
   ```

### Run Job

```bash
# Execute the job
gcloud run jobs execute arthur-model-upload --region=<REGION>

# View logs
gcloud run jobs executions logs <EXECUTION_ID> --region=<REGION>

# List executions
gcloud run jobs executions list --job arthur-model-upload --region=<REGION>
```

## Environment Variables

The job uses the unified `upload_models.py` script with the following environment variables:

- `STORAGE_BACKEND=gcs` - Use GCS backend
- `GCS_BUCKET` - Target GCS bucket name
- `GCS_PREFIX=models` - GCS object prefix
- `MODELS_DIR=/models` - Source directory in container
- `LOG_LEVEL=INFO` - Logging level

## Image Tags

Images follow the naming convention:
- `arthurplatform/genai-engine-models:<VERSION>-gcs`
- Example: `arthurplatform/genai-engine-models:2.1.343-gcs`

## IAM Permissions

The service account needs:

```yaml
roles/storage.objectAdmin  # On the target bucket
```

Or specific permissions:
- `storage.objects.create`
- `storage.objects.get`
- `storage.objects.list`

## Configuration

Create the service account and grant permissions:

```bash
# Create service account
gcloud iam service-accounts create arthur-model-upload \
  --display-name "Arthur Model Upload"

# Grant storage permissions
gsutil iam ch serviceAccount:arthur-model-upload@PROJECT_ID.iam.gserviceaccount.com:objectAdmin \
  gs://YOUR_BUCKET_NAME

# Allow Cloud Run to use the service account
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member serviceAccount:arthur-model-upload@PROJECT_ID.iam.gserviceaccount.com \
  --role roles/run.invoker
```

## Related

- [Unified Model Upload Code](/model-upload/) - Source code and Dockerfile
- [ECS Deployment](../ecs/model-upload/) - AWS ECS deployment
- [K8s Deployment](../k8s/model-upload-oc/) - Kubernetes deployment
