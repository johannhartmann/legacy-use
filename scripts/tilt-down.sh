#!/usr/bin/env bash
# Wrapper script for tilt down that ensures proper VM cleanup

# Don't exit on error - we want to clean up as much as possible
set +e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if cluster is accessible
if ! kubectl cluster-info &>/dev/null; then
    error "Cannot connect to Kubernetes cluster"
    error "Tilt down may fail, but attempting anyway..."
fi

# Clean up VMs before tilt down
log "Cleaning up KubeVirt VMs..."
if kubectl get namespace legacy-use &>/dev/null; then
    # Delete all VMIs
    if kubectl get vmi -n legacy-use &>/dev/null; then
        kubectl delete vmi -n legacy-use --all --force --grace-period=0 2>/dev/null || true
        log "Deleted VirtualMachineInstances"
    fi
    
    # Scale down all VMIRS
    if kubectl get vmirs -n legacy-use &>/dev/null; then
        kubectl scale vmirs -n legacy-use --all --replicas=0 2>/dev/null || true
        log "Scaled down VirtualMachineInstanceReplicaSets"
    fi
else
    warning "legacy-use namespace not found, skipping VM cleanup"
fi

# Run tilt down with timeout and error handling
log "Running tilt down..."
timeout 60 tilt down "$@" || {
    exit_code=$?
    if [ $exit_code -eq 124 ]; then
        error "Tilt down timed out after 60 seconds"
        warning "Attempting force cleanup..."
        
        # Force delete namespace if it exists
        if kubectl get namespace legacy-use &>/dev/null; then
            kubectl delete namespace legacy-use --force --grace-period=0 2>/dev/null || true
        fi
    else
        error "Tilt down failed with exit code $exit_code"
        warning "Some resources may not have been cleaned up"
    fi
}

# Final check
if kubectl get namespace legacy-use &>/dev/null; then
    warning "legacy-use namespace still exists after tilt down"
    kubectl get all -n legacy-use
else
    log "Tilt down completed successfully"
fi
