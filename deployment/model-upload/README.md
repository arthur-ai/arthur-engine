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

The `fs` backend writes the pre-downloaded models to a mounted filesystem (a Kubernetes PVC or an AWS EFS volume) with a one-time job. The genai-engine pods then mount that same filesystem and load models from it, so models are uploaded once and shared across all replicas. The mount must be **read-write**: the HuggingFace loaders write `.lock`/cache files under the mount even with `HF_HUB_OFFLINE=1`, so a read-only mount fails with `[Errno 30] Read-only file system`.

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

Use EFS when you run **more than one genai-engine replica** (HPA, multi-AZ). EFS gives you a `ReadWriteMany` volume that the upload job writes once and every engine pod mounts read-write (the loaders write lock/cache files even offline). Models are read into memory at pod startup, so EFS latency only affects cold start, not inference.

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

**2. Create the EFS filesystem and mount targets.** The filesystem must be reachable from the worker nodes, so create a mount target in **every AZ your nodes can run in**, with a security group that allows inbound NFS (TCP 2049) from the nodes' security group.

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

# EFS allows exactly ONE mount target per AZ. Create one in every AZ your nodes can run in,
# passing any subnet in that AZ (a second create in the same AZ fails with MountTargetConflict).
aws efs create-mount-target --file-system-id fs-xxxx --subnet-id <subnet-az-a> --security-groups <efs-sg>
aws efs create-mount-target --file-system-id fs-xxxx --subnet-id <subnet-az-b> --security-groups <efs-sg>
aws efs create-mount-target --file-system-id fs-xxxx --subnet-id <subnet-az-c> --security-groups <efs-sg>
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
  uid: "65532"                      # the genai-engine image's nonroot user
  gid: "65532"
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

This replaces `k8s/01-pvc.yaml` (which defaults to `ReadWriteOnce` and the cluster's default StorageClass). With `efs-ap` provisioning the access point **squashes all reads and writes to its `uid`/`gid`**, so neither the upload job nor the genai-engine pods need a matching `runAsUser` for access to work. Set `uid`/`gid` to `65532` (the genai-engine image's `nonroot` user) so on-disk ownership is sensible and consistent with [`README-regular-pvc.md`](README-regular-pvc.md).

**4. Run the upload job** against the EFS-backed PVC, then the config-copy job. Run the config-copy job **only after the upload job completes** — it copies `gliner_config.json` (written by the upload job) to `config.json`, so applying both together races and the copy fails with `gliner_config.json not found`:

```bash
kubectl apply -f <the StorageClass + PVC above>
kubectl apply -f k8s/02-serviceaccount.yaml

# Edit k8s/04-job.yaml to set the correct image version, then run the upload and wait for it:
kubectl apply -f k8s/04-job.yaml
kubectl wait --for=condition=complete job/arthur-genai-engine-models-k8s --timeout=600s

# Only now run the GLiNER config-copy job, and wait for it too:
kubectl apply -f k8s/06-copy-config-job.yaml
kubectl wait --for=condition=complete job/copy-gliner-config --timeout=300s
```

**5. Mount the volume into genai-engine** (read-write) and point the engine at it. Add the PVC volume to the genai-engine deployment and set:

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
        readOnly: false  # loaders write .lock/cache files even offline
```

> The genai-engine Helm chart supports this mount natively via the optional `modelPVC` values (the online/offline toggle, off by default): `--set modelPVC.enabled=true --set modelPVC.claimName=arthur-models-pvc --set modelPVC.mountPath=/home/nonroot/models-output`. The chart then adds the volume/volumeMount (read-write) and sets `MODEL_STORAGE_PATH` + `HF_HUB_OFFLINE=1` for you. Provision the EFS-backed PVC with the steps in this section (StorageClass + `ReadWriteMany` PVC above).

**IAM / networking checklist:**
- EFS CSI driver IAM role attached (`AmazonEFSCSIDriverPolicy`).
- EFS security group allows inbound TCP 2049 from the node security group.
- A mount target exists in every AZ where genai-engine / the upload job can be scheduled.
- The access point `uid`/`gid` is set to `65532` (the genai-engine `nonroot` user). Because the access point squashes all I/O to this identity, the upload job and engine pods do **not** need a matching `runAsUser`.

> **Transient mount error on freshly-provisioned nodes.** On EKS Auto Mode / Karpenter, the first pod to schedule onto a brand-new node may fail to mount for ~10–30s with `driver name efs.csi.aws.com not found in the list of registered CSI drivers`, until the `efs-csi-node` DaemonSet registers the driver on that node. It self-heals and the pod mounts — no action needed.

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

## AI Bill of Materials (AI-BOM)

`generate_aibom.py` produces a **CycloneDX 1.6** AI-BOM documenting the bundled ML models —
the guardrail and embedding models Arthur ships (prompt-injection, toxicity, profanity, PII,
relevance/NLI, claim-classifier embedding). The container SBOM (Trivy) covers OS and Python
packages but not these HuggingFace model weights; this file is the missing bill of materials
for the models themselves.

Each model is a `machine-learning-model` component carrying its pinned HuggingFace commit
SHA (`version` + `purl`), SHA-256 file hashes, license, task, and the Arthur check it powers.
The model list is reused from `download_models.DEFAULT_MODELS` and the commit SHAs from
`models-manifest.json` — nothing is re-hardcoded.

```bash
# Catalog copy — HuggingFace LFS hashes + license/task, no weight download
python generate_aibom.py --manifest models-manifest.json -o aibom.cdx.json

# Committed copy — as above, but stable across releases (no timestamp, no engine version)
python generate_aibom.py --no-timestamp --no-engine-version \
  --manifest models-manifest.json -o aibom.cdx.json

# From downloaded files — SHA-256 computed locally over the exact bytes that ship
python generate_aibom.py --models-dir /models --manifest models-manifest.json -o /models/aibom.cdx.json

# Offline — identity + commit SHA only, no network
python generate_aibom.py --offline -o aibom.cdx.json
```

**Where it is published (all built at build time):**

- **`s3://arthur-cft`** — Arthur's public catalog, alongside the CloudFormation templates.
  On each `Increment arthur-engine version` commit, the `push-aibom` job in
  `arthur-engine-workflow.yml` publishes to
  `https://arthur-cft.s3.us-east-2.amazonaws.com/arthur-engine/aibom/<version>/aibom.cdx.json`
  (and `.../aibom/latest/aibom.cdx.json`).
- **Deployment model storage** — the image `downloader` stage writes `aibom.cdx.json` into
  `/models`, so `upload_models.py` ships it to your S3/GCS/FS bucket next to the model files.
- **Repo** — the committed `aibom.cdx.json` (diffable model inventory) is regenerated by the
  model-upload build workflows and committed back to the branch.
  Generated with `--no-engine-version`, so it carries no `metadata.component.version`: this
  copy documents the bundled models, which do not change with the engine version, and
  stamping it made the file churn on every release. The two release-specific copies above
  keep the version. `--engine-version` defaults to `$VERSION`, which CI sets, so the flag is
  required — dropping `--engine-version` is not enough.
