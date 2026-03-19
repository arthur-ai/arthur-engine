#!/bin/bash
# Build script for unified model upload image

set -e

VERSION="${VERSION:-latest}"
REGISTRY="${REGISTRY:-arthurplatform}"
IMAGE_BASE="${IMAGE_BASE:-genai-engine-models}"
PUSH="${PUSH:-false}"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_usage() {
    cat << EOF
Build the unified model upload Docker image

Usage: $0 [OPTIONS]

OPTIONS:
    --version VERSION    Version tag (default: latest)
    --registry REGISTRY  Docker registry (default: arthurplatform)
    --push              Push image after building
    -h, --help          Show this help message

EXAMPLES:
    # Build with default tag
    $0

    # Build with custom version
    $0 --version 2.1.345

    # Build and push
    $0 --push --version 2.1.345

ENVIRONMENT VARIABLES:
    VERSION     Override version tag
    REGISTRY    Override registry name
    PUSH        Set to "true" to push after build
EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --version)
            VERSION="$2"
            shift 2
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --push)
            PUSH="true"
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown argument: $1${NC}"
            print_usage
            exit 1
            ;;
    esac
done

IMAGE_TAG="${REGISTRY}/${IMAGE_BASE}:${VERSION}"

echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}Building unified model upload image${NC}"
echo -e "${BLUE}Tag: ${IMAGE_TAG}${NC}"
echo -e "${BLUE}===================================================${NC}"

docker build \
    --target runtime \
    -t "${IMAGE_TAG}" \
    .

echo -e "${GREEN}✓ Built ${IMAGE_TAG}${NC}"

# Also tag as latest
if [ "$VERSION" != "latest" ]; then
    LATEST_TAG="${REGISTRY}/${IMAGE_BASE}:latest"
    docker tag "${IMAGE_TAG}" "${LATEST_TAG}"
    echo -e "${GREEN}✓ Tagged as ${LATEST_TAG}${NC}"
fi

if [ "$PUSH" = "true" ]; then
    echo -e "${BLUE}Pushing ${IMAGE_TAG}...${NC}"
    docker push "${IMAGE_TAG}"
    if [ "$VERSION" != "latest" ]; then
        docker push "${LATEST_TAG}"
    fi
    echo -e "${GREEN}✓ Pushed${NC}"
fi

echo -e "${GREEN}===================================================${NC}"
echo -e "${GREEN}✓ Build complete!${NC}"
echo -e "${GREEN}===================================================${NC}"

if [ "$PUSH" != "true" ]; then
    echo -e "${BLUE}Tip: Use --push to push image to registry${NC}"
fi
