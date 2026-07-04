# Guardrail Models on a Regular PVC (No Network File System)

How to load Arthur GenAI Engine's guardrail models from a **standard block-backed `ReadWriteOnce` PVC** — no EFS, NFS, or other network/`ReadWriteMany` file system required.

Use this when you want to get running quickly on plain Kubernetes: dev/test, a single node, a single GenAI Engine replica, or any cluster that only has block storage (EKS EBS `gp3`, GKE PD, AKS managed-disk, `local-path`/hostpath on a single node, etc.).

> **The one trade-off to understand.** A block-backed PVC is `ReadWriteOnce` (RWO) — it can be attached to **one node at a time**, in **one availability zone**. That's fine for a **single** GenAI Engine replica, which is auto-pinned to the volume's zone. If you need **multiple replicas / HA / multi-AZ**, you need a `ReadWriteMany` volume (EFS/NFS) instead — see the **AWS EKS + EFS** section in [`../README.md`](../README.md).

---

## How it works

1. A one-time **Job** copies the model binaries baked into the `genai-engine-models-fs` image (`/models`) onto a mounted PVC (`/models-output`).
2. A small **config-copy Job** finalizes the GLiNER PII model config.
3. **GenAI Engine** mounts the same PVC and loads the models locally with `HF_HUB_OFFLINE=1` — no Hugging Face downloads at pod startup.

The Job auto-selects the filesystem backend because `TARGET_DIR` is set (as opposed to `S3_BUCKET` for the S3 backend).

---

## Prerequisites

- A Kubernetes cluster with a **StorageClass that dynamically provisions RWO block volumes** and is set as default (or named below). On EKS Auto Mode this is a `gp3` class using `ebs.csi.eks.amazonaws.com`.
- `kubectl` access and a namespace (`arthur` is used throughout).
- Enough node capacity for the Job (~1 CPU / 1Gi) and later the engine.
- **No** EFS/NFS, CSI-for-NFS, mount targets, or access points.

```bash
kubectl create namespace arthur   # if it doesn't exist
kubectl get storageclass          # confirm a default block SC exists (e.g. gp3)
```

---

## What differs from the EFS / `ReadWriteMany` path

| | Regular PVC (this doc) | EFS / RWX |
|---|---|---|
| `accessModes` | `ReadWriteOnce` | `ReadWriteMany` |
| Extra infra | none | EFS CSI driver, filesystem, mount targets, access point |
| File ownership | **real on-disk uid/gid** | squashed to the access point's `uid`/`gid` |
| Non-root writes | need **`fsGroup`** on the pod | handled by the access point |
| GenAI Engine replicas | **1** (co-located with the volume) | many, across AZs |

Because ownership is real (no access-point squash), the writer and the reader must agree on uid: write the files as **uid `65532`** — the `genai-engine` image's `nonroot` user — and set **`fsGroup: 65532`** so a non-root process can write a freshly provisioned disk.

> These manifests are adapted from the OpenShift-oriented files in [`k8s/`](k8s/): they use `runAsUser: 65532` (not `1000760000`), add `fsGroup: 65532`, and **drop `imagePullSecrets`** (the `arthurplatform/*` images are public on Docker Hub).

---

## Step 1 — PersistentVolumeClaim (RWO)

`pvc.yaml`
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: arthur-models-pvc
  namespace: arthur
  labels: { app: arthur-models }
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: gp3          # your default block StorageClass; omit this line to use the cluster default
  resources:
    requests: { storage: 25Gi }  # adjust to your model set
```

## Step 2 — ServiceAccount

`sa.yaml`
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: arthur-genai-engine-models-k8s-sa
  namespace: arthur
```

## Step 3 — Model upload Job

`upload-job.yaml`
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: arthur-genai-engine-models-k8s
  namespace: arthur
spec:
  backoffLimit: 3
  activeDeadlineSeconds: 3600
  ttlSecondsAfterFinished: 86400
  template:
    metadata:
      labels: { app: arthur-genai-engine-models-k8s }
    spec:
      serviceAccountName: arthur-genai-engine-models-k8s-sa
      restartPolicy: Never
      securityContext:
        fsGroup: 65532                 # block volume: kubelet chowns the fresh disk to this group so a non-root user can write
      containers:
      - name: model-upload
        image: arthurplatform/genai-engine-models-fs:<VERSION>   # pin a release, e.g. 2.1.683
        imagePullPolicy: Always
        command: ["python", "-u", "/app/upload_models.py"]
        env:
        - { name: SOURCE_DIR, value: "/models" }
        - { name: TARGET_DIR, value: "/models-output" }   # presence of TARGET_DIR selects the filesystem backend
        - { name: LOG_LEVEL,  value: "INFO" }
        volumeMounts:
        - { name: models-storage, mountPath: /models-output }
        resources:
          requests: { cpu: "500m", memory: "1Gi" }
          limits:   { cpu: "1000m", memory: "1Gi" }
        securityContext:
          runAsNonRoot: true
          runAsUser: 65532             # write as 65532 so the engine (nonroot uid 65532) owns and can read/write the files
          runAsGroup: 65532
          allowPrivilegeEscalation: false
          capabilities: { drop: ["ALL"] }
      volumes:
      - name: models-storage
        persistentVolumeClaim:
          claimName: arthur-models-pvc
```

## Step 4 — GLiNER config-copy Job

`copy-config-job.yaml`
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: copy-gliner-config
  namespace: arthur
spec:
  backoffLimit: 1
  activeDeadlineSeconds: 600
  ttlSecondsAfterFinished: 3600
  template:
    metadata:
      labels: { app: copy-gliner-config }
    spec:
      serviceAccountName: arthur-genai-engine-models-k8s-sa
      restartPolicy: Never
      securityContext:
        fsGroup: 65532
      containers:
      - name: copier
        image: arthurplatform/genai-engine-models-fs:<VERSION>
        imagePullPolicy: IfNotPresent
        command:
        - python
        - -c
        - |
          import shutil, os, sys
          d = '/models-output/urchade/gliner_multi_pii-v1'
          src = os.path.join(d, 'gliner_config.json')
          if os.path.exists(src):
              shutil.copy2(src, os.path.join(d, 'config.json'))
              print('✅ Copied gliner_config.json to config.json')
          else:
              print('❌ gliner_config.json not found'); sys.exit(1)
        volumeMounts:
        - { name: models-storage, mountPath: /models-output }
        securityContext:
          runAsNonRoot: true
          runAsUser: 65532
          runAsGroup: 65532
          allowPrivilegeEscalation: false
          capabilities: { drop: ["ALL"] }
      volumes:
      - name: models-storage
        persistentVolumeClaim:
          claimName: arthur-models-pvc
```

## Step 5 — Apply and verify

```bash
kubectl apply -f pvc.yaml -f sa.yaml
kubectl apply -f upload-job.yaml

# With WaitForFirstConsumer (typical for block SCs) the PVC stays Pending until the Job pod
# is scheduled; the volume is then provisioned in that pod's zone. This is expected.
kubectl -n arthur wait --for=condition=complete job/arthur-genai-engine-models-k8s --timeout=900s
kubectl -n arthur logs -l app=arthur-genai-engine-models-k8s --tail=5   # expect: "All models transferred successfully!"

kubectl apply -f copy-config-job.yaml
kubectl -n arthur wait --for=condition=complete job/copy-gliner-config --timeout=300s

kubectl -n arthur get pvc arthur-models-pvc   # expect: Bound
```

---

## Pointing GenAI Engine at the PVC

The chart doesn't template the model volume, so add it to the GenAI Engine deployment (via Helm values that support it, or a `kubectl patch`). Because this is a single RWO volume:

- **Run one replica** (`genaiEngineReplicaCount: 1`, HPA disabled). The PV carries zone node-affinity, so the scheduler automatically keeps the pod in the volume's zone. A second replica will get stuck (`Multi-Attach` / `FailedMount`).
- **Mount read-write** (`readOnly: false`) — the model loader writes Hugging Face `*.lock` files under the model dir even with `HF_HUB_OFFLINE=1`; a read-only mount crashes the worker.
- Set **`fsGroup: 65532`** on the engine pod too, and:

```
MODEL_STORAGE_PATH=/home/nonroot/models-output
HF_HUB_OFFLINE=1
```

```yaml
# added to the genai-engine pod spec
spec:
  securityContext:
    fsGroup: 65532
  volumes:
  - name: models
    persistentVolumeClaim:
      claimName: arthur-models-pvc
  containers:
  - name: arthur-genai-engine
    volumeMounts:
    - name: models
      mountPath: /home/nonroot/models-output   # matches MODEL_STORAGE_PATH
      readOnly: false
```

---

## Gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Job pod `CreateContainerConfigError`, "permission denied" writing `/models-output` | non-root user can't write a fresh block volume | add `fsGroup: 65532` to the pod `securityContext` |
| Engine can't read models / permission denied | files written as a different uid than the engine (65532) | write with `runAsUser: 65532` (no access-point squash on block storage) |
| Job pod `secret "arthurai-repo-creds" not found` | leftover `imagePullSecrets` on a public image | remove `imagePullSecrets` (done in the manifests above) |
| Second engine replica stuck `Pending` / `Multi-Attach error` | RWO volume can attach to only one node | run a single replica, or switch to an EFS/RWX PVC |
| Engine worker crashes: `[Errno 30] Read-only file system` | loader writes HF lock files | mount the volume **read-write** |
| PVC stays `Pending` before the Job runs | `WaitForFirstConsumer` binding mode | expected — it binds once the Job pod schedules |

---

## Graduating to a network file system

Switch to a `ReadWriteMany` PVC when you need **more than one GenAI Engine replica**, HA, or multi-AZ scheduling. The Job manifests above are unchanged — only the PVC (and its StorageClass) change to an EFS/NFS-backed RWX volume. See the **FS → AWS EKS + EFS** section in [`../README.md`](../README.md).

---

## Cleanup

```bash
kubectl -n arthur delete job arthur-genai-engine-models-k8s copy-gliner-config
# delete the PVC only if you also want to discard the downloaded models:
# kubectl -n arthur delete pvc arthur-models-pvc
```
