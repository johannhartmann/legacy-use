#!/bin/bash
# Script to teardown Kind cluster with KubeVirt and local registry

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
CLUSTER_NAME="${KIND_CLUSTER_NAME:-legacy-use}"
REGISTRY_NAME='kind-registry'

# Functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

delete_cluster() {
    log "Checking if cluster '$CLUSTER_NAME' exists..."
    
    if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
        log "Deleting Kind cluster '$CLUSTER_NAME'..."
        kind delete cluster --name "$CLUSTER_NAME"
        log "Cluster '$CLUSTER_NAME' deleted successfully!"
    else
        warning "Cluster '$CLUSTER_NAME' does not exist."
    fi
}

delete_registry() {
    log "Checking if registry '$REGISTRY_NAME' exists..."
    
    if [ "$(docker ps -aq -f name=^${REGISTRY_NAME}$)" ]; then
        log "Stopping and removing Docker registry..."
        docker stop "${REGISTRY_NAME}" 2>/dev/null || true
        docker rm "${REGISTRY_NAME}" 2>/dev/null || true
        log "Registry '$REGISTRY_NAME' removed successfully!"
    else
        warning "Registry '$REGISTRY_NAME' does not exist."
    fi
}

cleanup_local_files() {
    log "Cleaning up local files..."
    
    # Remove virtctl if installed in current directory
    if [ -f "virtctl" ]; then
        rm -f virtctl
        log "Removed local virtctl binary"
    fi
    
    # Clean up kubectl config
    if kubectl config get-contexts | grep -q "kind-$CLUSTER_NAME"; then
        kubectl config delete-context "kind-$CLUSTER_NAME" 2>/dev/null || true
        log "Removed kubectl context for cluster"
    fi
}

# Main execution
main() {
    log "Starting Kind cluster teardown..."
    
    # Confirm deletion
    echo
    warning "This will delete the Kind cluster '$CLUSTER_NAME', the local registry, and all associated resources."
    read -p "Are you sure you want to continue? (y/N) " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Teardown cancelled."
        exit 0
    fi
    
    delete_cluster
    delete_registry
    cleanup_local_files
    
    log "Teardown completed successfully!"
    echo
    echo "To create a new cluster, run: ./scripts/kind-setup.sh"
}

# Run main function
main "$@"