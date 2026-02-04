# ECS Model Upload Deployment

This directory contains ECS-specific deployment configuration for the unified model upload job.

## About

The model upload code is located at `/model-upload/` (repository root). This directory only contains ECS deployment configuration.

## Files

- `task-definition.json` - ECS Fargate task definition for S3 model upload

## Usage

### Prerequisites

1. Build and push the unified S3 image:
   ```bash
   cd ../../model-upload
   ./build.sh --version <VERSION> --push s3
   ```

2. Push image to your ECR repository:
   ```bash
   # Tag for ECR
   docker tag arthurplatform/genai-engine-models:<VERSION>-s3 \
     <AWS_ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/arthur-model-upload:<VERSION>

   # Push to ECR
   aws ecr get-login-password --region <REGION> | \
     docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com
   docker push <AWS_ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/arthur-model-upload:<VERSION>
   ```

### Deploy Task Definition

1. Replace placeholders in `task-definition.json`:
   - `${ECR_IMAGE_URI}` - Your ECR image URI
   - `${EXECUTION_ROLE_ARN}` - ECS task execution role ARN
   - `${TASK_ROLE_ARN}` - ECS task role ARN (needs S3 write permissions)
   - `${S3_BUCKET}` - Target S3 bucket name
   - `${S3_PREFIX}` - S3 key prefix (optional)
   - `${AWS_REGION}` - AWS region

2. Register the task definition:
   ```bash
   aws ecs register-task-definition --cli-input-json file://task-definition.json
   ```

### Run Task

```bash
aws ecs run-task \
  --cluster <CLUSTER_NAME> \
  --task-definition arthur-model-upload \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[<SUBNET_IDs>],securityGroups=[<SG_IDs>],assignPublicIp=ENABLED}"
```

## Environment Variables

The task uses the unified `upload_models.py` script with the following environment variables:

- `STORAGE_BACKEND=s3` - Use S3 backend
- `S3_BUCKET` - Target S3 bucket
- `S3_PREFIX` - S3 key prefix (optional)
- `LOG_LEVEL=INFO` - Logging level

## Image Tags

Images follow the naming convention:
- `arthurplatform/genai-engine-models:<VERSION>-s3`
- Example: `arthurplatform/genai-engine-models:2.1.343-s3`

## IAM Permissions

The task role needs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::YOUR_BUCKET_NAME/*",
        "arn:aws:s3:::YOUR_BUCKET_NAME"
      ]
    }
  ]
}
```

## Related

- [Unified Model Upload Code](/model-upload/) - Source code and Dockerfile
- [GCP Deployment](../gcp/model-upload/) - GCS deployment
- [K8s Deployment](../k8s/model-upload-oc/) - Kubernetes deployment
