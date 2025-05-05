# Arthur GenAI Engine Docker Compose Deployment Guide

## TLDR - Quick Start

1. Copy `.env.template` file and modify it
2. Run `docker compose up`
3. Monitor the logs to see the ml-engine poll and process jobs from the API Host.

* Make sure to run `docker compose pull` first to get the most recent`latest` tagged image.
* You might need to change the `image` and the `platform` configurations in the `docker-compose.yml` depending on your environment.

## Prerequisites

### Container Image Repository Access
- There must be a network route available to connect to Docker Hub
- If Docker Hub access is not an option, you can push the images from Docker Hub to your private container registry and provide its access information in the Docker Compose script

## Steps
1. Install and run Docker for Mac
2. Create `.env` file from `.env.template` file and modify it
3. Navigate to the `docker-compose` directory on your terminal and run `docker compose up`
   ```
       docker compose up --pull always
   ```
