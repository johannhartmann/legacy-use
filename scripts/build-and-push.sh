#!/bin/bash
# Script to build and push images to local registry (useful for manual builds)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REGISTRY="localhost:5001"
IMAGES=(
    "legacy-use-mgmt:infra/docker/legacy-use-mgmt/Dockerfile"
    "legacy-use-mcp-server:infra/docker/legacy-use-mcp/Dockerfile"
    "legacy-use-wine-target:infra/docker/legacy-use-wine-target/Dockerfile"
    "linux-machine:infra/docker/linux-machine/Dockerfile"
    "legacy-use-android-target:infra/docker/legacy-use-android-target/Dockerfile"
)

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

check_registry() {
    log "Checking local registry..."
    
    # Check if registry is running
    if [ "$(docker inspect -f '{{.State.Running}}' "kind-registry" 2>/dev/null || true)" != 'true' ]; then
        error "Local registry 'kind-registry' is not running."
        error "Run ./scripts/kind-setup-with-registry.sh first."
        exit 1
    fi
    
    # Test registry connectivity
    if ! curl -s -o /dev/null -w "%{http_code}" "http://${REGISTRY}/v2/" | grep -q "200"; then
        error "Cannot connect to registry at ${REGISTRY}"
        exit 1
    fi
    
    log "Registry is accessible at ${REGISTRY}"
}

build_and_push_image() {
    local image_spec="$1"
    local image_name="${image_spec%%:*}"
    local dockerfile="${image_spec#*:}"
    local full_image="${REGISTRY}/${image_name}:latest"
    
    log "Building ${image_name}..."
    
    # Change to project root
    cd "$(dirname "$0")/.."
    
    # Build image
    if docker build -t "$full_image" -f "$dockerfile" .; then
        log "Successfully built ${image_name}"
    else
        error "Failed to build ${image_name}"
        return 1
    fi
    
    # Push to registry
    log "Pushing ${image_name} to registry..."
    if docker push "$full_image"; then
        log "Successfully pushed ${image_name}"
    else
        error "Failed to push ${image_name}"
        return 1
    fi
    
    return 0
}

build_specific_image() {
    local target="$1"
    
    for image_spec in "${IMAGES[@]}"; do
        local image_name="${image_spec%%:*}"
        if [[ "$image_name" == *"$target"* ]]; then
            build_and_push_image "$image_spec"
            return $?
        fi
    done
    
    error "Unknown target: $target"
    echo "Available targets:"
    for image_spec in "${IMAGES[@]}"; do
        echo "  - ${image_spec%%:*}"
    done
    return 1
}

build_all_images() {
    log "Building all images..."
    
    local failed=0
    for image_spec in "${IMAGES[@]}"; do
        if ! build_and_push_image "$image_spec"; then
            ((failed++))
        fi
    done
    
    if [ $failed -gt 0 ]; then
        error "Failed to build $failed images"
        return 1
    fi
    
    log "All images built successfully!"
    return 0
}

list_registry_images() {
    log "Images in registry:"
    echo
    
    # List images using registry API
    local repos=$(curl -s "http://${REGISTRY}/v2/_catalog" | jq -r '.repositories[]?' 2>/dev/null || true)
    
    if [ -z "$repos" ]; then
        log "No images found in registry"
    else
        for repo in $repos; do
            local tags=$(curl -s "http://${REGISTRY}/v2/${repo}/tags/list" | jq -r '.tags[]?' 2>/dev/null || true)
            for tag in $tags; do
                echo "  ${REGISTRY}/${repo}:${tag}"
            done
        done
    fi
}

usage() {
    echo "Usage: $0 [OPTIONS] [TARGET]"
    echo
    echo "Build and push Docker images to local Kind registry"
    echo
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -l, --list     List images in registry"
    echo
    echo "Targets:"
    echo "  all            Build all images (default)"
    echo "  mgmt           Build management service"
    echo "  mcp            Build MCP server"
    echo "  wine           Build Wine target"
    echo "  linux          Build Linux target"
    echo "  android        Build Android target"
    echo
    echo "Examples:"
    echo "  $0              # Build all images"
    echo "  $0 mgmt         # Build only management service"
    echo "  $0 --list       # List images in registry"
}

# Main execution
main() {
    # Parse arguments
    case "${1:-all}" in
        -h|--help)
            usage
            exit 0
            ;;
        -l|--list)
            check_registry
            list_registry_images
            exit 0
            ;;
        all)
            check_registry
            build_all_images
            ;;
        mgmt|mcp|wine|linux|android)
            check_registry
            build_specific_image "$1"
            ;;
        *)
            error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"