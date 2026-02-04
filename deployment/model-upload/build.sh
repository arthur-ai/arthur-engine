#!/bin/bash
# Build script for unified model upload images
# Builds backend-specific images with appropriate tags

set -e

# Default values
VERSION="${VERSION:-latest}"
REGISTRY="${REGISTRY:-arthurplatform}"
IMAGE_BASE="${IMAGE_BASE:-genai-engine-models}"
PUSH="${PUSH:-false}"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_usage() {
    cat << EOF
Build unified model upload Docker images for different backends

Usage: $0 [OPTIONS] BACKEND

BACKEND:
    s3          Build for AWS S3 (distroless runtime)
    gcs         Build for Google Cloud Storage (slim runtime)
    k8s         Build for Kubernetes PVC (distroless runtime)
    all         Build all three backends

OPTIONS:
    --version VERSION    Version tag (default: latest)
    --registry REGISTRY  Docker registry (default: arthurplatform)
    --push              Push images after building
    -h, --help          Show this help message

EXAMPLES:
    # Build S3 variant
    $0 s3

    # Build all variants with custom version
    $0 --version 2.1.343 all

    # Build and push GCS variant
    $0 --push --version 2.1.343 gcs

ENVIRONMENT VARIABLES:
    VERSION     Override version tag
    REGISTRY    Override registry name
    PUSH        Set to "true" to push after build
EOF
}

build_image() {
    local backend=$1
    local target=$2
    local tag_suffix=$3

    local image_tag="${REGISTRY}/${IMAGE_BASE}:${VERSION}-${tag_suffix}"

    echo -e "${BLUE}===================================================${NC}"
    echo -e "${BLUE}Building ${backend} image${NC}"
    echo -e "${BLUE}Tag: ${image_tag}${NC}"
    echo -e "${BLUE}Target: ${target}${NC}"
    echo -e "${BLUE}===================================================${NC}"

    docker build \
        --build-arg BACKEND="${backend}" \
        --target "${target}" \
        -t "${image_tag}" \
        .

    echo -e "${GREEN}✓ Built ${image_tag}${NC}"

    # Also tag as latest-<backend>
    local latest_tag="${REGISTRY}/${IMAGE_BASE}:latest-${tag_suffix}"
    docker tag "${image_tag}" "${latest_tag}"
    echo -e "${GREEN}✓ Tagged as ${latest_tag}${NC}"

    if [ "$PUSH" = "true" ]; then
        echo -e "${BLUE}Pushing ${image_tag}...${NC}"
        docker push "${image_tag}"
        docker push "${latest_tag}"
        echo -e "${GREEN}✓ Pushed ${image_tag}${NC}"
    fi

    echo ""
}

# Parse arguments
BACKEND=""
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
        s3|gcs|k8s|all)
            BACKEND="$1"
            shift
            ;;
        *)
            echo -e "${RED}Error: Unknown argument: $1${NC}"
            print_usage
            exit 1
            ;;
    esac
done

# Validate backend argument
if [ -z "$BACKEND" ]; then
    echo -e "${RED}Error: BACKEND argument is required${NC}"
    print_usage
    exit 1
fi

# Build requested backends
case $BACKEND in
    s3)
        build_image "s3" "runtime-distroless" "s3"
        ;;
    gcs)
        build_image "gcs" "runtime-slim" "gcs"
        ;;
    k8s)
        build_image "filesystem" "runtime-distroless" "k8s"
        ;;
    all)
        build_image "s3" "runtime-distroless" "s3"
        build_image "gcs" "runtime-slim" "gcs"
        build_image "filesystem" "runtime-distroless" "k8s"
        ;;
    *)
        echo -e "${RED}Error: Invalid backend: $BACKEND${NC}"
        exit 1
        ;;
esac

echo -e "${GREEN}===================================================${NC}"
echo -e "${GREEN}✓ Build complete!${NC}"
echo -e "${GREEN}===================================================${NC}"

if [ "$PUSH" != "true" ]; then
    echo -e "${BLUE}Tip: Use --push to push images to registry${NC}"
fi
