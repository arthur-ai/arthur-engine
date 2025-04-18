#!/bin/bash

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# Load environment variables from a .env file if provided
if [ -n "$1" ] && [ -f "$1" ]; then
    echo "Loading environment variables from $1"
    source "$1"
else
    echo "No .env file provided or file does not exist. Proceeding with manual input."
    # Decide which type of GenAI Engine to start

    # Prompt the user to choose between GPU and CPU
    read -p "Which version of the GenAI Engine would you like to run? (GPU/CPU): " engine_type

    # Validate the input
    if [[ "$engine_type" == "GPU" || "$engine_type" == "CPU" ]]; then
        echo "Starting the GenAI Engine with $engine_type support..."
        # Add the command to start the engine with the selected option here
    else
        echo "Invalid option. Please choose either 'GPU' or 'CPU'."
        exit 1
    fi

    # Prompt for variables with defaults
    read -p "Enter Kubernetes Namespace [arthur]: " K8S_NAMESPACE
    K8S_NAMESPACE=${K8S_NAMESPACE:-arthur}

    read -p "Enter environment suffix [None]: " ENV_SUFFIX

    read -p "Enter Postgres User [arthur_genai_engine]: " POSTGRES_USER
    POSTGRES_USER=${POSTGRES_USER:-arthur_genai_engine}

    read -p "Enter Postgres Password [changeme_pg_password]: " POSTGRES_PASSWORD
    POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-changeme_pg_password}

    read -p "Enter Postgres Endpoint [mydb]: " POSTGRES_ENDPOINT
    POSTGRES_ENDPOINT=${POSTGRES_ENDPOINT:-mydb}

    read -p "Enter GenAI Engine Version [latest]: " GENAI_ENGINE_VERSION
    GENAI_ENGINE_VERSION=${GENAI_ENGINE_VERSION:-latest}

    read -p "Enter GenAI Engine Admin Key [changeme_genai_engine_admin_key]: " GENAI_ENGINE_ADMIN_KEY
    GENAI_ENGINE_ADMIN_KEY=${GENAI_ENGINE_ADMIN_KEY:-changeme_genai_engine_admin_key}

    read -p "Enter GenAI Engine OpenAI Provider [Azure]: " GENAI_ENGINE_OPENAI_PROVIDER
    GENAI_ENGINE_OPENAI_PROVIDER=${GENAI_ENGINE_OPENAI_PROVIDER:-Azure}

    read -p "Enter GenAI Engine OpenAI GPT Names Endpoints Keys [model_name::https://my_service.openai.azure.com/::my_api_key]: " GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS
    GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS=${GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS:-model_name::https://my_service.openai.azure.com/::my_api_key}

    read -p "Enter GenAI Engine Ingress URL [genai-engine.mycompany.ai]: " GENAI_ENGINE_INGRESS_URL
    GENAI_ENGINE_INGRESS_URL=${GENAI_ENGINE_INGRESS_URL:-genai-engine.mycompany.ai}

    read -p "Enter ML Engine Arhur API Host [https://platform.arthur.ai]: " ML_ENGINE_ARTHUR_API_HOST
    ML_ENGINE_ARTHUR_API_HOST=${ML_ENGINE_ARTHUR_API_HOST:-https://platform.arthur.ai}

    read -p "Enter ML Engine Version [latest]: " ML_ENGINE_VERSION
    ML_ENGINE_VERSION=${ML_ENGINE_VERSION:-latest}

    read -p "Enter ML Engine Client ID: " ML_ENGINE_CLIENT_ID

    read -p "Enter ML Engine Client Secret: " ML_ENGINE_CLIENT_SECRET
fi

# Create Kubernetes secrets
# TODO: Secret will not be overwritten if it already exists
kubectl -n $K8S_NAMESPACE create secret generic postgres-secret \
    --from-literal=username=$POSTGRES_USER \
    --from-literal=password=$POSTGRES_PASSWORD
kubectl -n $K8S_NAMESPACE create secret generic genai-engine-secret-admin-key \
    --from-literal=key=$GENAI_ENGINE_ADMIN_KEY
kubectl -n $K8S_NAMESPACE create secret generic genai-engine-secret-open-ai-gpt-model-names-endpoints-keys \
    --from-literal=keys=$GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS

CLIENT_SECRET_BASE64=$(echo -n $ML_ENGINE_CLIENT_SECRET | base64)
kubectl -n $K8S_NAMESPACE create secret generic ml-engine-secrets \
    --from-literal=client_secret=$CLIENT_SECRET_BASE64

if [[ "$engine_type" == "GPU" ]]; then
    helm upgrade --install arthur-parent-chart $SCRIPT_DIR \
    --namespace $K8S_NAMESPACE \
    --set genaiEngineVersion=$GENAI_ENGINE_VERSION \
    --set postgresBYOEndpoint=$POSTGRES_ENDPOINT \
    --set genaiEngineIngressURL=$GENAI_ENGINE_INGRESS_URL \
    --set genaiEngineOpenAIProvider=$GENAI_ENGINE_OPENAI_PROVIDER \
    --set gpuEnabled=true \
    --set genaiEngineDeploymentType=daemonset \
    --set genaiEngineWorkers=5 \
    --set genaiEngineContainerImageLocation=arthurplatform/genai-engine-gpu \
    --set mlEngine.deployment.appPlaneUrl=$ML_ENGINE_ARTHUR_API_HOST \
    --set mlEngine.deployment.clientId=$ML_ENGINE_CLIENT_ID \
    --set mlEngine.deployment.version=$ML_ENGINE_VERSION \
    --set mlEngine.deployment.containerImageVersion=$ML_ENGINE_VERSION \
    --set mlEngine.namespace=$K8S_NAMESPACE \
    --set env.suffix=$ENV_SUFFIX
else
    helm upgrade --install arthur-parent-chart $SCRIPT_DIR \
    --namespace $K8S_NAMESPACE \
    --set arthur-engine.genaiEngineVersion=$GENAI_ENGINE_VERSION \
    --set arthur-engine.postgresBYOEndpoint=$POSTGRES_ENDPOINT \
    --set arthur-engine.genaiEngineIngressURL=$GENAI_ENGINE_INGRESS_URL \
    --set arthur-engine.genaiEngineOpenAIProvider=$GENAI_ENGINE_OPENAI_PROVIDER \
    --set arthur-engine.gpuEnabled=false \
    --set arthur-engine.genaiEngineDeploymentType=deployment \
    --set arthur-engine.genaiEngineWorkers=1 \
    --set arthur-engine.genaiEngineContainerImageLocation=arthurplatform/genai-engine-cpu \
    --set ml-engine.mlEngine.deployment.appPlaneUrl=$ML_ENGINE_ARTHUR_API_HOST \
    --set ml-engine.mlEngine.deployment.clientId=$ML_ENGINE_CLIENT_ID \
    --set ml-engine.mlEngine.deployment.version=$ML_ENGINE_VERSION \
    --set ml-engine.mlEngine.deployment.containerImageVersion=$ML_ENGINE_VERSION \
    --set ml-engine.namespace=$K8S_NAMESPACE \
    --set env.suffix=$ENV_SUFFIX
fi
