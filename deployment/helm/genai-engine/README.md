# Arthur GenAI Engine Helm Chart Deployment Guide

## Pre-requisites

### Engine Version
Look up an engine version to use from the [Releases](https://github.com/arthur-ai/arthur-engine/releases).

### Helm
* Install Helm on your workstation. Helm version 3.8.0 or higher is required
* The Arthur Engine Helm charts are hosted in the OCI format as [GitHub packages](https://github.com/arthur-ai/arthur-engine/pkgs/container/arthur-engine%2Fcharts%2Farthur-engine)
  ```bash
  helm show chart oci://ghcr.io/arthur-ai/arthur-engine/charts/arthur-genai-engine:<version_number>
  ```

### OpenAI GPT Model
Arthur GenAI Engine's hallucination and sensitive data rules require an OpenAI GPT model for running evaluations.
Please review the GPT model requirements below:
* An OpenAI GPT model with at least one endpoint. GenAI Engine supports Azure and OpenAI as the LLM service provider.
* A secure network route between your environment and the OpenAI endpoint(s)
* Token limits, configured appropriately for your use cases

### DNS and TLS
A DNS hostname for the GenAI Engine, plus a TLS certificate for that **same** hostname — an
[AWS ACM](https://docs.aws.amazon.com/acm/) certificate for the ALB path, or a Kubernetes TLS
secret for the nginx path. The DNS hostname, the certificate domain, and `genaiEngineIngressURL`
must all be identical. See [Ingress and HTTPS](#ingress-and-https).

### Kubernetes
The chart is tested on AWS Elastic Kubernetes Service (EKS) version 1.31.

* A `kubectl` workstation with admin privileges
* An ingress controller (see [Ingress and HTTPS](#ingress-and-https) for the full setup):
  * Classic EKS / self-managed clusters: an nginx ingress controller, installed separately (it is **not** part of this chart).
  * EKS Auto Mode, or any cluster running the AWS Load Balancer Controller: no nginx controller is needed — use the built-in `alb` IngressClass.
* A dedicated namespace (e.g. `arthur`)
* For CPU high availability deployment: a node group with AWS `m8g.large` x 2 or similar
  * Memory: 16 GiB
  * CPU: 4 cores
  * Metrics server
* For GPU high availability deployment: a node group with AWS `g4dn.2xlarge` x 2 or similar
  * Memory: 64 GiB
  * CPU: 16 cores
  * GPU: 2 cores

### Postgres database
The GenAI Engine is tested on PostgreSQL 15. Using a managed Postgres database is recommended.
Please pre-create a database on your instance (e.g. `arthur_genai_engine`)

### Container Image Repository Access
* There must be a network route available to connect to Docker Hub
* If Docker Hub access is not an option, you can push the images from Docker Hub to your private container registry and provide its access information in the `values.yaml` file

## GPU deployment
Arthur recommends running the GenAI Engine on GPUs for any production-grade deployments. The usage of GPUs provides significantly lower latency, higher scalability and platform cost efficiency.

The CPU deployment runs the GenAI Engine as a Deployment with a Horizontal Pod Autoscaler (HPA).

For GPU, the chart supports two topologies. Pick the one that matches how your cluster provisions nodes (selected with `genaiEngineDeploymentType` in [values.yaml.template](values.yaml.template)):

- **Managed GPU node group + ASG → DaemonSet.** Arthur's preferred configuration for classic EKS clusters with managed node groups. GenAI Engine runs as a DaemonSet — one pod per GPU node — and the node group's Auto Scaling Group (ASG) scales GPU nodes out and in on demand. This does not assume a large pool of idle GPUs. See [How to configure your AWS EKS cluster with a GPU node group (managed node group)](#how-to-configure-your-aws-eks-cluster-with-a-gpu-node-group-managed-node-group).
- **EKS Auto Mode / Karpenter → Deployment.** For clusters on [EKS Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/automode.html), which have no managed node groups. Auto Mode's Karpenter provisions a GPU node only in response to a **pending workload pod** — it does not scale up for a DaemonSet ([Karpenter FAQ](https://karpenter.sh/docs/faq/)) — so GenAI Engine runs as a Deployment. See [How to configure EKS Auto Mode for GPU](#how-to-configure-eks-auto-mode-for-gpu-karpenter).

## How to configure your AWS EKS cluster with a GPU node group (managed node group)
This section is a guide to help you configure your existing AWS EKS cluster with a GPU node group for GenAI Engine.
To perform the steps, you need AWS CLI with admin level permissions for the target AWS account.

1. Prepare base64 encoded user data for boostrapping the EKS GPU nodes with the below script.
Replace `${CLUSTER_NAME}` with your EKS cluster name. The script is tested on MacOS.

```bash
export USER_DATA_BASE64=$(cat <<'EOF' | base64 -b 0
#!/bin/bash
set -ex

# EKS Bootstrap script
/etc/eks/bootstrap.sh ${CLUSTER_NAME}

# CloudWatch Agent setup
yum install -y amazon-cloudwatch-agent

cat <<CWAGENT > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
{
  "agent": {
    "run_as_user": "root"
  },
  "metrics": {
    "aggregation_dimensions": [["InstanceId"]],
    "metrics_collected": {
      "nvidia_gpu": {
        "append_dimensions": {
          "EKSClusterName": "${CLUSTER_NAME}",
          "EKSNodeGroupType": "arthur-genai-engine-eks-gpu",
          "ImageId": "$(curl -s http://169.254.169.254/latest/meta-data/ami-id)",
          "InstanceId": "$(curl -s http://169.254.169.254/latest/meta-data/instance-id)",
          "InstanceType": "$(curl -s http://169.254.169.254/latest/meta-data/instance-type)"
        },
        "measurement": [
          "utilization_gpu",
          "utilization_memory",
          "memory_total",
          "memory_used",
          "memory_free",
          "power_draw"
        ]
      }
    }
  }
}
CWAGENT

/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
  -s

systemctl enable amazon-cloudwatch-agent
systemctl restart amazon-cloudwatch-agent
EOF
)
```

2. Make sure your AWS CLI is configured with the correct AWS account and region

3. Add the following permissions to your EKS node IAM role so that the GPU metrics can be shipped to CloudWatch from the GPU nodes
```json
    "Action": [
        "cloudwatch:ListMetrics",
        "cloudwatch:PutMetricData",
        "cloudwatch:PutMetricStream"
    ],
```

4. Look up the AMI ID for the latest GPU optimized AMI in the correct region
```bash
aws ssm get-parameters \
--names /aws/service/eks/optimized-ami/<kubernetes-version>/amazon-linux-2-gpu/recommended/image_id \
--region us-east-2
```

5. Create a launch template for the GPU nodes.
Replace `REPLACE_ME_CLUSTER_NAME` with your EKS cluster name.
Replace `REPLACE_ME_AMI_ID` with the AMI ID you found in the previous step.
Make sure the `$USER_DATA_BASE64` is correctly set from step 1.

```bash
export CLUSTER_NAME=REPLACE_ME_CLUSTER_NAME
export IMAGE_ID=REPLACE_ME_AMI_ID
export LAUNCH_TEMPLATE_NAME=arthur-genai-engine-eks-gpu
export NODEGROUP_NAME=arthur-genai-engine-eks-gpu
export INSTANCE_TYPE=g4dn.2xlarge
export VOLUME_SIZE=60

aws ec2 create-launch-template \
  --launch-template-name ${LAUNCH_TEMPLATE_NAME} \
  --version-description "Arthur GenAI Engine EKS GPU nodes" \
  --launch-template-data "{
    \"ImageId\": \"${IMAGE_ID}\",
    \"InstanceType\": \"${INSTANCE_TYPE}\",
    \"BlockDeviceMappings\": [
      {
        \"DeviceName\": \"/dev/xvda\",
        \"Ebs\": {
          \"VolumeSize\": ${VOLUME_SIZE},
          \"Encrypted\": true
        }
      }
    ],
    \"TagSpecifications\": [
      {
        \"ResourceType\": \"instance\",
        \"Tags\": [
          {
            \"Key\": \"Name\",
            \"Value\": \"${NODEGROUP_NAME}\"
          },
          {
            \"Key\": \"kubernetes.io/cluster/${CLUSTER_NAME}\",
            \"Value\": \"owned\"
          }
        ]
      }
    ],
    \"UserData\": \"${USER_DATA_BASE64}\"
  }"
```

6. Create a EKS node group with the launch template created in the previous step.
Replace `REPLACE_ME_SUBNET_1_ID`, `REPLACE_ME_SUBNET_2_ID`, `REPLACE_ME_SUBNET_3_ID`, and `REPLACE_ME_NODE_ROLE_ARN` with the correct values.

```bash
export MIN_NODES=2
export MAX_NODES=2
export DESIRED_NODES=2
export SUBNET_1_ID=REPLACE_ME_SUBNET_1_ID
export SUBNET_2_ID=REPLACE_ME_SUBNET_2_ID
export SUBNET_3_ID=REPLACE_ME_SUBNET_3_ID
export NODE_ROLE_ARN=REPLACE_ME_NODE_ROLE_ARN
export LAUNCH_TEMPLATE_VERSION=1

LAUNCH_TEMPLATE_ID=$(aws ec2 describe-launch-templates \
  --filters Name=launch-template-name,Values=${LAUNCH_TEMPLATE_NAME} \
  --query 'LaunchTemplates[0].LaunchTemplateId' \
  --output text)

aws eks create-nodegroup \
  --cluster-name ${CLUSTER_NAME} \
  --nodegroup-name ${NODEGROUP_NAME} \
  --scaling-config minSize=${MIN_NODES},maxSize=${MAX_NODES},desiredSize=${DESIRED_NODES} \
  --subnets ${SUBNET_1_ID} ${SUBNET_2_ID} ${SUBNET_3_ID} \
  --launch-template id=${LAUNCH_TEMPLATE_ID},version=${LAUNCH_TEMPLATE_VERSION} \
  --node-role ${NODE_ROLE_ARN} \
  --labels capability=gpu \
  --tags "k8s.io/cluster-autoscaler/enabled=true,k8s.io/cluster-autoscaler/${CLUSTER_NAME}=owned"
```

7. Configure autoscaling policies for the node group. Wait until the node group is created before running the below commands.
```bash
export AUTOSCALING_GROUP_NAME=$(aws eks describe-nodegroup \
  --cluster-name ${CLUSTER_NAME} \
  --nodegroup-name ${NODEGROUP_NAME} \
  --query 'nodegroup.resources.autoScalingGroups[0].name' \
  --output text)

AUTOSCALING_ARN=$(aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names ${AUTOSCALING_GROUP_NAME} \
  --query 'AutoScalingGroups[0].AutoScalingGroupARN' \
  --output text)

# Define queries for CloudWatch alarms
export CPU_UTILIZATION_QUERY="SELECT AVG(CPUUtilization) FROM SCHEMA(\"AWS/EC2\", AutoScalingGroupName) WHERE AutoScalingGroupName = '${AUTOSCALING_GROUP_NAME}'"
export CPU_ALARM_NAME="arthur-genai-engine-eks-cpu-utilization-alarm"
export GPU_UTILIZATION_QUERY="SELECT AVG(nvidia_smi_utilization_gpu) FROM SCHEMA(CWAgent,EKSClusterName,ImageId,InstanceId,InstanceType,EKSNodeGroupType,arch,host,index,name) WHERE EKSClusterName = '${CLUSTER_NAME}' AND EKSNodeGroupType = 'arthur-genai-engine-eks-gpu'"
export GPU_ALARM_NAME="arthur-genai-engine-eks-gpu-utilization-alarm"

# Create scale-out policy for GPU
export SCALE_OUT_POLICY_ARN=$(aws autoscaling put-scaling-policy \
  --auto-scaling-group-name ${AUTOSCALING_GROUP_NAME} \
  --policy-name gpu-utilization-scale-out-policy \
  --policy-type StepScaling \
  --adjustment-type ChangeInCapacity \
  --step-adjustments '[{
    "MetricIntervalLowerBound": 0,
    "ScalingAdjustment": 1
  }]' \
  --query 'PolicyARN' \
  --output text)

aws cloudwatch put-metric-alarm \
  --alarm-name ${GPU_ALARM_NAME}-scale-out \
  --alarm-description "Triggers autoscaling when average GPU utilization exceeds 40%" \
  --metrics '[{
    "Id": "gpu_util",
    "Expression": "'${GPU_UTILIZATION_QUERY}'",
    "Period": 120,
    "ReturnData": true
  }]' \
  --threshold 40 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions ${SCALE_OUT_POLICY_ARN}

# Create scale-out policy for CPU
export CPU_SCALE_OUT_POLICY_ARN=$(aws autoscaling put-scaling-policy \
  --auto-scaling-group-name ${AUTOSCALING_GROUP_NAME} \
  --policy-name cpu-utilization-scale-out-policy \
  --policy-type StepScaling \
  --adjustment-type ChangeInCapacity \
  --step-adjustments '[{
    "MetricIntervalLowerBound": 0,
    "ScalingAdjustment": 1
  }]' \
  --query 'PolicyARN' \
  --output text)

aws cloudwatch put-metric-alarm \
  --alarm-name ${CPU_ALARM_NAME}-scale-out \
  --alarm-description "Triggers autoscaling when average CPU utilization exceeds 60%" \
  --metrics '[{
    "Id": "cpu_util",
    "Expression": "'${CPU_UTILIZATION_QUERY}'",
    "Period": 120,
    "ReturnData": true
  }]' \
  --threshold 60 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions ${CPU_SCALE_OUT_POLICY_ARN}
```

Note: For faster scaling, usage of warm instances can be considered.

8. Optionally, create a scale-in policy for the GPU node group
```bash
# Create scale-in policy for GPU
export SCALE_IN_POLICY_ARN=$(aws autoscaling put-scaling-policy \
  --auto-scaling-group-name ${AUTOSCALING_GROUP_NAME} \
  --policy-name gpu-utilization-scale-in-policy \
  --policy-type StepScaling \
  --adjustment-type ChangeInCapacity \
  --step-adjustments '[{
    "MetricIntervalUpperBound": 0,
    "ScalingAdjustment": -1
  }]' \
  --query 'PolicyARN' \
  --output text)

aws cloudwatch put-metric-alarm \
  --alarm-name ${GPU_ALARM_NAME}-scale-in \
  --alarm-description "Triggers autoscaling when average GPU utilization is below 10%" \
  --metrics '[{
    "Id": "gpu_util",
    "Expression": "'${GPU_UTILIZATION_QUERY}'",
    "Period": 120,
    "ReturnData": true
  }]' \
  --threshold 10 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions ${SCALE_IN_POLICY_ARN}

# Create scale-in policies for CPU
export CPU_SCALE_IN_POLICY_ARN=$(aws autoscaling put-scaling-policy \
  --auto-scaling-group-name ${AUTOSCALING_GROUP_NAME} \
  --policy-name cpu-utilization-scale-in-policy \
  --policy-type StepScaling \
  --adjustment-type ChangeInCapacity \
  --step-adjustments '[{
    "MetricIntervalUpperBound": 0,
    "ScalingAdjustment": -1
  }]' \
  --query 'PolicyARN' \
  --output text)

aws cloudwatch put-metric-alarm \
  --alarm-name ${CPU_ALARM_NAME}-scale-in \
  --alarm-description "Triggers autoscaling when average CPU utilization is below 5%" \
  --metrics '[{
    "Id": "cpu_util",
    "Expression": "'${CPU_UTILIZATION_QUERY}'",
    "Period": 120,
    "ReturnData": true
  }]' \
  --threshold 5 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions ${CPU_SCALE_IN_POLICY_ARN}
```

9. Label the CPU node group with `capability=cpu`

## How to configure EKS Auto Mode for GPU (Karpenter)
This section is a guide to run the GenAI Engine on GPUs on an [EKS Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/automode.html) cluster. Auto Mode has no managed node groups — it uses a managed **Karpenter** to provision nodes. Karpenter only launches a node in response to an **unschedulable workload pod**, and it will **not** scale up for a DaemonSet on its own ([Karpenter FAQ](https://karpenter.sh/docs/faq/)). So on Auto Mode the GenAI Engine runs as a **Deployment**, and it is the Deployment's pod (pinned to your GPU nodes via a `nodeSelector`) that triggers Karpenter to create a GPU node.

To perform the steps you need `kubectl` access to the cluster with admin privileges.

1. **Create a GPU NodePool.** Auto Mode's built-in `system` / `general-purpose` NodePools only run non-accelerated instances, so create a custom NodePool that provisions NVIDIA GPU instances, labels its nodes so the engine can target them, and taints them so other workloads don't land on expensive GPU hardware. Save as `gpu-nodepool.yaml` and apply with `kubectl apply -f gpu-nodepool.yaml`. Adjust the instance family/sizes and GPU limit for your needs; see [Manage compute for AI/ML workloads with EKS Auto Mode and Karpenter](https://docs.aws.amazon.com/eks/latest/userguide/ml-node-pools.html) for the full set of well-known labels.

    ```yaml
    apiVersion: karpenter.sh/v1
    kind: NodePool
    metadata:
      name: arthur-genai-engine-gpu
    spec:
      template:
        metadata:
          labels:
            capability: gpu          # GenAI Engine pods target this via nodeSelector
        spec:
          # Use the built-in EKS Auto Mode NodeClass (or reference your own custom NodeClass)
          nodeClassRef:
            group: eks.amazonaws.com
            kind: NodeClass
            name: default
          requirements:
            - key: "eks.amazonaws.com/instance-family"
              operator: In
              values: ["g4dn"]                 # NVIDIA GPU instance family
            - key: "eks.amazonaws.com/instance-size"
              operator: In
              values: ["2xlarge", "4xlarge"]   # -> g4dn.2xlarge / g4dn.4xlarge
            - key: "eks.amazonaws.com/instance-gpu-manufacturer"
              operator: In
              values: ["nvidia"]
            - key: "karpenter.sh/capacity-type"
              operator: In
              values: ["on-demand"]
          # Taint so only GPU workloads that tolerate it land on these nodes
          taints:
            - key: nvidia.com/gpu
              value: "true"
              effect: NoSchedule
      # Cap total GPUs; idle GPU nodes are consolidated away (scale to zero)
      limits:
        nvidia.com/gpu: "8"
      disruption:
        consolidationPolicy: WhenEmptyOrUnderutilized
        consolidateAfter: 1m
    ```

2. **Configure `values.yaml` for the Auto Mode GPU deployment.** In your `values.yaml` (from [values.yaml.template](values.yaml.template)):
    - Comment out the default **CPU deployment** four-line block and uncomment the **"GPU deployment with EKS Auto Mode / Karpenter"** block:

    ```yaml
    gpuEnabled: true
    genaiEngineDeploymentType: "deployment"
    genaiEngineWorkers: 2
    genaiEngineContainerImageLocation: "arthurplatform/genai-engine-gpu"
    ```

      `genaiEngineDeploymentType` is the key setting that distinguishes the two GPU topologies, so make sure you pick the Auto Mode block and not the managed-node-group one:

      | | `genaiEngineDeploymentType` | Why |
      | --- | --- | --- |
      | Managed node group + ASG | `"daemonset"` | One GPU pod per node; the ASG fills nodes as it scales the node group. |
      | **EKS Auto Mode / Karpenter** | **`"deployment"`** | Karpenter only provisions a node for an unschedulable **workload pod**, and will **not** scale up for a DaemonSet — so the engine must run as a Deployment whose pending pod is the scale-up trigger. |

      `gpuEnabled: true` and the `-gpu` image select the GPU build; `genaiEngineWorkers: 2` is the per-pod worker count (keep it low — each worker loads the full model suite onto the GPU).

    - Set the pod `nodeSelector` to the NodePool's label and add a toleration for the taint, and disable the HPA:

    ```yaml
    arthurGenaiEngineDeployment:
      genaiEnginePodNodeSelector:
        capability: gpu
      genaiEnginePodTolerations:
        - key: "nvidia.com/gpu"
          operator: "Exists"
          effect: "NoSchedule"
    arthurGenaiEngineHPA:
      enabled: false
    ```

    The `nodeSelector` is what makes the pod unschedulable on the general-purpose nodes, which is the signal that prompts Karpenter to provision a GPU node from the NodePool above. The chart grants the container GPU access via `NVIDIA_VISIBLE_DEVICES`, so no `nvidia.com/gpu` resource request is required in the pod spec.

3. **Scaling is automatic.** Unlike the managed node group path, there is no launch template, ASG, or CloudWatch alarm to configure — Karpenter adds a GPU node when a GenAI Engine pod is pending and removes it when the node is idle (per the NodePool's `disruption` policy). To run more replicas, increase `genaiEngineReplicaCount`; Karpenter provisions additional GPU nodes to fit the pending pods (up to the NodePool `limits`).

## Ingress and HTTPS

The chart creates a Kubernetes `Ingress` for the GenAI Engine, but it **does not install an
ingress controller** and does not provision DNS or certificates. You choose how TLS is
terminated based on how your cluster exposes services, then configure the `ingress` block and
`genaiEngineIngressURL` in your `values.yaml`.

> **Invariant:** `genaiEngineIngressURL`, the TLS certificate domain, and the DNS record must all
> be the **same hostname**. If they disagree, requests return `404` or a certificate error even
> though the pods are healthy.

### Option A — nginx ingress controller (default)

For classic EKS / self-managed clusters. Install an nginx ingress controller separately, then
terminate TLS at nginx with a Kubernetes TLS secret:

```bash
kubectl -n arthur create secret tls genai-engine-tls --cert=tls.crt --key=tls.key
```

```yaml
genaiEngineIngressURL: arthur-genai-engine.mydomain.com
ingress:
  className: "nginx"
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
  tls:
    - hosts:
        - arthur-genai-engine.mydomain.com   # must equal genaiEngineIngressURL
      secretName: genai-engine-tls
```

### Option B — AWS ALB (EKS Auto Mode / AWS Load Balancer Controller)

**EKS Auto Mode clusters have no nginx ingress controller** — they ship the AWS Load Balancer
Controller with a built-in `alb` IngressClass. Use it, and terminate TLS at the ALB with an
[AWS ACM](https://docs.aws.amazon.com/acm/) certificate whose domain equals
`genaiEngineIngressURL`. Do **not** set a `tls` block — TLS is handled by the ALB, not a
Kubernetes secret:

```yaml
genaiEngineIngressURL: arthur-genai-engine.mydomain.com
ingress:
  className: "alb"
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/ssl-redirect: "443"
    alb.ingress.kubernetes.io/certificate-arn: "arn:aws:acm:<region>:<account-id>:certificate/<cert-id>"
    alb.ingress.kubernetes.io/healthcheck-path: /health
```

> Do not mix classes and annotations. `nginx.ingress.kubernetes.io/*` annotations are ignored by
> the ALB controller, and `alb.ingress.kubernetes.io/*` annotations are ignored by nginx. If you
> switch `className`, remove the other controller's annotations. (When switching an existing
> release via `helm upgrade --reuse-values`, the old annotations are merged back in and must be
> cleared explicitly.)

### DNS + verification

After install, get the load balancer address and point DNS at it (a CNAME or Route53 ALIAS,
since the LB is a hostname — not a plain `A` record):

```bash
kubectl get ingress -n arthur
```

Then verify HTTPS end to end:

```bash
curl -sS https://arthur-genai-engine.mydomain.com/health
# {"message":"ok", ...}
```

## Using a private image repository

By default the chart pulls the GenAI Engine image from Docker Hub (`arthurplatform/genai-engine-cpu` or `arthurplatform/genai-engine-gpu`). If Docker Hub is not reachable from your cluster, mirror the image into your own container registry and point the chart at it.

1. **Mirror the image** into your registry. Use the CPU or GPU variant that matches your deployment; the tag is used verbatim, so you can keep the upstream version or re-tag it as you like:

    ```bash
    docker pull arthurplatform/genai-engine-cpu:<version>
    docker tag  arthurplatform/genai-engine-cpu:<version> <your-registry>/<path>/genai-engine-cpu:<tag>
    docker push <your-registry>/<path>/genai-engine-cpu:<tag>
    ```

2. **Create an image pull secret** — only if your registry requires authentication. This is the same standard Kubernetes `docker-registry` secret (type `kubernetes.io/dockerconfigjson`) used in the install steps below; just point `--docker-server` at your registry host:

    ```bash
    # WARNING: Do NOT set up secrets this way in production.
    #          Use a secure method such as sealed secrets and external secret store providers.
    kubectl -n arthur create secret docker-registry arthur-repository-credentials \
        --docker-server='<your-registry-host>' \
        --docker-username='<username>' \
        --docker-password='<password>' \
        --docker-email=''
    ```

3. **Point the chart at your registry** in `values.yaml`. Unlike ML Engine, the GenAI Engine image reference is assembled from just two fields — `<genaiEngineContainerImageLocation>:<genaiEngineVersion>` (one `:`) — so the entire repository path (registry host + org + image name) goes in `genaiEngineContainerImageLocation`:

    ```yaml
    # Full repository path INCLUDING the image name (cpu or gpu variant)
    genaiEngineContainerImageLocation: "<your-registry>/<path>/genai-engine-cpu"
    # The tag you pushed, used verbatim
    genaiEngineVersion: "<tag>"
    # Set to true only if the registry requires authentication
    containerRepositoryCredentialRequired: true
    # Name of the docker-registry secret from step 2
    imagePullSecretName: "arthur-repository-credentials"
    ```

    Example — for the image `myregistry.example.com/arthur/genai-engine-cpu:genai-engine_2.1.683`:

    | Field | Value |
    | --- | --- |
    | `genaiEngineContainerImageLocation` | `myregistry.example.com/arthur/genai-engine-cpu` |
    | `genaiEngineVersion` | `genai-engine_2.1.683` |

    > For a GPU deployment, mirror and reference the `genai-engine-gpu` image and keep the related GPU settings (`gpuEnabled`, `genaiEngineDeploymentType`, `genaiEngineWorkers`) as described in the [GPU deployment](#gpu-deployment) section.

You can verify the rendered image reference before installing:

```bash
helm template arthur-genai-engine oci://ghcr.io/arthur-ai/arthur-engine/charts/arthur-genai-engine \
    --version <version_number> -f values.yaml | grep 'image:'
# -> image: "myregistry.example.com/arthur/genai-engine-cpu:genai-engine_2.1.683"
```

## How to install GenAI Engine using Helm Chart

1. Create Kubernetes secrets
    ```bash
    # WARNING: Do NOT set up secrets this way in production.
    #          Use a secure method such as sealed secrets and external secret store providers.
    kubectl -n arthur create secret generic postgres-secret \
        --from-literal=username='<username>' \
        --from-literal=password='<password>'

    # Create this secret only if you have username and password to the container registry.
    # If you do, also make sure `containerRepositoryCredentialRequired` in
    # the `values.yaml` is set correctly.
    kubectl -n arthur create secret docker-registry arthur-repository-credentials \
        --docker-server='registry-1.docker.io' \
        --docker-username='<username>' \
        --docker-password='<password>' \
        --docker-email=''

    kubectl -n arthur create secret generic genai-engine-secret-admin-key \
        --from-literal=key='<key>'

    # Connection strings for Azure OpenAI GPT model endpoints (Many may be specified)
    # Must be in the form:
    # "DEPLOYMENT_NAME1::OPENAI_ENDPOINT1::SECRET_KEY1,DEPLOYMENT_NAME2::OPENAI_ENDPOINT2::SECRET_KEY2"
    kubectl -n arthur create secret generic genai-engine-secret-open-ai-gpt-model-names-endpoints-keys \
        --from-literal=keys='<your_gpt_keys>'

    # (Optional) GCP service account credentials for Vertex AI integration.
    # The secret key MUST be named 'credentials.json' — this becomes the filename
    # mounted inside the container at /var/secrets/google/credentials.json.
    # Set gcpDiscoveryConfig.isEnabled=true and gcpDiscoveryConfig.googleCredentialsSecretName
    # in your values.yaml to enable.
    kubectl -n arthur create secret generic gcp-sa-key \
        --from-file credentials.json='<path_to_your_gcp_service_account_key.json>'
    ```

2. Prepare an Arthur GenAI Engine Helm Chart configuration file, `values.yaml` from [values.yaml.template](values.yaml.template) in the directory where you will run Helm install and populate the values accordingly. For GPU deployment, please review the "Additional Required Configurations For GPU Deployment" section in the [values.yaml.template](values.yaml.template) file.

3. Install the Arthur GenAI Engine Helm Chart
    ```bash
    helm upgrade --install -n arthur -f values.yaml arthur-genai-engine oci://ghcr.io/arthur-ai/arthur-engine/charts/arthur-genai-engine --version <version_number>
    ```
4. Configure DNS to route `genaiEngineIngressURL` to the load balancer created for the ingress (find it with `kubectl get ingress -n arthur`). An AWS ALB/NLB is a hostname, so use a **CNAME** or a **Route53 ALIAS** record — not a plain `A` record. The DNS hostname, the TLS certificate domain, and `genaiEngineIngressURL` must all match. See [Ingress and HTTPS](#ingress-and-https).
5. Verify that all the pods are running with
    ```bash
    kubectl get pods -n arthur
    ```
    You should see the GenAI Engine pods in the running state. Please also inspect the log.

## FAQs

### The usage of my Azure OpenAI endpoint is going beyond my quota. What do I do?

Azure OpenAI has a quota called Tokens-per-Minute (TPM). It limits the number of tokens that a single model can
process within a minute in the region the model is deployed. In order to get a larger quota for GenAI Engine, you can deploy
additional models in other regions and have Arthur GenAI Engine round-robin against multiple Azure OpenAI endpoints. In
addition, you can request and get approved for a model quota increase in the desired regions by Azure.

### How do I load models from a shared volume instead of downloading them at startup?

`modelPVC.enabled` is the online/offline toggle. By default (`false`) GenAI Engine downloads its
model binaries from Hugging Face on startup (or fetches them from `modelRepositoryURL` if set), and
no PersistentVolumeClaim is required. For air-gapped clusters or to avoid per-pod downloads, set it
to `true` to pre-populate a shared volume once and have every replica load models offline from it:

```bash
--set modelPVC.enabled=true \
--set modelPVC.claimName=arthur-models-pvc \
--set modelPVC.mountPath=/home/nonroot/models-output
```

When enabled, the chart mounts the claim (read-write — see below) and sets `MODEL_STORAGE_PATH` +
`HF_HUB_OFFLINE=1`, and the engine skips the startup download. Populate the volume with the one-time
job in [../../model-upload](../../model-upload). On AWS EKS, back the `ReadWriteMany` PVC with EFS by
following the [AWS EKS + EFS](../../model-upload/README.md#aws-eks--efs) section of that guide.

> The mount must be **read-write** (`modelPVC.readOnly` defaults to `false`). The HuggingFace
> loaders write `.lock`/cache files under the mount even with `HF_HUB_OFFLINE=1`, so a read-only
> mount fails with `[Errno 30] Read-only file system`.
