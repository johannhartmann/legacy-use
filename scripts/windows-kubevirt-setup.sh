#!/bin/bash
set -e

# Windows KubeVirt VM Setup and Management Script

NAMESPACE="${NAMESPACE:-legacy-use}"
VM_NAME="${VM_NAME:-legacy-use-windows-vm}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Check if KubeVirt is installed
check_kubevirt() {
    info "Checking KubeVirt installation..."
    if kubectl get crd virtualmachines.kubevirt.io &> /dev/null; then
        info "KubeVirt is installed"
        kubectl get pods -n kubevirt | grep -E "virt-controller|virt-api|virt-handler"
    else
        error "KubeVirt is not installed. Please install KubeVirt first."
    fi
}

# Check if virtctl is installed
check_virtctl() {
    if ! command -v virtctl &> /dev/null; then
        warn "virtctl is not installed"
        info "Installing virtctl..."
        
        # Download virtctl
        VIRTCTL_VERSION=$(kubectl get kubevirt.kubevirt.io/kubevirt -n kubevirt -o jsonpath='{.status.targetKubeVirtVersion}')
        curl -L -o virtctl https://github.com/kubevirt/kubevirt/releases/download/${VIRTCTL_VERSION}/virtctl-${VIRTCTL_VERSION}-linux-amd64
        chmod +x virtctl
        sudo mv virtctl /usr/local/bin/
        
        info "virtctl installed successfully"
    else
        info "virtctl is already installed"
    fi
}

# Build Windows image
build_windows_image() {
    info "Building Windows VM image..."
    
    cd infra/docker/legacy-use-windows-image-builder
    docker build -t localhost:5000/legacy-use-windows-image-builder .
    docker push localhost:5000/legacy-use-windows-image-builder
    
    # Run the builder
    docker run --rm \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v $(pwd)/output:/output \
        -e USE_DOCKUR_IMAGE=1 \
        -e WINDOWS_VERSION=win11 \
        -e DISK_SIZE=64G \
        localhost:5000/legacy-use-windows-image-builder
    
    info "Windows image built successfully"
    ls -lh output/
}

# Upload Windows image to PVC
upload_windows_image() {
    local IMAGE_PATH="${1:-output/windows-kubevirt.qcow2}"
    
    if [ ! -f "$IMAGE_PATH" ]; then
        error "Image file not found: $IMAGE_PATH"
    fi
    
    info "Uploading Windows image to PVC..."
    
    # Delete existing PVC if it exists
    kubectl delete pvc ${VM_NAME}-disk -n $NAMESPACE --ignore-not-found=true
    
    # Upload image
    virtctl image-upload pvc ${VM_NAME}-disk \
        --size=64Gi \
        --image-path="$IMAGE_PATH" \
        --namespace=$NAMESPACE \
        --storage-class=local-path \
        --wait-secs=300
    
    info "Image uploaded successfully"
}

# Deploy Windows VM
deploy_vm() {
    info "Deploying Windows VM with Helm..."
    
    helm upgrade --install legacy-use ./infra/helm/legacy-use \
        -f ./infra/helm/legacy-use/values-windows-kubevirt.yaml \
        --namespace $NAMESPACE \
        --create-namespace \
        --wait
    
    info "Windows VM deployed successfully"
}

# Start VM
start_vm() {
    info "Starting Windows VM..."
    virtctl start $VM_NAME -n $NAMESPACE
    
    # Wait for VM to be ready
    info "Waiting for VM to be ready..."
    kubectl wait --for=condition=Ready vmi/$VM_NAME -n $NAMESPACE --timeout=300s
    
    info "VM started successfully"
}

# Stop VM
stop_vm() {
    info "Stopping Windows VM..."
    virtctl stop $VM_NAME -n $NAMESPACE
    info "VM stopped"
}

# Restart VM
restart_vm() {
    info "Restarting Windows VM..."
    virtctl restart $VM_NAME -n $NAMESPACE
    info "VM restarted"
}

# Get VM status
status_vm() {
    info "Windows VM Status:"
    echo ""
    kubectl get vm,vmi -n $NAMESPACE | grep -E "(NAME|$VM_NAME)"
    echo ""
    
    # Get IP if running
    if kubectl get vmi $VM_NAME -n $NAMESPACE &> /dev/null; then
        IP=$(kubectl get vmi $VM_NAME -n $NAMESPACE -o jsonpath='{.status.interfaces[0].ipAddress}')
        if [ -n "$IP" ]; then
            info "VM IP Address: $IP"
        fi
    fi
}

# Connect via VNC
connect_vnc() {
    info "Connecting to Windows VM via VNC..."
    virtctl vnc $VM_NAME -n $NAMESPACE
}

# Connect via console
connect_console() {
    info "Connecting to Windows VM console..."
    info "Press Ctrl+] to exit console"
    virtctl console $VM_NAME -n $NAMESPACE
}

# Port forward for RDP
forward_rdp() {
    info "Setting up RDP port forwarding..."
    info "RDP will be available at localhost:3389"
    info "User: Admin, Password: windows"
    kubectl port-forward svc/$VM_NAME 3389:3389 -n $NAMESPACE
}

# Port forward for noVNC
forward_novnc() {
    info "Setting up noVNC port forwarding..."
    info "noVNC will be available at http://localhost:6083"
    info "Password: windows"
    kubectl port-forward svc/${VM_NAME}-novnc 6083:6080 -n $NAMESPACE
}

# Show logs
show_logs() {
    info "Showing VM logs..."
    kubectl logs -l kubevirt.io/vm=$VM_NAME -n $NAMESPACE --tail=50 -f
}

# Main menu
show_help() {
    cat << EOF
Windows KubeVirt VM Management Script

Usage: $0 [command]

Commands:
    check       - Check KubeVirt installation
    build       - Build Windows VM image
    upload      - Upload Windows image to PVC
    deploy      - Deploy Windows VM with Helm
    start       - Start the Windows VM
    stop        - Stop the Windows VM
    restart     - Restart the Windows VM
    status      - Show VM status
    vnc         - Connect via VNC (virtctl)
    console     - Connect via serial console
    rdp         - Set up RDP port forwarding
    novnc       - Set up noVNC port forwarding
    logs        - Show VM logs
    full-setup  - Run full setup (check, build, upload, deploy, start)

Environment variables:
    NAMESPACE   - Kubernetes namespace (default: legacy-use)
    VM_NAME     - VM name (default: legacy-use-windows-vm)

Examples:
    $0 check                    # Check KubeVirt installation
    $0 full-setup              # Complete setup from scratch
    $0 status                  # Check VM status
    $0 rdp                     # Connect via RDP
EOF
}

# Full setup
full_setup() {
    info "Running full Windows VM setup..."
    check_kubevirt
    check_virtctl
    build_windows_image
    upload_windows_image
    deploy_vm
    start_vm
    status_vm
    
    info "Full setup complete!"
    info "Connect via:"
    info "  - RDP: Run '$0 rdp' then connect to localhost:3389"
    info "  - VNC: Run '$0 vnc'"
    info "  - noVNC: Run '$0 novnc' then open http://localhost:6083"
}

# Main script logic
case "${1:-help}" in
    check)
        check_kubevirt
        check_virtctl
        ;;
    build)
        build_windows_image
        ;;
    upload)
        upload_windows_image "${2:-}"
        ;;
    deploy)
        deploy_vm
        ;;
    start)
        start_vm
        ;;
    stop)
        stop_vm
        ;;
    restart)
        restart_vm
        ;;
    status)
        status_vm
        ;;
    vnc)
        connect_vnc
        ;;
    console)
        connect_console
        ;;
    rdp)
        forward_rdp
        ;;
    novnc)
        forward_novnc
        ;;
    logs)
        show_logs
        ;;
    full-setup)
        full_setup
        ;;
    help|*)
        show_help
        ;;
esac