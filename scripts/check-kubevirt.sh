#!/bin/bash
# Script to check KubeVirt status and health

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CLUSTER_NAME="${KIND_CLUSTER_NAME:-legacy-use}"

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

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

check_cluster() {
    log "Checking Kind cluster status..."
    
    if ! kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
        error "Cluster '$CLUSTER_NAME' does not exist."
        echo "Run './scripts/kind-setup.sh' to create the cluster."
        exit 1
    fi
    
    # Set context
    kubectl config use-context "kind-$CLUSTER_NAME" &>/dev/null
    
    # Check cluster connectivity
    if ! kubectl cluster-info &>/dev/null; then
        error "Cannot connect to cluster '$CLUSTER_NAME'"
        exit 1
    fi
    
    info "Cluster '$CLUSTER_NAME' is running"
}

check_kubevirt_deployment() {
    log "Checking KubeVirt deployment status..."
    
    # Check if KubeVirt namespace exists
    if ! kubectl get namespace kubevirt &>/dev/null; then
        error "KubeVirt namespace not found"
        exit 1
    fi
    
    # Check KubeVirt CR status
    local kubevirt_status=$(kubectl get kubevirt.kubevirt.io/kubevirt -n kubevirt -o=jsonpath="{.status.phase}" 2>/dev/null || echo "NotFound")
    
    if [ "$kubevirt_status" = "Deployed" ]; then
        info "KubeVirt is deployed and ready"
    else
        error "KubeVirt status: $kubevirt_status (expected: Deployed)"
        exit 1
    fi
    
    # Check KubeVirt version
    local kubevirt_version=$(kubectl get kubevirt.kubevirt.io/kubevirt -n kubevirt -o=jsonpath="{.status.observedKubeVirtVersion}" 2>/dev/null || echo "Unknown")
    info "KubeVirt version: $kubevirt_version"
    
    # Check if emulation is enabled
    local emulation_enabled=$(kubectl get kubevirt.kubevirt.io/kubevirt -n kubevirt -o=jsonpath="{.spec.configuration.developerConfiguration.useEmulation}" 2>/dev/null || echo "false")
    if [ "$emulation_enabled" = "true" ]; then
        warning "KubeVirt is running in emulation mode (no hardware virtualization)"
    else
        info "KubeVirt is using hardware virtualization"
    fi
}

check_kubevirt_components() {
    log "Checking KubeVirt components..."
    
    # Components to check
    local components=(
        "deployment/virt-api"
        "deployment/virt-controller"
        "daemonset/virt-handler"
    )
    
    local all_ready=true
    
    for component in "${components[@]}"; do
        local type=$(echo "$component" | cut -d'/' -f1)
        local name=$(echo "$component" | cut -d'/' -f2)
        
        if [ "$type" = "deployment" ]; then
            local ready=$(kubectl get -n kubevirt "$component" -o=jsonpath="{.status.readyReplicas}" 2>/dev/null || echo "0")
            local desired=$(kubectl get -n kubevirt "$component" -o=jsonpath="{.status.replicas}" 2>/dev/null || echo "0")
        elif [ "$type" = "daemonset" ]; then
            local ready=$(kubectl get -n kubevirt "$component" -o=jsonpath="{.status.numberReady}" 2>/dev/null || echo "0")
            local desired=$(kubectl get -n kubevirt "$component" -o=jsonpath="{.status.desiredNumberScheduled}" 2>/dev/null || echo "0")
        fi
        
        if [ "$ready" = "$desired" ] && [ "$ready" != "0" ]; then
            info "$component: $ready/$desired ready"
        else
            error "$component: $ready/$desired ready"
            all_ready=false
        fi
    done
    
    if ! $all_ready; then
        error "Some KubeVirt components are not ready"
        exit 1
    fi
}

check_cdi_deployment() {
    log "Checking CDI (Containerized Data Importer) status..."
    
    # Check if CDI namespace exists
    if ! kubectl get namespace cdi &>/dev/null; then
        warning "CDI namespace not found - CDI may not be installed"
        return
    fi
    
    # Check CDI CR status
    local cdi_status=$(kubectl get cdi/cdi -n cdi -o=jsonpath="{.status.phase}" 2>/dev/null || echo "NotFound")
    
    if [ "$cdi_status" = "Deployed" ]; then
        info "CDI is deployed and ready"
    else
        warning "CDI status: $cdi_status (expected: Deployed)"
    fi
    
    # Check CDI version
    local cdi_version=$(kubectl get cdi/cdi -n cdi -o=jsonpath="{.status.observedVersion}" 2>/dev/null || echo "Unknown")
    info "CDI version: $cdi_version"
}

check_cdi_components() {
    log "Checking CDI components..."
    
    # Skip if CDI is not installed
    if ! kubectl get namespace cdi &>/dev/null; then
        return
    fi
    
    # Components to check
    local components=(
        "deployment/cdi-apiserver"
        "deployment/cdi-controller"
        "deployment/cdi-uploadproxy"
    )
    
    local all_ready=true
    
    for component in "${components[@]}"; do
        local ready=$(kubectl get -n cdi "$component" -o=jsonpath="{.status.readyReplicas}" 2>/dev/null || echo "0")
        local desired=$(kubectl get -n cdi "$component" -o=jsonpath="{.status.replicas}" 2>/dev/null || echo "0")
        
        if [ "$ready" = "$desired" ] && [ "$ready" != "0" ]; then
            info "$component: $ready/$desired ready"
        else
            warning "$component: $ready/$desired ready"
            all_ready=false
        fi
    done
    
    if ! $all_ready; then
        warning "Some CDI components are not ready"
    fi
}

check_virtctl() {
    log "Checking virtctl CLI tool..."
    
    if command -v virtctl &>/dev/null; then
        local virtctl_version=$(virtctl version --client 2>/dev/null | grep -oP 'GitVersion:"\K[^"]+' || echo "Unknown")
        info "virtctl is installed (version: $virtctl_version)"
    else
        warning "virtctl is not installed or not in PATH"
        echo "Run './scripts/kind-setup.sh' to install virtctl"
    fi
}

list_vms() {
    log "Listing Virtual Machines..."
    
    # Check if CRDs exist first
    if kubectl get crd virtualmachines.kubevirt.io &>/dev/null; then
        local vm_output=$(kubectl get vms --all-namespaces 2>&1)
        if echo "$vm_output" | grep -q "No resources found"; then
            local vm_count=0
        else
            local vm_count=$(echo "$vm_output" | grep -v NAMESPACE | wc -l | tr -d ' ')
        fi
    else
        local vm_count=0
    fi
    
    if kubectl get crd virtualmachineinstances.kubevirt.io &>/dev/null; then
        local vmi_output=$(kubectl get vmis --all-namespaces 2>&1)
        if echo "$vmi_output" | grep -q "No resources found"; then
            local vmi_count=0
        else
            local vmi_count=$(echo "$vmi_output" | grep -v NAMESPACE | wc -l | tr -d ' ')
        fi
    else
        local vmi_count=0
    fi
    
    info "Virtual Machines (VMs): $vm_count"
    info "Virtual Machine Instances (VMIs): $vmi_count"
    
    if [ "$vm_count" -gt "0" ] || [ "$vmi_count" -gt "0" ]; then
        echo
        echo "Virtual Machines:"
        kubectl get vms,vmis --all-namespaces
    fi
}

print_summary() {
    echo
    echo "=================================="
    echo "KubeVirt Status Summary"
    echo "=================================="
    echo "Cluster: $CLUSTER_NAME"
    echo "Context: kind-$CLUSTER_NAME"
    echo
    echo "Quick Commands:"
    echo "  Create a test VM:     kubectl apply -f https://kubevirt.io/labs/manifests/vm.yaml"
    echo "  List VMs:            kubectl get vms,vmis"
    echo "  Console access:      virtctl console <vm-name>"
    echo "  VNC access:          virtctl vnc <vm-name>"
    echo
    echo "For more details:"
    echo "  kubectl get all -n kubevirt"
}

# Main execution
main() {
    log "Starting KubeVirt health check..."
    
    check_cluster
    check_kubevirt_deployment
    check_kubevirt_components
    # CDI checks removed - not needed when using container disks exclusively
    # check_cdi_deployment
    # check_cdi_components
    check_virtctl
    list_vms
    print_summary
    
    log "Health check completed!"
}

# Run main function
main "$@"