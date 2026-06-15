# Terraform: EFS-backed models PVC for EKS Auto Mode

Provisions an **EFS-backed `ReadWriteMany` PersistentVolumeClaim** that the Arthur
genai-engine uses to share ML model binaries across replicas on an **EKS Auto Mode**
cluster. This is the Terraform equivalent of the manual `aws` / `eksctl` / `kubectl`
runbook in [`../../model-upload/README.md`](../../model-upload/README.md) (section
"AWS EKS + EFS"), and it follows the naming/tagging conventions of the existing
CloudFormation stacks under [`../../cloudformation/`](../../cloudformation/).

See [`DESIGN.md`](./DESIGN.md) for why it is built this way (static vs. dynamic
provisioning, Pod Identity vs. IRSA, Auto Mode specifics).

## What it creates

| Layer | Resources |
|-------|-----------|
| **EFS** | Encrypted filesystem (elastic throughput), one mount target per subnet, an access point pinned to uid/gid `1000760000` rooted at `/models` |
| **Networking** | Security group allowing inbound NFS (TCP 2049) from the Auto Mode cluster security group |
| **IAM** | Role for the EFS CSI driver + an EKS **Pod Identity** association (`kube-system/efs-csi-controller-sa`) |
| **Add-on** | The `aws-efs-csi-driver` EKS add-on (not bundled with Auto Mode) |
| **Kubernetes** | A non-default `efs-models` StorageClass, a statically-provisioned PV, and the `arthur-models-pvc` PVC (waits until `Bound`) |

After `apply`, you have a `Bound` PVC ready for the existing model-upload job, and the
uploaded models survive PVC delete/recreate (PV `reclaimPolicy: Retain`, EFS
`prevent_destroy`).

## Prerequisites

- An existing **EKS Auto Mode** cluster.
- Terraform `>= 1.5`, AWS provider `~> 5.0`, Kubernetes provider `~> 2.0`.
- AWS credentials with permission to create EFS, security groups, IAM roles, EKS add-ons, and Pod Identity associations.
- `kubectl` access to the cluster (for the upload job and verification).

## Usage

```bash
cd deployment/terraform/eks-efs-models
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars: cluster_name, region, vpc_id, subnet_ids, namespace

terraform init
terraform plan
terraform apply
```

Key inputs (see [`variables.tf`](./variables.tf) for all):

| Variable | Default | Notes |
|----------|---------|-------|
| `cluster_name`, `region`, `vpc_id`, `subnet_ids` | — | Required. `subnet_ids` = private/service subnets (one mount target each). |
| `arthur_resource_namespace` / `arthur_resource_name_suffix` | `arthur` / `""` | Names resources `${ns}-genai-engine${suffix}-…`. |
| `namespace` | `default` | Must match the upload job + genai-engine namespace. |
| `pvc_name` | `arthur-models-pvc` | Keep so the upload job manifests work unchanged. |
| `access_point_uid` / `gid` | `1000760000` | Must match the upload job and genai-engine `runAsUser`. |
| `existing_efs_file_system_id`, `byo_efs_security_group_ids`, `byo_efs_csi_role_arn` | empty | BYO overrides — skip creating that resource. |

### CI / long-running pipelines

`providers.tf` authenticates the kubernetes provider with a short-lived
`aws_eks_cluster_auth` token. For pipelines that run longer than the token TTL, switch
to the exec-plugin form:

```hcl
provider "kubernetes" {
  host                   = data.aws_eks_cluster.this.endpoint
  cluster_ca_certificate = base64decode(data.aws_eks_cluster.this.certificate_authority[0].data)
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", var.cluster_name]
  }
}
```

## After apply: upload models, then wire genai-engine

1. **Do NOT** apply `deployment/model-upload/k8s/01-pvc.yaml` on EKS — this module owns the PVC.
2. Run the one-time upload job into the now-`Bound` PVC (from `deployment/model-upload/`):
   ```bash
   kubectl -n <namespace> apply -f k8s/02-serviceaccount.yaml
   # edit k8s/04-job.yaml to set the genai-engine-models-fs image version, then:
   kubectl -n <namespace> apply -f k8s/04-job.yaml
   kubectl -n <namespace> apply -f k8s/06-copy-config-job.yaml
   kubectl -n <namespace> wait --for=condition=complete job/arthur-genai-engine-models-k8s --timeout=600s
   ```
3. Point genai-engine at the PVC. The genai-engine Helm chart supports this natively via the
   optional `modelPVC` values (off by default). Enable it:
   ```bash
   helm upgrade --install arthur-genai-engine ../../helm/genai-engine \
     --set modelPVC.enabled=true \
     --set modelPVC.claimName=arthur-models-pvc \
     --set modelPVC.mountPath=/home/nonroot/models-output
   ```
   The chart mounts the claim read-only and sets `MODEL_STORAGE_PATH` + `HF_HUB_OFFLINE=1`.
   No pod `securityContext` change is needed — the EFS access point's `posix_user` enforces
   uid/gid `1000760000` for all reads regardless of the pod's `runAsUser`. Run
   `terraform output model_upload_hint` for the exact flags.

## Verification

```bash
kubectl get csidrivers | grep efs.csi.aws.com                 # driver registered
kubectl -n kube-system get pods -l app=efs-csi-controller     # controller running (no AccessDenied in logs)
kubectl get sc                                                # efs-models present and NOT default
kubectl -n <namespace> get pvc arthur-models-pvc              # STATUS = Bound
```

## Teardown

```bash
terraform destroy
```

The EFS filesystem is protected by `lifecycle { prevent_destroy = true }` so the uploaded
models are not deleted by accident. To intentionally remove the filesystem, first remove that
`lifecycle` block from `main.tf` (or manage the filesystem out-of-band via
`existing_efs_file_system_id`), then destroy.

## Gotchas

- **uid/gid:** the EFS access point's `posix_user` overrides the client uid/gid, so reads/writes through it always use `1000760000` — the genai-engine pod needs no special `runAsUser`. The upload jobs (`04-job.yaml`, `06-copy-config-job.yaml`) still set `runAsUser: 1000760000` to satisfy OpenShift's restricted SCC; keep `access_point_uid/gid` aligned with them.
- **Mount target per subnet:** Auto Mode does not tightly control node placement, so create mount targets in **all** private subnets where pods may schedule.
- **StorageClass is not default:** the `efs-models` class must not displace the Auto Mode EBS default. This module never sets the default annotation.
- **Cold cluster ordering:** the kubernetes provider needs a reachable cluster. The PV/PVC `depend_on` the add-on, so a single `apply` works on an existing cluster; against a brand-new cluster, stage the AWS resources first (`-target`).
