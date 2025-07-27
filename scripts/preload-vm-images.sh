#!/bin/bash
# Script to pre-pull VM container images to prevent re-downloading

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
CLUSTER_NAME="${KIND_CLUSTER_NAME:-legacy-use}"

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# VM Images to preload
declare -A VM_IMAGES=(
    ["windows-xp"]="registry.git.mayflower.de/legacy-use/legacy-use/legacy-use-windows-xp-containerdisk:latest"
    ["windows-10"]="registry.git.mayflower.de/legacy-use/legacy-use/legacy-use-windows-10-containerdisk:latest"
    ["macos-mojave"]="registry.git.mayflower.de/legacy-use/legacy-use/legacy-use-macos-mojave-containerdisk:latest"
)

# Check if running in Kind node
check_kind_node() {
    local control_plane="${CLUSTER_NAME}-control-plane"
    if ! docker exec "$control_plane" true 2>/dev/null; then
        error "Kind cluster not running. Please run 'make kind-setup' first."
        exit 1
    fi
}

# Pull image into Kind node
pull_image() {
    local name=$1
    local image=$2
    local control_plane="${CLUSTER_NAME}-control-plane"
    
    log "Checking $name image: $image"
    
    # Check if image already exists in Kind node
    if docker exec "$control_plane" crictl images | awk '{print $1":"$2}' | grep -q "^${image}$"; then
        log "✓ $name image already present"
        return 0
    fi
    
    log "Pulling $name image (this may take several minutes)..."
    
    # Pull image on host first
    if ! docker pull "$image"; then
        warning "Failed to pull $image - it may not be accessible"
        return 1
    fi
    
    # Load image into Kind
    log "Loading $name image into Kind cluster..."
    if ! kind load docker-image "$image" --name "$CLUSTER_NAME"; then
        error "Failed to load $image into Kind"
        return 1
    fi
    
    log "✓ $name image loaded successfully"
    return 0
}

# Tag images to prevent pruning
protect_images() {
    log "Tagging images to prevent pruning..."
    local control_plane="${CLUSTER_NAME}-control-plane"
    
    for name in "${!VM_IMAGES[@]}"; do
        local image="${VM_IMAGES[$name]}"
        local protected_tag="localhost:5001/protected/$name:keep"
        
        # Tag image in Kind node to prevent pruning
        docker exec "$control_plane" ctr -n k8s.io images tag "$image" "$protected_tag" 2>/dev/null || true
    done
    
    log "✓ Images tagged for protection"
}

# Show image sizes
show_image_info() {
    log "VM Image information:"
    echo "===================="
    local control_plane="${CLUSTER_NAME}-control-plane"
    
    for name in "${!VM_IMAGES[@]}"; do
        local image="${VM_IMAGES[$name]}"
        local size=$(docker exec "$control_plane" crictl images | grep -F "$image" | head -1 | awk '{print $4}' || echo "Not loaded")
        printf "%-15s %s\n" "$name:" "$size"
    done
    echo
}

# Main execution
main() {
    log "Starting VM image preload..."
    
    check_kind_node
    
    local failed=0
    for name in "${!VM_IMAGES[@]}"; do
        if ! pull_image "$name" "${VM_IMAGES[$name]}"; then
            ((failed++))
        fi
    done
    
    if [ $failed -gt 0 ]; then
        warning "$failed images failed to load"
    fi
    
    protect_images
    show_image_info
    
    log "VM image preload complete!"
    
    if [ $failed -eq 0 ]; then
        echo
        echo "All images loaded successfully. You can now run:"
        echo "  make tilt-up"
    else
        echo
        echo "Some images failed to load. Tilt may still work if those VMs are not enabled."
    fi
}

# Run main function
main "$@"