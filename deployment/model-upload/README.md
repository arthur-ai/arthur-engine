# Arthur Model Upload

Uploads pre-downloaded ML models to cloud storage for airgapped deployments. Supports three backends:

| Backend | Storage | Image suffix | Deployment |
|---------|---------|--------------|------------|
| `s3` | AWS S3 | `-s3` | ECS Fargate |
| `gcs` | Google Cloud Storage | `-gcp` | Cloud Run |
| `pvc` | Kubernetes PVC | `-k8s` | Helm / raw K8s |

## Build Images

```bash
# ECS / S3
docker build --build-arg BACKEND=s3 --target runtime-s3 \
  -t arthurplatform/genai-engine-models-s3:<version> .

# GCP / GCS
docker build --build-arg BACKEND=gcs --target runtime-gcs \
  -t arthurplatform/genai-engine-models-gcs:<version> .

# K8s / PVC
docker build --build-arg BACKEND=pvc --target runtime-pvc \
  -t arthurplatform/genai-engine-models-k8s:<version> .
```

## Deploy

### ECS (S3)

Fill in the variables and register the task definition:

```bash
export ECR_IMAGE_URI=<account>.dkr.ecr.<region>.amazonaws.com/genai-engine-models-s3:<version>
export EXECUTION_ROLE_ARN=arn:aws:iam::<account>:role/ecsTaskExecutionRole
export TASK_ROLE_ARN=arn:aws:iam::<account>:role/arthur-model-upload-role
export S3_BUCKET=my-models-bucket
export S3_PREFIX=models
export AWS_REGION=us-east-1

envsubst < ecs/task-definition.json > task-definition-resolved.json
aws ecs register-task-definition --cli-input-json file://task-definition-resolved.json

aws ecs run-task \
  --cluster <cluster> \
  --task-definition arthur-model-upload \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[<subnet>],securityGroups=[<sg>],assignPublicIp=ENABLED}"
```

**IAM permissions required** (task role): `s3:PutObject`, `s3:GetObject`, `s3:HeadObject`, `s3:ListBucket`

### GCP (GCS)

Fill in `gcp/cloud-run-job.yaml` then:

```bash
gcloud run jobs replace gcp/cloud-run-job.yaml --region=<region>
gcloud run jobs execute arthur-model-upload --region=<region>
```

**IAM permissions required** (service account): `roles/storage.objectAdmin` on the bucket.

After upload, mount the GCS bucket as a storage volume on the genai-engine Cloud Run service and set:
```
MODEL_STORAGE_PATH=/home/nonroot/<GCS_PREFIX>
HF_HUB_OFFLINE=1
```

### K8s / OpenShift (PVC)

**Via Helm:**
```bash
helm install arthur-model-upload ./helm \
  --set image.tag=<version> \
  --set pvc.claimName=arthur-models-pvc
```

**Via raw manifests** (OpenShift):
```bash
kubectl apply -f k8s/01-pvc.yaml
kubectl apply -f k8s/02-serviceaccount.yaml
# Edit k8s/04-job.yaml to set the correct image version, then:
kubectl apply -f k8s/04-job.yaml
kubectl apply -f k8s/06-copy-config-job.yaml
```

## Environment Variables

| Variable | Backends | Required | Default | Description |
|----------|----------|----------|---------|-------------|
| `S3_BUCKET` | s3 | Yes | - | Target S3 bucket |
| `S3_PREFIX` | s3 | No | `` | S3 key prefix |
| `GCS_BUCKET` | gcs | Yes | - | Target GCS bucket |
| `GCS_PREFIX` | gcs | No | `` | GCS object prefix |
| `MODELS_DIR` | all | No | `/models` | Local models directory |
| `TARGET_DIR` | pvc | No | `/models-output` | PVC mount path |
| `LOG_LEVEL` | all | No | `INFO` | Logging level |

## Model Update Detection

`check_model_updates.py` checks whether HuggingFace models have changed since the last build by comparing commit hashes against `models-manifest.json`. Used by CI to skip unnecessary image rebuilds.

```bash
python check_model_updates.py             # check only
python check_model_updates.py --update    # check and update manifest
python check_model_updates.py --output github  # GitHub Actions format
```
