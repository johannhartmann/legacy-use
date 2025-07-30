#!/bin/bash
# Build script for macOS Mojave container disks

set -euo pipefail

# Configuration
REGISTRY=${REGISTRY:-"registry.git.mayflower.de/legacy-use/legacy-use"}
VMS_SOURCE_DIR="../../vms/macos-mojave"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if source files exist
check_source_files() {
    log "Checking for source files in $VMS_SOURCE_DIR..."
    
    local required_files=(
        "OVMF_CODE.fd"
        "OVMF_VARS-1920x1080.fd"
        "OpenCore.qcow2"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$VMS_SOURCE_DIR/$file" ]; then
            error "Required file $file not found in $VMS_SOURCE_DIR"
        fi
    done
    
    log "All required source files found"
}

# Copy source files to build directory
prepare_build_context() {
    log "Preparing build context..."
    
    # Copy OVMF_CODE.fd
    cp -v "$VMS_SOURCE_DIR/OVMF_CODE.fd" .
    
    # Copy OVMF_VARS
    cp -v "$VMS_SOURCE_DIR/OVMF_VARS-1920x1080.fd" .
    
    # Copy OpenCore
    cp -v "$VMS_SOURCE_DIR/OpenCore.qcow2" .
    
    log "Build context prepared"
}

# Build container disk image
build_disk() {
    local dockerfile=$1
    local image_name=$2
    local tag=${3:-latest}
    
    log "Building $image_name:$tag using $dockerfile..."
    
    docker build \
        -f "$dockerfile" \
        -t "${REGISTRY}/${image_name}:${tag}" \
        .
    
    if [ $? -eq 0 ]; then
        log "Successfully built ${REGISTRY}/${image_name}:${tag}"
    else
        error "Failed to build ${image_name}"
    fi
}

# Push container disk image
push_disk() {
    local image_name=$1
    local tag=${2:-latest}
    
    log "Pushing ${REGISTRY}/${image_name}:${tag}..."
    
    docker push "${REGISTRY}/${image_name}:${tag}"
    
    if [ $? -eq 0 ]; then
        log "Successfully pushed ${REGISTRY}/${image_name}:${tag}"
    else
        error "Failed to push ${image_name}"
    fi
}

# Clean up build artifacts
cleanup() {
    log "Cleaning up build artifacts..."
    rm -f OVMF_CODE.fd
    rm -f OVMF_VARS-1920x1080.fd
    rm -f OpenCore.qcow2
}

# Main execution
main() {
    log "Starting macOS container disk build process..."
    
    # Check prerequisites
    check_source_files
    
    # Prepare build context
    prepare_build_context
    
    # Build all container disks
    log "Building container disk images..."
    
    build_disk "Dockerfile.ovmf-code" "macos-ovmf-code" "latest"
    build_disk "Dockerfile.ovmf-vars" "macos-ovmf-vars" "latest"
    build_disk "Dockerfile.opencore" "macos-opencore" "latest"
    
    # Push images if requested
    if [ "${PUSH:-false}" = "true" ]; then
        log "Pushing images to registry..."
        push_disk "macos-ovmf-code" "latest"
        push_disk "macos-ovmf-vars" "latest"
        push_disk "macos-opencore" "latest"
    else
        log "Skipping push (set PUSH=true to push images)"
    fi
    
    # Clean up
    cleanup
    
    log "macOS container disk build complete!"
    
    echo
    echo "Built images:"
    echo "============="
    docker images | grep -E "(macos-ovmf-code|macos-ovmf-vars|macos-opencore)" | grep "${REGISTRY}"
    
    echo
    echo "To push images to registry:"
    echo "  PUSH=true ./build-macos-disks.sh"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [--push]"
        echo ""
        echo "Build macOS container disk images"
        echo ""
        echo "Options:"
        echo "  --push    Build and push images to registry"
        echo ""
        echo "Environment variables:"
        echo "  REGISTRY            Registry URL (default: registry.git.mayflower.de/legacy-use/legacy-use)"
        echo "  PUSH                Set to 'true' to push images"
        exit 0
        ;;
    --push)
        export PUSH=true
        ;;
esac

# Run main function
main "$@"