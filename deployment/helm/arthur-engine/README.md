# Arthur Engine Helm Chart Deployment Guide

## Pre-requisites
Review the pre-requisites in the submodules, [genai-engine](../genai-engine/) and [ml-engine](../ml-engine/).

## Using a private image repository

If Docker Hub is not reachable from your cluster, mirror both engine images into your own container registry and set the image values under each subchart in `values.yaml`. The keys are identical to the standalone charts — see [genai-engine](../genai-engine/README.md#using-a-private-image-repository) and [ml-engine](../ml-engine/README.md#using-a-private-image-repository) for the mirroring commands and full field-by-field details — just nested under the `arthur-genai-engine` and `arthur-ml-engine` keys:

```yaml
arthur-genai-engine:
  # Full repository path INCLUDING the image name (cpu or gpu variant)
  genaiEngineContainerImageLocation: "myregistry.example.com/arthur/genai-engine-cpu"
  genaiEngineVersion: "<tag>"                     # used verbatim
  containerRepositoryCredentialRequired: true    # only if the registry needs auth
  imagePullSecretName: "arthur-repository-credentials"

arthur-ml-engine:
  containerRepository:
    # Registry host + org/path, WITHOUT the final image-name segment
    imageLocation: "myregistry.example.com/arthur"
    credentialsRequired: true                     # only if the registry needs auth
    imagePullSecretName: "arthur-repository-credentials"
  mlEngine:
    deployment:
      containerImageName: "ml-engine"             # the final repository segment
      containerImageVersion: "<tag>"              # used verbatim
```

Note the two engines split the image reference differently: GenAI Engine takes the whole repository path (incl. image name) in one field, while ML Engine takes the registry/org path and the image name in separate fields. The `arthur-ml-engine.image` block in the values template (`repository`/`tag`/`pullPolicy`) is **not** read by the deployment — set the `containerRepository` and `mlEngine.deployment.container*` fields shown above instead.

If your registry requires authentication, create the pull secret in the deploy namespace before installing (a standard Kubernetes `docker-registry` secret). Both engines can share one secret when they use the same registry:

```bash
# WARNING: Do NOT set up secrets this way in production.
#          Use a secure method such as sealed secrets and external secret store providers.
kubectl -n arthur create secret docker-registry arthur-repository-credentials \
    --docker-server='<your-registry-host>' \
    --docker-username='<username>' \
    --docker-password='<password>' \
    --docker-email=''
```

## How to install Arthur Engine using Helm Chart
1. Prepare an Arthur Engine Helm Chart configuration file, `values.yaml` from [values.yaml.template](values.yaml.template) in the directory where you will run Helm install. Populate the values accordingly.

2. Create Kubernetes secrets and install the Arthur Engine Chart by referencing [start.sh.template.cpu](start.sh.template.cpu) or [start.sh.template.gpu](start.sh.template.gpu).

3. Verify that all the pods are running with
    ```bash
    kubectl get pods -n arthur
    ```
    You should see both the GenAI Engine pods (`arthur-genai-engine`) and the ML Engine pods (`arthur-ml-engine`) in the running state. Please also inspect the logs.
