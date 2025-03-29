# Arthur GenAI Engine Helm Chart Deployment Guide

## Pre-requisites

### Engine Version
Look up an engine version to use from the [Releases](https://github.com/arthur-ai/arthur-engine/releases).

### Helm
* Install Helm on your workstation. Helm version 3.8.0 or higher is required
* The Arthur Engine Helm charts are hosted in the OCI format as [GitHub packages](https://github.com/arthur-ai/arthur-engine/pkgs/container/arthur-engine%2Fcharts%2Farthur-engine)
  ```bash
  helm show chart oci://ghcr.io/arthur-ai/arthur-engine/charts/arthur-engine:<version_number>
  ```

### OpenAI GPT Model
Arthur GenAI Engine's hallucination and sensitive data rules require an OpenAI GPT model for running evaluations.
Please review the GPT model requirements below:
* An OpenAI GPT model with at least one endpoint. GenAI Engine supports Azure and OpenAI as the LLM service provider.
* A secure network route between your environment and the OpenAI endpoint(s)
* Token limits, configured appropriately for your use cases

### DNS
A DNS URL for GenAI Engine with a SSL certificate

### Kubernetes
The chart is tested on AWS Elastic Kubernetes Service (EKS) version 1.31.

* A `kubectl` workstation with admin privileges
* Nginx ingress controller
* A dedicated namespace (e.g. `arthur`)
* For CPU deployment: a node group with AWS `m8g.large` x 2 or similar
  * Memory: 16 GiB
  * CPU: 4 cores
  * Metrics server
* For GPU deployment: a node group with AWS `g4dn.2xlarge` x 2 or similar
  * Memory: 64 GiB
  * CPU: 16 cores
  * GPU: 2 cores

### Postgres database
The GenAI Engine is tested on PostgreSQL 15. Using a managed Postgres database is recommended.
Please pre-create a database on your instance (e.g. `arthur_genai_engine`)

### Container Image Repository Access
* There must be a network route available to connect to Docker Hub
* If Docker Hub access is not an option, you can push the images from Docker Hub to your private container registry and provide its access information in the `values.yaml` file

# How to configure your AWS EKS cluster with a GPU node group
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

4. Look up the AMI ID for the latest GPU optimized AMI
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

# How to install GenAI Engine using Helm Chart

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
        --from-literal=key='<api_key>'

    # Connection strings for Azure OpenAI GPT model endpoints (Many may be specified)
    # Must be in the form:
    # "DEPLOYMENT_NAME1::OPENAI_ENDPOINT1::SECRET_KEY1,DEPLOYMENT_NAME2::OPENAI_ENDPOINT2::SECRET_KEY2"
    kubectl -n arthur create secret generic genai-engine-secret-open-ai-gpt-model-names-endpoints-keys \
        --from-literal=keys='<your_gpt_keys>'
    ```

2. Prepare a copy of the Arthur GenAI Engine Helm Chart configuration file, [values.yaml](values.yaml) in the directory where you will run `helm install` and populate the values accordingly:

3. Install the Arthur GenAI Engine Helm Chart
    ```bash
    helm upgrade --install -n arthur -f genai-values.yaml arthur-engine oci://ghcr.io/arthur-ai/arthur-engine/charts/arthur-engine --version <version_number>
    ```
4. Configure DNS by create an `A` record that routes the Arthur GenAI Engine service ingress DNS URL to the GenAI Engine load balancer created
    by the ingress.
5. Verify that all the pods are running with
    ```bash
    kubectl get pods -n arthur
    ```
    You should see the GenAI Engine pods in the running state. Please also inspect the log.

# FAQs

### The usage of my Azure OpenAI endpoint is going beyond my quota. What do I do?

Azure OpenAI has a quota called Tokens-per-Minute (TPM). It limits the number of tokens that a single model can
process within a minute in the region the model is deployed. In order to get a larger quota for GenAI Engine, you can deploy
additional models in other regions and have Arthur GenAI Engine round-robin against multiple Azure OpenAI endpoints. In
addition, you can request and get approved for a model quota increase in the desired regions by Azure.
