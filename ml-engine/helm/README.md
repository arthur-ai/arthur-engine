# Arthur ML Engine Helm Chart Deployment Guide

## Pre-requisites

### Engine Version
Look up an engine version to use from the [Releases](https://github.com/arthur-ai/arthur-engine/releases).

### Helm
* Install Helm on your workstation. Helm version 3.8.0 or higher is required.
* The Arthur ML Engine Helm charts are hosted in the OCI format as [GitHub packages](https://github.com/arthur-ai/arthur-engine/pkgs/container/arthur-engine%2Fcharts%2Fml-engine)
  ```bash
  helm show chart oci://ghcr.io/arthur-ai/arthur-engine/charts/ml-engine:<version_number>
  ```

### Kubernetes
The chart is tested on AWS Elastic Kubernetes Service (EKS) version 1.31.

* A `kubectl` workstation with admin privileges
* A dedicated namespace (e.g. `ml-engine`)
* For CPU high availability deployment: a node group with AWS `m8g.large` x 2 or similar
  * Memory: 16 GiB
  * CPU: 4 cores
  * Metrics server

### Container Image Repository Access
* There must be a network route available to connect to Docker Hub
* If Docker Hub access is not an option, you can push the images from Docker Hub to your private container registry and provide its access information in the `values.yaml` file

## How to install ML Engine using Helm Chart

1. Encode client secret to base64 and input it to `application-secret-example.yaml`
2. Apply secret to kubernetess:
   ```bash
   kubectl apply -f secrets-example.yaml
   ```

3. Prepare a copy of the Arthur ML Engine Helm Chart configuration file, [values.yaml](values.yaml) in the directory where you will run `helm install` and populate the values accordingly.

4. Install the Arthur ML Engine Helm Chart
    ```bash
    helm upgrade --install -n ml-engine -f ml-values.yaml ml-engine oci://ghcr.io/arthur-ai/arthur-engine/charts/ml-engine --version <version_number>
    ```

5. Verify that all the pods are running with
    ```bash
    kubectl get pods -n ml-engine
    ```
    You should see the ML Engine pods in the running state. Please also inspect the log.
