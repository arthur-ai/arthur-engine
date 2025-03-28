# Arthur GenAI Engine Docker Compose Deployment Guide

## TLDR - Quick Start

1. Copy `*.env.template` files and modify them
2. Run `docker compose up`
3. Wait for the `genai-engine` container to initialize then navigate to localhost:3000/docs to see the API docs

* Depending on your environment, Pytorch package wheel might not be available (e.g. Intel chip Mac).
* You might need to change the `image` and the `platform` configurations in the `docker-compose.yml` depending on your environment.
* When `GENAI_ENGINE_VERSION` environment variable is not set, `latest` stable image is used. When `latest` is used, make sure to run `docker compose pull` first to get the latest of the `latest` tagged image.

## Prerequisites

### Engine Version
Look up an engine version to use from the [Releases](https://github.com/arthur-ai/arthur-engine-temp/releases).

### OpenAI GPT Model
Arthur's GenAI Engine hallucination and sensitive data rules require an OpenAI-compatible GPT model for running evaluations.

Please review the GPT model requirements below:

- An OpenAI-compatible GPT model with at least one endpoint. The GenAI Engine supports Azure and OpenAI as the LLM service provider.
  - Note: If using OpenAI's APIs directly, the endpoint can be inferred by leaving the `base_url` part of the configuration empty
- A secure network route between your environment and the OpenAI endpoint(s)
- Token limits, configured appropriately for your use cases

### Container Image Repository Access
- There must be a network route available to connect to Docker Hub
- If Docker Hub access is not an option, you can push the images from Docker Hub to your private container registry and provide its access information in the Docker Compose script

## Steps for Mac
1. Install and run Docker for Mac
2. Copy the `.env.template` files as `.env` files in the `docker-compose` folder
3. Configure the `.env` files
4. Navigate to the `docker-compose` directory on your terminal and run `docker compose up`
   ```
       export GENAI_ENGINE_VERSION=<genai_enginve_version>
       docker compose up
   ```
5. Access the GenAI Engine API interactive documentation via a web browser at [http://localhost:3000/docs](http://localhost:3000/docs)

## Steps for Windows (with Powershell)
1. Install and run Docker for Windows
2. Copy the `.env.template` files as `.env` files in the `docker-compose` folder
3. Configure the `.env` files
4. Navigate to the `docker-compose` directory on your terminal and run `docker compose up`
    ```
        $env:GENAI_ENGINE_VERSION = "<genai_enginve_version>"
        docker-compose up
    ```
5. Access the GenAI Engine API interactive documentation via a web browser at [http://localhost:3000/docs](http://localhost:3000/docs)
