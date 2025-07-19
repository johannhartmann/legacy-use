#!/bin/bash
# Script to stop Tilt and clean up resources

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
CLUSTER_NAME="${KIND_CLUSTER_NAME:-legacy-use}"
NAMESPACE="legacy-use"

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

stop_tilt() {
    log "Stopping Tilt..."
    
    # Change to project root
    cd "$(dirname "$0")/.."
    
    # Check if Tilt is running
    if pgrep -f "tilt up" > /dev/null 2>&1; then
        log "Stopping Tilt processes..."
        tilt down || true
        pkill -f "tilt up" || true
    else
        log "Tilt is not running"
    fi
}

clean_kubernetes_resources() {
    log "Cleaning up Kubernetes resources..."
    
    # Check if cluster exists
    if ! kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
        warning "Kind cluster '$CLUSTER_NAME' not found"
        return
    fi
    
    # Set kubectl context
    kubectl config use-context "kind-${CLUSTER_NAME}" || return
    
    # Delete Helm release
    if helm list -n "$NAMESPACE" 2>/dev/null | grep -q "legacy-use"; then
        log "Uninstalling Helm release..."
        helm uninstall legacy-use -n "$NAMESPACE" || true
    fi
    
    # Delete namespace (optional - uncomment if you want to clean everything)
    # if kubectl get namespace "$NAMESPACE" &> /dev/null; then
    #     log "Deleting namespace $NAMESPACE..."
    #     kubectl delete namespace "$NAMESPACE" --timeout=60s || true
    # fi
    
    # Clean up any remaining resources
    log "Cleaning up any remaining resources..."
    kubectl delete all --all -n "$NAMESPACE" --timeout=60s || true
}

clean_docker_images() {
    log "Cleaning up local registry images..."
    
    # Get images from local registry
    local registry_images=$(docker exec kind-registry ls /var/lib/registry/docker/registry/v2/repositories 2>/dev/null || true)
    
    if [ -n "$registry_images" ]; then
        log "Found images in local registry: $registry_images"
        # Note: We don't delete them as they might be needed for next run
        log "Images will remain in registry for faster startup next time"
    fi
}

print_cleanup_info() {
    log "Tilt environment stopped!"
    echo
    echo "Resources cleaned:"
    echo "=================="
    echo "✓ Tilt processes stopped"
    echo "✓ Kubernetes resources deleted"
    echo "✓ Helm release uninstalled"
    echo
    echo "Resources preserved:"
    echo "===================="
    echo "• Kind cluster: $CLUSTER_NAME"
    echo "• Local registry: kind-registry"
    echo "• Docker images in registry"
    echo
    echo "To completely remove everything:"
    echo "  ./scripts/kind-teardown.sh"
    echo
    echo "To restart development:"
    echo "  ./scripts/tilt-up.sh"
}

# Main execution
main() {
    log "Stopping Tilt development environment..."
    
    stop_tilt
    clean_kubernetes_resources
    clean_docker_images
    print_cleanup_info
}

# Run main function
main "$@"