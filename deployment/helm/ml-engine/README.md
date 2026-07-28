# Arthur ML Engine Helm Chart Deployment Guide

## Pre-requisites

### Engine Version
Look up an engine version to use from the [Releases](https://github.com/arthur-ai/arthur-engine/releases).

### Helm
* Install Helm on your workstation. Helm version 3.8.0 or higher is required.
* The Arthur ML Engine Helm charts are hosted in the OCI format as [GitHub packages](https://github.com/arthur-ai/arthur-engine/pkgs/container/arthur-engine%2Fcharts%2Farthur-ml-engine)
  ```bash
  helm show chart oci://ghcr.io/arthur-ai/arthur-engine/charts/arthur-ml-engine:<version_number>
  ```

### Kubernetes
The chart is tested on AWS Elastic Kubernetes Service (EKS) version 1.31.

* A `kubectl` workstation with admin privileges
* A dedicated namespace (e.g. `arthur`)
* For CPU high availability deployment: a node group with AWS `m8g.large` x 2 or similar
  * Memory: 16 GiB
  * CPU: 4 cores
  * Metrics server

### Container Image Repository Access
* There must be a network route available to connect to Docker Hub
* If Docker Hub access is not an option, you can push the images from Docker Hub to your private container registry and provide its access information in the `values.yaml` file

## Using a private image repository

By default the chart pulls the ML Engine image from Docker Hub (`arthurplatform/ml-engine`). If Docker Hub is not reachable from your cluster, mirror the image into your own container registry and point the chart at it.

1. **Mirror the image** into your registry. The tag is used verbatim, so you can keep the upstream version or re-tag it as you like:

    ```bash
    docker pull arthurplatform/ml-engine:<version>
    docker tag  arthurplatform/ml-engine:<version> <your-registry>/<path>/ml-engine:<tag>
    docker push <your-registry>/<path>/ml-engine:<tag>
    ```

2. **Create an image pull secret** — only if your registry requires authentication. This must be a standard Kubernetes `docker-registry` secret (type `kubernetes.io/dockerconfigjson`); the chart references it as a pod `imagePullSecrets` entry. Point `--docker-server` at your registry host:

    ```bash
    # WARNING: Do NOT set up secrets this way in production.
    #          Use a secure method such as sealed secrets and external secret store providers.
    kubectl -n arthur create secret docker-registry my-registry-credentials \
        --docker-server='<your-registry-host>' \
        --docker-username='<username>' \
        --docker-password='<password>' \
        --docker-email=''
    ```

3. **Point the chart at your registry** in `values.yaml`. The image reference is assembled as `<imageLocation>/<containerImageName>:<containerImageVersion>` (one `/`, one `:`), so split your full image reference across the three fields — everything before the final repository segment goes in `imageLocation`:

    ```yaml
    containerRepository:
      # Registry host + org/path, WITHOUT the final image-name segment
      imageLocation: "<your-registry>/<path>"      # e.g. myregistry.example.com/arthur
      # Set to true only if the registry requires authentication
      credentialsRequired: true
      # Name of the docker-registry secret from step 2 (leave "" if credentialsRequired is false)
      imagePullSecretName: "my-registry-credentials"
    mlEngine:
      deployment:
        containerImageName: "ml-engine"            # the final repository segment
        containerImageVersion: "<tag>"             # the tag you pushed, used verbatim
    ```

    Example — for the image `myregistry.example.com/arthur/ml-engine:ml-engine_2.1.683`:

    | Field | Value |
    | --- | --- |
    | `containerRepository.imageLocation` | `myregistry.example.com/arthur` |
    | `mlEngine.deployment.containerImageName` | `ml-engine` |
    | `mlEngine.deployment.containerImageVersion` | `ml-engine_2.1.683` |

    > Do **not** put the whole `repo:tag` into `containerImageName` — the tag (including any prefix such as `ml-engine_`) belongs only in `containerImageVersion`.

You can verify the rendered image reference before installing:

```bash
helm template arthur-ml-engine oci://ghcr.io/arthur-ai/arthur-engine/charts/arthur-ml-engine \
    --version <version_number> -f values.yaml | grep 'image:'
# -> image: "myregistry.example.com/arthur/ml-engine:ml-engine_2.1.683"
```

## How to install ML Engine using Helm Chart

1. Create a Kubernetes secret for the client secret provided by the Arthur Platform
    # WARNING: Do NOT set up secrets this way in production.
    #          Use a secure method such as sealed secrets and external secret store providers.
   ```bash
   kubectl -n arthur create secret generic ml-engine-client-secret \
        --from-literal=client_id='<client_id>' \
        --from-literal=client_secret='<client_secret>'
   ```

2. Prepare an Arthur ML Engine Helm Chart configuration file, `values.yaml` from [values.yaml.template](values.yaml.template) in the directory where you will run Helm install and populate the values accordingly.

3. Install the Arthur ML Engine Helm Chart
    ```bash
    helm upgrade --install -n arthur -f values.yaml arthur-ml-engine oci://ghcr.io/arthur-ai/arthur-engine/charts/arthur-ml-engine --version <version_number>
    ```

4. Verify that all the pods are running with
    ```bash
    kubectl get pods -n arthur
    ```
    You should see the ML Engine pods in the running state. Please also inspect the log.

## Autoscaling (HPA)

The chart ships a `HorizontalPodAutoscaler` that is **enabled by default**. It scales the ML Engine
deployment on both CPU and memory utilization. When the HPA is enabled the deployment's replica
count is managed by the HPA (the static `mlEngine.deployment.replicas` value is not rendered).

Requirements and caveats:

* A **metrics-server** must be running in the cluster (already listed under the Kubernetes
  prerequisites above).
* Each replica requests a **large footprint (~16Gi RAM / 7–8 CPU)**, so `maxReplicas` multiplies
  that footprint — e.g. `maxReplicas: 10` can request up to ~160Gi / ~80 CPU. Tune `minReplicas`
  and `maxReplicas` to your node budget.

Configure it via the `arthurMLEngineHPA` block in `values.yaml`:

```yaml
arthurMLEngineHPA:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 50
  targetMemoryUtilizationPercentage: 80
```

To pin a fixed replica count instead, set `arthurMLEngineHPA.enabled: false`; the deployment then
uses `mlEngine.deployment.replicas`.
