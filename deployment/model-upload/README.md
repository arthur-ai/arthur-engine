# Arthur Model Upload

Uploads pre-downloaded ML models to cloud storage for air-gapped deployments. Supports three backends:

| Backend | Storage | Image suffix | Deployment |
|---------|---------|--------------|------------|
| `s3` | AWS S3 | `-s3` | ECS |
| `gcs` | Google Cloud Storage | `-gcs` | Cloud Run with mounted GCS |
| `pvc` | Kubernetes PVC | `-fs` | Helm / raw K8s |
| `efs` | AWS EFS | `-fs` | ECS |

## Build Images

```bash
# ECS + S3 HTTP retrieval
docker build --build-arg BACKEND=s3 --target runtime-s3 \
  -t arthurplatform/genai-engine-models-s3:<version> .

# GCP + GCS mount
docker build --build-arg BACKEND=gcs --target runtime-gcs \
  -t arthurplatform/genai-engine-models-gcs:<version> .

# K8s + PVC mount or ECS + EFS mount
docker build --build-arg BACKEND=fs --target runtime-fs \
  -t arthurplatform/genai-engine-models-fs:<version> .
```

## Deploy

### S3

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

After upload, set the following envar:
```
MODEL_REPOSITORY_URL=https://s3-object
```

### GCS

Fill in `gcp/cloud-run-job.yaml` then:

```bash
gcloud run jobs replace gcp/cloud-run-job.yaml --region=<region>
gcloud run jobs execute arthur-model-upload --region=<region>
```

**IAM permissions required** (service account): `roles/storage.objectAdmin` on the bucket.

After upload, mount the GCS bucket as a storage volume on the genai-engine Cloud Run service and set the following envars:
```
MODEL_STORAGE_PATH=/home/nonroot/<GCS_PREFIX>
HF_HUB_OFFLINE=1
```

### FS

The `fs` backend writes the pre-downloaded models to a mounted filesystem (a Kubernetes PVC or an AWS EFS volume) with a one-time job. The genai-engine pods then mount that same filesystem **read-only** and load models from it, so models are uploaded once and shared across all replicas.

> **PVC vs. EFS on EKS:** these are not alternatives — on EKS, EFS is what *backs* a shared PVC. An EBS-backed PVC is `ReadWriteOnce` (single node/AZ) and cannot be shared across genai-engine replicas. To share models across multiple pods/AZs you need a `ReadWriteMany` PVC, and on AWS that means backing it with EFS via the EFS CSI driver. See [AWS EKS + EFS](#aws-eks--efs) below.

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

After upload, mount the PVC/EFS to the pod/task and set the following envars:
```
MODEL_STORAGE_PATH=/home/nonroot/<PREFIX>
HF_HUB_OFFLINE=1
```

#### AWS EKS + EFS

Use EFS when you run **more than one genai-engine replica** (HPA, multi-AZ). EFS gives you a `ReadWriteMany` volume that the upload job writes once and every engine pod mounts read-only. Models are read into memory at pod startup, so EFS latency only affects cold start, not inference.

**1. Install the EFS CSI driver** (once per cluster). Easiest via the EKS add-on:

```bash
# Associate an IAM OIDC provider if you haven't already
eksctl utils associate-iam-oidc-provider --cluster <cluster> --approve

# Create the IAM role the driver uses to manage access points
eksctl create iamserviceaccount \
  --name efs-csi-controller-sa \
  --namespace kube-system \
  --cluster <cluster> \
  --role-name AmazonEKS_EFS_CSI_DriverRole \
  --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEFSCSIDriverPolicy \
  --approve

# Install the add-on
eksctl create addon --name aws-efs-csi-driver --cluster <cluster> \
  --service-account-role-arn arn:aws:iam::<account>:role/AmazonEKS_EFS_CSI_DriverRole --force
```

**2. Create the EFS filesystem and mount targets.** The filesystem must be reachable from the worker nodes, so create a mount target in each node subnet with a security group that allows inbound NFS (TCP 2049) from the nodes' security group.

```bash
# Create the filesystem (Elastic throughput recommended — see note below)
aws efs create-file-system \
  --performance-mode generalPurpose \
  --throughput-mode elastic \
  --encrypted \
  --tags Key=Name,Value=arthur-models \
  --query FileSystemId --output text
# -> fs-xxxxxxxxxxxxxxxxx

# Allow NFS from the node security group
aws ec2 authorize-security-group-ingress \
  --group-id <efs-sg> --protocol tcp --port 2049 --source-group <node-sg>

# One mount target per node subnet
aws efs create-mount-target --file-system-id fs-xxxx --subnet-id <subnet-az-a> --security-groups <efs-sg>
aws efs create-mount-target --file-system-id fs-xxxx --subnet-id <subnet-az-b> --security-groups <efs-sg>
```

> Use **Elastic** (or provisioned) throughput, not Bursting. Model loading is many small-file reads and a low-baseline Bursting filesystem can throttle at startup.

**3. Create a StorageClass and a `ReadWriteMany` PVC.** Dynamic provisioning (EFS access points):

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-models
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap          # one EFS access point per PVC
  fileSystemId: fs-xxxxxxxxxxxxxxxxx
  directoryPerms: "700"
  uid: "1000760000"                 # match the upload job's runAsUser
  gid: "1000760000"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: arthur-models-pvc
  labels:
    app: arthur-models
spec:
  accessModes:
    - ReadWriteMany                 # required for sharing across pods/AZs
  storageClassName: efs-models
  resources:
    requests:
      storage: 25Gi                 # EFS is elastic; this is a nominal request
```

This replaces `k8s/01-pvc.yaml` (which defaults to `ReadWriteOnce` and the cluster's default StorageClass). The genai-engine pods must run with a UID matching the access point (`uid`/`gid` above) so they can read the files.

**4. Run the upload job** against the EFS-backed PVC:

```bash
kubectl apply -f <the StorageClass + PVC above>
kubectl apply -f k8s/02-serviceaccount.yaml
# Edit k8s/04-job.yaml to set the correct image version, then:
kubectl apply -f k8s/04-job.yaml
kubectl apply -f k8s/06-copy-config-job.yaml

# Confirm completion
kubectl wait --for=condition=complete job/arthur-genai-engine-models-k8s --timeout=600s
```

**5. Mount the volume into genai-engine** (read-only) and point the engine at it. Add the PVC volume to the genai-engine deployment and set:

```
MODEL_STORAGE_PATH=/home/nonroot/models-output
HF_HUB_OFFLINE=1
```

```yaml
# in the genai-engine pod spec
volumes:
  - name: models
    persistentVolumeClaim:
      claimName: arthur-models-pvc
containers:
  - name: genai-engine
    volumeMounts:
      - name: models
        mountPath: /home/nonroot/models-output
        readOnly: true
```

> The genai-engine Helm chart does not yet template a model PVC mount — it only wires `MODEL_REPOSITORY_URL` (the S3 path). Until it does, add the volume/volumeMount above to the deployment (e.g. via a patch/overlay) alongside the two env vars.

**IAM / networking checklist:**
- EFS CSI driver IAM role attached (`AmazonEFSCSIDriverPolicy`).
- EFS security group allows inbound TCP 2049 from the node security group.
- A mount target exists in every subnet where genai-engine / the upload job can be scheduled.
- The access point `uid`/`gid` matches the runAsUser of both the upload job and the genai-engine pods.

## Environment Variables

| Variable | Backends | Required | Default | Description |
|----------|----------|----------|---------|-------------|
| `S3_BUCKET` | s3 | Yes | - | Target S3 bucket |
| `S3_PREFIX` | s3 | No | `` | S3 key prefix |
| `GCS_BUCKET` | gcs | Yes | - | Target GCS bucket |
| `GCS_PREFIX` | gcs | No | `` | GCS object prefix |
| `MODELS_DIR` | all | No | `/models` | Local models directory |
| `TARGET_DIR` | pvc/efs | No | `/models-output` | PVC/EFS mount path |
| `LOG_LEVEL` | all | No | `INFO` | Logging level |

## Model Update Detection

`check_model_updates.py` checks whether Hugging Face models have changed since the last build by comparing commit hashes against `models-manifest.json`. Used by CI to skip unnecessary image rebuilds.

```bash
python check_model_updates.py             # check only
python check_model_updates.py --update    # check and update manifest
python check_model_updates.py --output github  # GitHub Actions format
```
