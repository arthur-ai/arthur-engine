Create a new top level skill called "arthur-onboard-platform". This will offer a new Claud Code skill that helps
onboard users to an Arthur Platform. This skill leverages some of the modularized skills used by the "arthur-onboard-oss" skill.
Reference the API doc (https://platform.arthur.ai/api/docs) for performing onboarding tasks.
Follow the same implementation design of Claude skills as "arthur-onboard-oss". "arthur-onboard-platform" should be implemented as
the orchestrator. If new modular skills are necessary to accomplish the tasks for "arthur-onboard-platform", add new modules.

## Pre-flight Checks
Use the same checks in "arthur-onboard-oss" skill.

## Identify the correct Arthur Platform
Verify that user wants to onboard Arthur SaaS at https://platform.arthur.ai/.
If not, ask where the Arthur Platform is located.

## Get access to the Arthur Platform
Have the user sign up to the platform, create a service account, and provide the credentials.
To create a service account, click on the grid icon located at the top right of the UI next to the profile icon with user name initials
to find the "Identity & Access" menu. Once you're on the "Identity & Access" page, click the "Users" tab. Click the "+ USER" and
follow the form to create a new "Service Account".
Instruct the user to practice least priviledge model when assigning groups or roles to the service account.
For the first time onboarding experience, the user might want to start with using the Organization Admin role.
However, a more experienced user who wants to use the onboard skill to add just an application should give the service account
less permissions.
Use the service account credentials to perform the rest of the onboarding tasks that require platform access.
For development, use the following client ID and client secret:
Client ID: arthur-sa-0bc27012-c07a-44de-ac19-5b86e3cf3a70
Client Secret: Jv-xRewmgnorTMwgEId1bje-BYBF5iN5EUtVefxM5Uc

## Select workspace in the Arthur Platform to work with
Select or create a desired workspace to work in.

## Ensure there's an Arthur Engine (ml-engine + genai-engine) registered with the platform
Ensure an active engine is available to the user. You can look up existing engines registered to the desired workspace via platform API.
The genai-engines installed with the "arthur-onboard-oss" are not compatible with the platform.
If ones exist already, ask the user if one of them is the one he/she wants to use.
If not, offer to deploy a new one. Availble options are:

### Docker Compose
https://github.com/arthur-ai/arthur-engine/tree/dev/deployment/docker-compose/arthur-engine
The engine.arthur.ai URL maps to the setup-and-start scripts:
* https://github.com/arthur-ai/arthur-engine/blob/dev/deployment/docker-compose/arthur-engine/setup-and-start.sh
* https://github.com/arthur-ai/arthur-engine/blob/dev/deployment/docker-compose/arthur-engine/setup-and-start.ps1

For Mac:
```
bash <(curl -sSL https://engine.arthur.ai/mac) \
  --arthur-client-id=client_id \
  --arthur-client-secret=client_secret \
  --arthur-api-host=platform_url (e.g. https://platform.arthur.ai) \
  --fetch-raw-data-enabled=true \
  --default-genai-config=false
```

For Windows:
```
& ([scriptblock]::Create((Invoke-WebRequest "https://engine.arthur.ai/win" -UseBasicParsing).Content)) `
  --arthur-client-id=data-plane-96470fed-66f2-4a49-9f5e-efc1fe999c62 `
  --arthur-client-secret=lAJ5bC5UCFt5fI7r3CKl2OtypebKj2aIeys8vUX-Kk8 `
  --arthur-api-host=https://platform.arthur.ai `
  --fetch-raw-data-enabled=true `
  --default-genai-config=false
```

### AWS Cloudformation
The install scripts on the S3 can be found in git also (https://github.com/arthur-ai/arthur-engine/tree/dev/deployment/cloudformation):
* https://github.com/arthur-ai/arthur-engine/blob/dev/deployment/cloudformation/root-arthur-engine-cpu.yml
* https://github.com/arthur-ai/arthur-engine/blob/dev/deployment/cloudformation/root-arthur-engine-gpu.yml

Deploy with CPUs only:
https://us-east-2.console.aws.amazon.com/cloudformation/home?region=us-east-2#/stacks/quickcreate?templateURL=https://arthur-cft.s3.us-east-2.amazonaws.com/arthur-engine/templates/0.0.9-lts/root-arthur-engine-cpu.yml&stackName=arthur-engine&param_MLEngineClientId=data-plane-ac586f7c-6661-434c-89b4-89c5287bf90f

Deploy with GPUs:
https://us-east-2.console.aws.amazon.com/cloudformation/home?region=us-east-2#/stacks/quickcreate?templateURL=https://arthur-cft.s3.us-east-2.amazonaws.com/arthur-engine/templates/0.0.9-lts/root-arthur-engine-gpu.yml&stackName=arthur-engine&param_MLEngineClientId=data-plane-ac586f7c-6661-434c-89b4-89c5287bf90f

### Kubernetes
https://github.com/arthur-ai/arthur-engine/tree/dev/deployment/helm/arthur-engine

Deploy with CPUs only:
```
#!/bin/bash

K8S_NAMESPACE=arthur
ARTHUR_ENGINE_VERSION=0.0.9-lts
POSTGRES_USER=arthur_genai_engine
POSTGRES_PASSWORD=changeme_pg_password
POSTGRES_ENDPOINT=mydb
GENAI_ENGINE_ADMIN_KEY=changeme_genai_engine_admin_key
GENAI_ENGINE_OPENAI_PROVIDER=Azure
GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS=model_name::https://my_service.openai.azure.com/::my_api_key
GENAI_ENGINE_INGRESS_URL=YOUR_INGRESS_URL_HERE
ML_ENGINE_CLIENT_ID=data-plane-11f88739-8a43-4460-b445-9ec7ef151717
ML_ENGINE_CLIENT_SECRET=7D18_zaPEF3aECWPsZVk69HwjXGtITMryshH32lTibw

kubectl -n $K8S_NAMESPACE create secret generic postgres-secret \
    --from-literal=username=$POSTGRES_USER \
    --from-literal=password=$POSTGRES_PASSWORD
kubectl -n $K8S_NAMESPACE create secret generic genai-engine-secret-admin-key \
    --from-literal=key=$GENAI_ENGINE_ADMIN_KEY
kubectl -n $K8S_NAMESPACE create secret generic genai-engine-secret-open-ai-gpt-model-names-endpoints-keys \
    --from-literal=keys=$GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS
kubectl -n arthur create secret generic ml-engine-client-secret \
    --from-literal=client_id=$ML_ENGINE_CLIENT_ID \
    --from-literal=client_secret=$ML_ENGINE_CLIENT_SECRET

mkdir -p tmp
curl -o "tmp/values.yaml" "https://raw.githubusercontent.com/arthur-ai/arthur-engine/refs/heads/main/deployment/helm/arthur-engine/values.yaml.template"
curl -o "tmp/Chart.yaml" "https://raw.githubusercontent.com/arthur-ai/arthur-engine/refs/heads/main/deployment/helm/arthur-engine/Chart.yaml"
cd tmp
helm dependency update
helm upgrade --install -n $K8S_NAMESPACE -f values.yaml arthur-engine . \
--set arthur-genai-engine.genaiEngineVersion=$ARTHUR_ENGINE_VERSION \
--set arthur-genai-engine.postgresBYOEndpoint=$POSTGRES_ENDPOINT \
--set arthur-genai-engine.genaiEngineIngressURL=$GENAI_ENGINE_INGRESS_URL \
--set arthur-genai-engine.genaiEngineOpenAIProvider=$GENAI_ENGINE_OPENAI_PROVIDER \
--set arthur-ml-engine.mlEngine.deployment.genaiEngineInternalIngressHost=$GENAI_ENGINE_INGRESS_URL
```

Deploy with GPUs:
```
#!/bin/bash

K8S_NAMESPACE=arthur
ARTHUR_ENGINE_VERSION=0.0.9-lts
POSTGRES_USER=arthur_genai_engine
POSTGRES_PASSWORD=changeme_pg_password
POSTGRES_ENDPOINT=mydb
GENAI_ENGINE_ADMIN_KEY=changeme_genai_engine_admin_key
GENAI_ENGINE_OPENAI_PROVIDER=Azure
GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS=model_name::https://my_service.openai.azure.com/::my_api_key
GENAI_ENGINE_INGRESS_URL=YOUR_INGRESS_URL_HERE
ML_ENGINE_CLIENT_ID=data-plane-11f88739-8a43-4460-b445-9ec7ef151717
ML_ENGINE_CLIENT_SECRET=7D18_zaPEF3aECWPsZVk69HwjXGtITMryshH32lTibw

kubectl -n $K8S_NAMESPACE create secret generic postgres-secret \
    --from-literal=username=$POSTGRES_USER \
    --from-literal=password=$POSTGRES_PASSWORD
kubectl -n $K8S_NAMESPACE create secret generic genai-engine-secret-admin-key \
    --from-literal=key=$GENAI_ENGINE_ADMIN_KEY
kubectl -n $K8S_NAMESPACE create secret generic genai-engine-secret-open-ai-gpt-model-names-endpoints-keys \
    --from-literal=keys=$GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS
kubectl -n arthur create secret generic ml-engine-client-secret \
    --from-literal=client_id=$ML_ENGINE_CLIENT_ID \
    --from-literal=client_secret=$ML_ENGINE_CLIENT_SECRET

mkdir -p tmp
curl -o "tmp/values.yaml" "https://raw.githubusercontent.com/arthur-ai/arthur-engine/refs/heads/main/deployment/helm/arthur-engine/values.yaml.template"
curl -o "tmp/Chart.yaml" "https://raw.githubusercontent.com/arthur-ai/arthur-engine/refs/heads/main/deployment/helm/arthur-engine/Chart.yaml"
cd tmp
helm dependency update
helm upgrade --install -n $K8S_NAMESPACE -f values.yaml arthur-engine . \
--set arthur-genai-engine.genaiEngineVersion=$ARTHUR_ENGINE_VERSION \
--set arthur-genai-engine.postgresBYOEndpoint=$POSTGRES_ENDPOINT \
--set arthur-genai-engine.genaiEngineIngressURL=$GENAI_ENGINE_INGRESS_URL \
--set arthur-genai-engine.genaiEngineOpenAIProvider=$GENAI_ENGINE_OPENAI_PROVIDER \
--set arthur-genai-engine.gpuEnabled=true \
--set arthur-genai-engine.genaiEngineDeploymentType=daemonset \
--set arthur-genai-engine.genaiEngineWorkers=5 \
--set arthur-genai-engine.genaiEngineContainerImageLocation=arthurplatform/genai-engine-gpu \
--set arthur-ml-engine.mlEngine.deployment.genaiEngineInternalIngressHost=$GENAI_ENGINE_INGRESS_URL
```

Make sure the engine is reporting active on the platform. If not, help the user troubleshoot.
Also make sure to memorize the engine API key and the engine URL. Make sure the API key works.

## Determine which type of application (model) the user wants to onboard
If an "Agentic Model", continue to the next steps in the skill
If "ML Model" or "Gen AI Model", instruct the user to login to the platform UI and onboard it via the "Applications" section then exit the skill

## Add an Agentic Model on the platform
Add an agentic model on the platform with the user's selected engine. Upon model creation, memorize the task ID created.

## Detect language, framework, existing instrumentation
Use the existing "arthur-onboard-analyze" skill.

## Instrument code (Python SDK, Mastra TS, or OpenInference)
Use the existing "arthur-onboard-instrument" skill.

## Extract & register prompts
Use the existing "arthur-onboard-promopts" skill

## Verify traces are flowing
Use the existing "arthur-onboard-verify" skill

## Configure LLM eval model provider
Use the existing "arthur-onboard-eval-provider" skill

## Recommend & create continuous evals
Use the existing "arthur-onboard-evals" skill
