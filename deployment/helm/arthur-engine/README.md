# Arthur Engine Helm Chart Deployment Guide

## Pre-requisites
Review the pre-requisites in the submodules, [genai-engine](../genai-engine/) and [ml-engine](../ml-engine/).

## How to install Arthur Engine using Helm Chart
1. Prepare an Arthur Engine Helm Chart configuration file, `values.yaml` from [values.yaml.template](values.yaml.template) in the directory where you will run Helm install. Populate the values accordingly.

2. Create Kubernetes secrets and install the Arthur Engine Chart by referencing [start.sh.template.cpu](start.sh.template.cpu) or [start.sh.template.gpu](start.sh.template.gpu).

3. Verify that all the pods are running with
    ```bash
    kubectl get pods -n arthur
    ```
    You should see both the GenAI Engine pods (`arthur-genai-engine`) and the ML Engine pods (`arthur-ml-engine`) in the running state. Please also inspect the logs.
