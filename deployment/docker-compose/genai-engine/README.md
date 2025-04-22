# Arthur GenAI Engine Docker Compose Deployment Guide

## TLDR - Quick Start

1. Create `.env` file from `.env.template` file and modify it
2. Run `docker compose up`
3. Wait for the containers to initialize then navigate to localhost:3000/docs to see the API docs

* Depending on your environment, Pytorch package wheel might not be available (e.g. Intel chip Mac).
* You might need to change the `image` and the `platform` configurations in the `docker-compose.yml` depending on your environment.
* When the `GENAI_ENGINE_VERSION` environment variable is not set, the `latest` stable image is used (not recommended). When `latest` is used, make sure to run `docker compose pull` first to get the most recent `latest` tagged image.

## Prerequisites

### Engine Version
Look up an engine version to use from the [Releases](https://github.com/arthur-ai/arthur-engine/releases).

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
2. Create `.env` file from `.env.template` file and modify it
3. Navigate to the `docker-compose` directory on your terminal and run `docker compose up`
   ```
       export GENAI_ENGINE_VERSION=<genai_engine_version>
       docker compose up
   ```
4. Access the GenAI Engine's interactive API documentation at [http://localhost:3000/docs](http://localhost:3000/docs)

## Steps for Windows (with Powershell)
1. Install and run Docker for Windows
2. Create `.env` file from `.env.template` file and modify it
3. Navigate to the `docker-compose` directory on your terminal and run `docker compose up`
    ```
        $env:GENAI_ENGINE_VERSION = "<genai_engine_version>"
        docker compose up
    ```
4. Access the GenAI Engine's interactive API documentation at [http://localhost:3000/docs](http://localhost:3000/docs)
