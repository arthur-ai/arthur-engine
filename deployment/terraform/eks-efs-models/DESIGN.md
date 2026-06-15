# Design: EFS-backed models PVC for EKS Auto Mode

This document records *why* this Terraform module is shaped the way it is. For *how* to
use it, see [`README.md`](./README.md).

## Problem

Arthur GenAI Engine deploys to EKS via Helm. Each genai-engine replica needs several GB of
HuggingFace model binaries (toxicity, prompt-injection, embeddings, PII, …). Downloading them
per pod is slow and, in air-gapped environments, impossible. The intended pattern — documented
manually in [`../../model-upload/README.md`](../../model-upload/README.md) — is:

1. Upload the models **once** to a shared filesystem (a one-time Kubernetes Job).
2. Mount that filesystem **read-only** into every genai-engine replica.
3. The engine loads models into memory at startup (`MODEL_STORAGE_PATH` + `HF_HUB_OFFLINE=1`),
   so filesystem latency only affects cold start, not inference.

On AWS, "shared filesystem" means **EFS**: a `ReadWriteMany` volume. An EBS-backed PVC is
`ReadWriteOnce` (single node/AZ) and cannot be shared across replicas or AZs. This module turns
the manual EFS runbook into reproducible Terraform, targeting **EKS Auto Mode**.

## EKS Auto Mode specifics

1. **EFS CSI driver is not bundled.** Auto Mode includes managed EBS block storage and ships its
   own default StorageClasses, but the EFS CSI driver is **not** part of the managed control plane.
   It is installed explicitly as the `aws-efs-csi-driver` EKS add-on (`aws_eks_addon`).
2. **IAM via Pod Identity, not IRSA.** The add-on needs an IAM role with `AmazonEFSCSIDriverPolicy`.
   We use **EKS Pod Identity** (`aws_eks_pod_identity_association`) rather than IRSA: no OIDC provider
   to create/maintain, a simpler trust policy (`pods.eks.amazonaws.com`), and native Auto Mode support.
   A `byo_efs_csi_role_arn` escape hatch is provided for orgs that mandate IRSA.
3. **Node security group = cluster security group.** Auto Mode nodes attach to the EKS-created
   cluster security group, resolved as `data.aws_eks_cluster.this.vpc_config[0].cluster_security_group_id`.
   The EFS mount-target SG allows inbound TCP 2049 from exactly that SG (source-SG reference, not a
   VPC CIDR — tighter than the common blog approach).
4. **StorageClass must not be default.** Auto Mode provides a default EBS StorageClass. The `efs-models`
   class uses a distinct name and is never annotated `is-default-class`, so it never competes with it.

## Key decision: static provisioning (not dynamic `efs-ap`)

We provision the volume **statically**: Terraform creates the filesystem + a single access point +
a PV bound 1:1 to the PVC. The alternative — dynamic provisioning via a StorageClass with
`provisioningMode: efs-ap`, where the CSI driver creates an access point per PVC — was rejected for
this use case.

| | **Static (chosen)** | Dynamic (`efs-ap`) |
|---|---|---|
| Intent | One shared write-once/read-many volume | Many independent claims |
| Access point | Declared in Terraform; survives PVC delete | Created by CSI per PVC; `Delete` reclaim can orphan/destroy it |
| uid/gid + path | Deterministic, Terraform-owned | Set via StorageClass params at claim time |
| Risk to uploaded models | Low — PV `Retain` + EFS `prevent_destroy` | Deleting the PVC can lose the several-GB upload |

Because there is exactly **one** shared models directory (written by the upload job, read by all
engine pods), static provisioning expresses the 1:1 intent precisely and keeps the model data's
lifecycle under Terraform's control.

## Alignment with the existing CloudFormation stacks

The module mirrors conventions from [`../../cloudformation/`](../../cloudformation/) so it feels
native to the stack:

- **Naming** — `${arthur_resource_namespace}-genai-engine${arthur_resource_name_suffix}-<type>`,
  matching e.g. the S3 models bucket `${ns}-genai-engine-models${suffix}-${AccountId}` and the
  task role `${ns}-genai-engine-task-role${suffix}`.
- **BYO pattern** — like `ExistingModelsBucketName` / `PostgresBYOSecurityGroupIDs` /
  `GenaiEngineBYO*RoleIAMArn`, the module exposes `existing_efs_file_system_id`,
  `byo_efs_security_group_ids`, and `byo_efs_csi_role_arn`; each resource is created only when its
  BYO input is empty.
- **Tagging** — every resource carries `Name` + `Purpose = "Arthur GenAI Engine Model Storage"`
  (the exact value used on the S3 bucket), merged over a free-form `tags` map.
- **Lifecycle** — the S3 bucket is `DeletionPolicy: Retain`; the EFS filesystem mirrors this with PV
  `reclaimPolicy: Retain` and `prevent_destroy` so models aren't lost on a careless `destroy`.
- **Encryption** — the bucket forces AES256 + HTTPS-only; EFS uses `encrypted = true` (at rest) and
  `mount_options = ["tls"]` (in transit).

## How it feeds the rest of the deployment

- **Upload jobs** (`../../model-upload/k8s/04-job.yaml`, `06-copy-config-job.yaml`) already reference
  `claimName: arthur-models-pvc` and run as uid/gid `1000760000` — they work unchanged given the
  default `pvc_name` and `access_point_uid/gid`.
- **`01-pvc.yaml`** (the `ReadWriteOnce`, default-class PVC) must **not** be applied on EKS — this
  module owns the PVC.
- **genai-engine deployment** — the Helm chart supports the mount natively via the optional
  `modelPVC` values (`enabled`, `claimName`, `mountPath`, `readOnly`), wired into both the
  Deployment and the GPU DaemonSet. It is **off by default** — genai-engine runs without a PVC and
  downloads models normally — and when enabled the chart mounts the claim read-only and sets
  `MODEL_STORAGE_PATH` + `HF_HUB_OFFLINE=1`. The access point's `posix_user` enforces the uid, so no
  pod `securityContext` change is required.

## Known trade-offs / follow-ups

- **Two-provider chicken-and-egg:** the kubernetes provider needs a reachable cluster. The PV/PVC
  `depend_on` the add-on so a single `apply` works against an existing cluster; a brand-new cluster
  needs the AWS resources staged first (`-target`).
- **Token expiry in CI:** `aws_eks_cluster_auth` tokens are short-lived; use the exec-plugin provider
  form for long pipelines (see README).
