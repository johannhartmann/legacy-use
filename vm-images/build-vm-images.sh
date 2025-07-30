#!/bin/bash
# Build container disk images for VMs and push to registry
#
# Usage:
#   ./build-vm-images.sh
#
# Environment variables:
#   REGISTRY_PROJECT - GitLab project path (e.g., "group/project")
#   REGISTRY - Registry URL (default: registry.git.mayflower.de)
#   REGISTRY_TOKEN - Registry authentication token
#   REGISTRY_USERNAME - GitLab username (for Personal Access Token)

set -uo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REGISTRY="${REGISTRY:-registry.git.mayflower.de}"
REGISTRY_PROJECT="${REGISTRY_PROJECT:-legacy-use/legacy-use}"  # GitLab group/project
REGISTRY_TOKEN="${REGISTRY_TOKEN:-LsGv1NWP5gycrtLxkWdR}"
REGISTRY_USERNAME="${REGISTRY_USERNAME:-johann-peter.hartmann}"  # GitLab username for PAT
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# VM definitions
declare -A VMS=(
    ["windows-xp"]="legacy-use-windows-xp-containerdisk"
    ["windows-10"]="legacy-use-windows-10-containerdisk"
    ["macos-mojave"]="legacy-use-macos-mojave-containerdisk"
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

check_image_exists() {
    local dir=$1
    local expected_file=""
    
    case $dir in
        "windows-xp") expected_file="winxp.qcow2" ;;
        "windows-10") expected_file="win10.qcow2" ;;
        "macos-mojave") expected_file="mojave.qcow2" ;;
    esac
    
    if [ ! -f "${SCRIPT_DIR}/${dir}/${expected_file}" ]; then
        error "Missing ${expected_file} in ${dir}/"
        error "Please run ./download-images.sh first"
        return 1
    fi
    
    return 0
}

build_vm_image() {
    local vm_dir=$1
    local image_name=$2
    local tag=""
    
    # Build full tag with project path for GitLab registry
    if [[ "$REGISTRY" == *"mayflower"* ]]; then
        tag="${REGISTRY}/${REGISTRY_PROJECT}/${image_name}:latest"
    else
        tag="${REGISTRY}/${image_name}:latest"
    fi
    
    log "Building ${image_name}..."
    
    # Check if qcow2 file exists
    if ! check_image_exists "$vm_dir"; then
        return 1
    fi
    
    # Build the image
    cd "${SCRIPT_DIR}/${vm_dir}"
    if docker build -t "$tag" .; then
        log "Built $tag successfully"
        
        # Get image size
        local size=$(docker image inspect "$tag" --format='{{.Size}}' | numfmt --to=iec-i --suffix=B)
        log "Image size: $size"
        
        # Push to registry
        log "Pushing to registry..."
        log "Pushing image: $tag"
        
        # Debug: check if we're logged in
        if ! docker system info 2>&1 | grep -q "Registry: ${REGISTRY}"; then
            warning "May not be properly authenticated to ${REGISTRY}"
        fi
        
        if docker push "$tag" 2>&1 | tee "/tmp/docker-push-${vm_dir}.log"; then
            log "Pushed $tag to registry"
        else
            error "Failed to push $tag"
            error "Check /tmp/docker-push-${vm_dir}.log for details"
            return 1
        fi
    else
        error "Failed to build $tag"
        return 1
    fi
    
    cd - >/dev/null
    return 0
}

check_registry() {
    log "Checking registry connectivity at $REGISTRY..."
    
    # Login to registry if it's the Mayflower registry
    if [[ "$REGISTRY" == *"mayflower"* ]]; then
        log "Logging in to Mayflower registry as $REGISTRY_USERNAME..."
        # Use your GitLab username with the project access token
        echo "$REGISTRY_TOKEN" | docker login "$REGISTRY" -u "$REGISTRY_USERNAME" --password-stdin || {
            error "Failed to login to registry"
            error "Check that your project token has 'write_registry' scope and at least Developer role"
            return 1
        }
    fi
    
    # For Mayflower registry, we need to check with auth header
    if [[ "$REGISTRY" == *"mayflower"* ]]; then
        if ! curl -s -f -o /dev/null -H "Authorization: Bearer $REGISTRY_TOKEN" "https://${REGISTRY}/v2/"; then
            warning "Registry API check failed, but Docker login succeeded. Continuing..."
        fi
    else
        # For local registry, check without auth
        if ! curl -s -f -o /dev/null "http://${REGISTRY}/v2/"; then
            error "Cannot connect to registry at $REGISTRY"
            return 1
        fi
    fi
    
    log "Registry is ready"
    return 0
}

main() {
    log "Starting VM container disk image builds..."
    
    # Check if registry is accessible
    if ! check_registry; then
        exit 1
    fi
    
    # Check if any qcow2 files exist
    local qcow2_count=$(find "$SCRIPT_DIR" -name "*.qcow2" | wc -l)
    if [ "$qcow2_count" -eq 0 ]; then
        warning "No qcow2 files found. Please run ./download-images.sh first"
        exit 1
    fi
    
    local failed=0
    local built=0
    
    # Build each VM image
    log "Found ${#VMS[@]} VMs to build"
    for vm_dir in "${!VMS[@]}"; do
        log "Processing VM: $vm_dir"
        if [ -d "${SCRIPT_DIR}/${vm_dir}" ]; then
            echo
            if build_vm_image "$vm_dir" "${VMS[$vm_dir]}"; then
                ((built++))
                log "Successfully built and pushed $vm_dir ($built/${#VMS[@]})"
            else
                ((failed++))
                warning "Failed to build/push ${vm_dir}"
            fi
        else
            warning "Directory ${vm_dir} not found, skipping"
            ((failed++))
        fi
    done
    
    echo
    echo "========================================"
    if [ $failed -eq 0 ]; then
        log "All VM images built and pushed successfully! ($built images)"
    else
        warning "Built $built images, $failed failed"
    fi
    
    echo
    log "Images in registry:"
    for vm_dir in "${!VMS[@]}"; do
        local image_name="${VMS[$vm_dir]}"
        if [[ "$REGISTRY" == *"mayflower"* ]]; then
            echo "  - ${REGISTRY}/${REGISTRY_PROJECT}/${image_name}:latest"
        else
            echo "  - ${REGISTRY}/${image_name}:latest"
        fi
    done
    
    echo
    log "To use these images, update your Helm values to use containerDisk instead of diskUrl"
}

# Run main function
main "$@"