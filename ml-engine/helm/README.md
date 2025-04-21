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

## How to install ML Engine using Helm Chart

1. Create a Kubernetes secret for the client secret provided by the Arthur Platform
   ```bash
   CLIENT_SECRET_BASE64=$(echo -n $ML_ENGINE_CLIENT_SECRET | base64)
   kubectl -n $K8S_NAMESPACE create secret generic ml-engine-secrets \
      --from-literal=client_secret=$CLIENT_SECRET_BASE64
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
