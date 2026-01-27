# Arthur Model Upload - Helm Chart

A Helm chart for deploying the Arthur Model Upload Job on Kubernetes or OpenShift. This chart replaces the ECS task definition and allows you to run the model upload job in any Kubernetes-compatible environment.

## Overview

This Helm chart deploys a Kubernetes Job that:
1. Runs a container with pre-downloaded ML models
2. Uploads all models to an S3-compatible object storage bucket
3. Supports multiple authentication methods (IRSA, secrets, IAM roles)

## Prerequisites

- Kubernetes 1.19+ or OpenShift 4.x+
- Helm 3.0+
- Access to the container image (default: `arthurplatform/arthur-model-upload`)
- S3 bucket or S3-compatible storage endpoint
- AWS credentials or IAM role with S3 permissions

## Installation

### Quick Start

```bash
# Install with default values
helm install model-upload ./deployment/helm/model-upload \
  --set s3.bucket=my-models-bucket \
  --set s3.prefix=models
```

### Using AWS IRSA (Recommended for EKS)

If you're using Amazon EKS with IAM Roles for Service Accounts (IRSA):

```bash
helm install model-upload ./deployment/helm/model-upload \
  --set s3.bucket=my-models-bucket \
  --set s3.prefix=models \
  --set serviceAccount.create=true \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::ACCOUNT_ID:role/arthur-model-upload-role \
  --set awsCredentials.create=false
```

**IAM Role Policy** (for the IRSA role):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:HeadObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-models-bucket",
        "arn:aws:s3:::my-models-bucket/*"
      ]
    }
  ]
}
```

### Using Kubernetes Secrets

For non-AWS environments or when IRSA is not available:

```bash
# Create a values file
cat > values-secret.yaml <<EOF
s3:
  bucket: my-models-bucket
  prefix: models
awsCredentials:
  create: true
  accessKeyId: "YOUR_ACCESS_KEY"
  secretAccessKey: "YOUR_SECRET_KEY"
  region: "us-east-1"
serviceAccount:
  create: true
  annotations: {}
EOF

# Install with secret-based credentials
helm install model-upload ./deployment/helm/model-upload \
  -f values-secret.yaml
```

### OpenShift Deployment

For OpenShift, enable SecurityContextConstraints:

```bash
helm install model-upload ./deployment/helm/model-upload \
  --set s3.bucket=my-models-bucket \
  --set s3.prefix=models \
  --set openshift.securityContextConstraints.enabled=true \
  --set serviceAccount.create=true \
  --set awsCredentials.create=true \
  --set awsCredentials.accessKeyId="YOUR_KEY" \
  --set awsCredentials.secretAccessKey="YOUR_SECRET"
```

## Configuration

### Required Values

| Parameter | Description | Example |
|-----------|-------------|---------|
| `s3.bucket` | S3 bucket name | `my-models-bucket` |

### Common Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `s3.prefix` | S3 key prefix | `""` |
| `image.repository` | Container image repository | `arthurplatform/arthur-model-upload` |
| `image.tag` | Container image tag | `""` (uses Chart.AppVersion) |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `modelsDir` | Models directory in container | `/models` |
| `logLevel` | Logging level | `INFO` |

### Job Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `job.backoffLimit` | Number of retries | `3` |
| `job.activeDeadlineSeconds` | Max job duration (seconds) | `3600` |
| `job.ttlSecondsAfterFinished` | Pod cleanup time | `86400` (24h) |

### Resource Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `resources.requests.cpu` | CPU request | `500m` |
| `resources.requests.memory` | Memory request | `1Gi` |
| `resources.limits.cpu` | CPU limit | `1000m` |
| `resources.limits.memory` | Memory limit | `2Gi` |

### AWS Authentication

Choose one of the following methods:

#### Method 1: AWS IRSA (EKS only)
```yaml
serviceAccount:
  create: true
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT_ID:role/arthur-model-upload-role
awsCredentials:
  create: false
```

#### Method 2: Kubernetes Secret
```yaml
awsCredentials:
  create: true
  accessKeyId: "AKIAIOSFODNN7EXAMPLE"
  secretAccessKey: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
  region: "us-east-1"
```

#### Method 3: IAM Instance Profile
```yaml
awsCredentials:
  create: false
serviceAccount:
  create: false
```
(Ensure nodes have IAM role with S3 permissions)

## Examples

### Complete Example with Custom Values

```yaml
# values.yaml
image:
  repository: my-registry.com/arthur-model-upload
  tag: "v1.0.0"
  pullPolicy: Always

s3:
  bucket: production-models-bucket
  prefix: models/v2

serviceAccount:
  create: true
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/model-upload-role

awsCredentials:
  create: false

job:
  backoffLimit: 5
  activeDeadlineSeconds: 7200  # 2 hours
  ttlSecondsAfterFinished: 172800  # 48 hours

resources:
  limits:
    cpu: "2000m"
    memory: "4Gi"
  requests:
    cpu: "1000m"
    memory: "2Gi"

nodeSelector:
  workload-type: batch

tolerations:
  - key: "batch-workload"
    operator: "Equal"
    value: "true"
    effect: "NoSchedule"
```

Install:
```bash
helm install model-upload ./deployment/helm/model-upload -f values.yaml
```

### Using S3-Compatible Storage (MinIO, etc.)

For non-AWS S3-compatible storage, you may need to set additional environment variables:

```yaml
extraEnv:
  - name: AWS_ENDPOINT_URL
    value: "https://minio.example.com"
  - name: AWS_ACCESS_KEY_ID
    valueFrom:
      secretKeyRef:
        name: minio-credentials
        key: access-key
  - name: AWS_SECRET_ACCESS_KEY
    valueFrom:
      secretKeyRef:
        name: minio-credentials
        key: secret-key
```

## Monitoring

### Check Job Status

```bash
# Get job status
kubectl get job arthur-model-upload

# View job logs
kubectl logs -l app.kubernetes.io/name=arthur-model-upload

# Get pod status
kubectl get pods -l app.kubernetes.io/name=arthur-model-upload
```

### View Logs

```bash
# Get logs from the job pod
kubectl logs -l app.kubernetes.io/name=arthur-model-upload --tail=100 -f
```

## Troubleshooting

### Job Fails Immediately

1. **Check image pull**: Ensure the image is accessible
   ```bash
   kubectl describe job arthur-model-upload
   ```

2. **Check credentials**: Verify AWS credentials are correct
   ```bash
   kubectl get secret arthur-model-upload-aws-credentials -o yaml
   ```

3. **Check S3 permissions**: Ensure the IAM role/user has S3 write permissions

### Job Runs But Upload Fails

1. **Check logs**:
   ```bash
   kubectl logs -l app.kubernetes.io/name=arthur-model-upload
   ```

2. **Verify S3 bucket exists and is accessible**:
   ```bash
   aws s3 ls s3://my-models-bucket
   ```

3. **Check network connectivity** (if using VPC endpoints or private S3)

### OpenShift-Specific Issues

1. **SecurityContextConstraints**: Ensure SCC is created and bound to service account
   ```bash
   oc get scc arthur-model-upload-scc
   oc describe scc arthur-model-upload-scc
   ```

2. **Image pull secrets**: If using private registry, configure image pull secrets
   ```yaml
   imagePullSecrets:
     - name: registry-secret
   ```

## Uninstallation

```bash
helm uninstall model-upload
```

**Note**: Completed jobs are kept by default for 24 hours (`ttlSecondsAfterFinished`). To clean up immediately:

```bash
kubectl delete job arthur-model-upload
kubectl delete pods -l app.kubernetes.io/name=arthur-model-upload
```

## Migration from ECS

### Key Differences

| ECS | Kubernetes/Helm |
|-----|-----------------|
| Task Definition | Job + ConfigMap/Values |
| Task Role | ServiceAccount with IRSA or Secret |
| Execution Role | Not needed (handled by cluster) |
| CloudWatch Logs | kubectl logs or cluster logging |
| Fargate | Any Kubernetes node |
| Run once | Job with backoffLimit |

### Migration Steps

1. **Build and push image** (same as ECS):
   ```bash
   docker build -t arthur-model-upload:latest .
   docker tag arthur-model-upload:latest my-registry/arthur-model-upload:latest
   docker push my-registry/arthur-model-upload:latest
   ```

2. **Set up IAM role** (if using IRSA):
   - Create IAM role with S3 permissions
   - Annotate service account with role ARN

3. **Install Helm chart**:
   ```bash
   helm install model-upload ./deployment/helm/model-upload \
     --set s3.bucket=my-bucket \
     --set image.repository=my-registry/arthur-model-upload
   ```

4. **Monitor job**:
   ```bash
   kubectl get job -w
   kubectl logs -l app.kubernetes.io/name=arthur-model-upload -f
   ```

## Additional Resources

- [Kubernetes Jobs Documentation](https://kubernetes.io/docs/concepts/workloads/controllers/job/)
- [OpenShift Security Context Constraints](https://docs.openshift.com/container-platform/latest/authentication/managing-security-context-constraints.html)
- [AWS IRSA Documentation](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
