# Kubernetes/OpenShift Model Upload Deployment

This directory contains Kubernetes/OpenShift-specific deployment configuration for the unified model upload job.

## About

The model upload code is located at `/model-upload/` (repository root). This directory only contains Kubernetes deployment manifests.

## Files

- `01-pvc.yaml` - PersistentVolumeClaim for model storage
- `02-serviceaccount.yaml` - ServiceAccount for the job
- `04-job.yaml` - Job definition to copy models to PVC
- `06-copy-config-job.yaml` - Optional job to copy configuration

## Usage

### Prerequisites

1. Build and push the unified K8s image:
   ```bash
   cd ../../../model-upload
   ./build.sh --version <VERSION> --push k8s
   ```

2. Ensure the image is accessible to your cluster:
   ```bash
   # For Docker Hub (if using private repo)
   kubectl create secret docker-registry arthurai-repo-creds \
     --docker-server=https://index.docker.io/v1/ \
     --docker-username=<USERNAME> \
     --docker-password=<PASSWORD>
   ```

### Deploy

1. Update `04-job.yaml`:
   - Replace `<genai_engine_models_version>` with your version (e.g., `2.1.343`)

2. Apply the manifests in order:
   ```bash
   # Create PVC for model storage
   kubectl apply -f 01-pvc.yaml

   # Create ServiceAccount
   kubectl apply -f 02-serviceaccount.yaml

   # Run model upload job
   kubectl apply -f 04-job.yaml

   # (Optional) Copy configuration
   kubectl apply -f 06-copy-config-job.yaml
   ```

### Monitor Job

```bash
# Check job status
kubectl get job arthur-genai-engine-models-k8s

# View logs
kubectl logs job/arthur-genai-engine-models-k8s

# Watch pod events
kubectl get pods -l app=arthur-genai-engine-models-k8s --watch
```

### Verify Models

```bash
# Create a debug pod to verify models were copied
kubectl run -it --rm debug --image=busybox --restart=Never -- sh

# Inside the pod, mount the PVC and check
ls -la /models-output/
```

## Environment Variables

The job uses the unified `upload_models.py` script with the following environment variables:

- `STORAGE_BACKEND=filesystem` - Use filesystem backend (copies to PVC)
- `SOURCE_DIR=/models` - Source directory in container (pre-downloaded models)
- `TARGET_DIR=/models-output` - Target directory (PVC mount point)
- `LOG_LEVEL=INFO` - Logging level

## Image Tags

Images follow the naming convention:
- `arthurplatform/genai-engine-models:<VERSION>-k8s`
- Example: `arthurplatform/genai-engine-models:2.1.343-k8s`

## Storage

The PVC is configured with:
- **Size**: 10Gi (adjust based on model size, currently ~1.8GB)
- **AccessMode**: ReadWriteOnce
- **StorageClass**: Default (or specify custom class)

Models are copied to the PVC and can be mounted by GenAI Engine pods:

```yaml
volumes:
  - name: models
    persistentVolumeClaim:
      claimName: arthur-models-pvc
```

## OpenShift Security

The job runs with restricted security context:
- Non-root user (UID 1000760000)
- No privilege escalation
- Drops all capabilities
- Read-only root filesystem: false (needs to write to /models-output)

Ensure your namespace has the appropriate SecurityContextConstraints (SCC):
```bash
# Grant restricted-v2 SCC to service account
oc adm policy add-scc-to-user restricted-v2 \
  system:serviceaccount:YOUR_NAMESPACE:arthur-genai-engine-models-k8s-sa
```

## Cleanup

```bash
# Delete job (PVC and ServiceAccount remain for reuse)
kubectl delete job arthur-genai-engine-models-k8s

# To delete everything:
kubectl delete -f 04-job.yaml
kubectl delete -f 02-serviceaccount.yaml
kubectl delete -f 01-pvc.yaml  # WARNING: Deletes all models
```

## Related

- [Unified Model Upload Code](/model-upload/) - Source code and Dockerfile
- [ECS Deployment](../ecs/model-upload/) - AWS ECS deployment
- [GCP Deployment](../gcp/model-upload/) - GCS Cloud Run deployment
