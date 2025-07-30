#!/bin/bash
# Script to set up Kind cluster with KubeVirt support and local registry

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
CLUSTER_NAME="${KIND_CLUSTER_NAME:-legacy-use}"
CONFIG_FILE="${KIND_CONFIG_FILE:-kind-config.yaml}"
KUBEVIRT_VERSION="${KUBEVIRT_VERSION:-}"
REGISTRY_NAME='kind-registry'
REGISTRY_PORT='5000'

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

check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check for required commands
    local required_commands=("docker" "kind" "kubectl")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            error "$cmd is not installed. Please install it first."
            exit 1
        fi
    done
    
    # Check Docker is running
    if ! docker info &> /dev/null; then
        error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    log "All prerequisites met!"
}

create_registry() {
    log "Creating local Docker registry..."
    
    # Check if registry already exists
    if [ "$(docker inspect -f '{{.State.Running}}' "${REGISTRY_NAME}" 2>/dev/null || true)" == 'true' ]; then
        log "Registry ${REGISTRY_NAME} already exists and is running"
    else
        docker run -d \
            --restart=always \
            -p "127.0.0.1:${REGISTRY_PORT}:5000" \
            --name "${REGISTRY_NAME}" \
            registry:2
        log "Registry created at localhost:${REGISTRY_PORT}"
    fi
}

create_kind_cluster() {
    log "Creating Kind cluster '$CLUSTER_NAME' with registry support..."
    
    # Check if cluster already exists
    if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
        warning "Cluster '$CLUSTER_NAME' already exists. Delete it first with: kind delete cluster --name $CLUSTER_NAME"
        exit 1
    fi
    
    # Create cluster with configuration
    if [ -f "$CONFIG_FILE" ]; then
        log "Using configuration from $CONFIG_FILE"
        kind create cluster --name "$CLUSTER_NAME" --config "$CONFIG_FILE"
    else
        log "Creating cluster with default configuration and registry support"
        cat <<EOF | kind create cluster --name "$CLUSTER_NAME" --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
containerdConfigPatches:
- |-
  [plugins."io.containerd.grpc.v1.cri".registry]
    config_path = "/etc/containerd/certs.d"
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
- role: worker
- role: worker
EOF
    fi
    
    # Set kubectl context
    kubectl cluster-info --context "kind-$CLUSTER_NAME"
}

connect_registry_to_kind() {
    log "Connecting registry to Kind network..."
    
    # Connect the registry to the cluster network
    if [ "$(docker inspect -f='{{json .NetworkSettings.Networks.kind}}' "${REGISTRY_NAME}")" = 'null' ]; then
        docker network connect "kind" "${REGISTRY_NAME}" || true
    fi
}

configure_registry_on_nodes() {
    log "Configuring registry on Kind nodes..."
    
    # Create registry config directory and hosts.toml on each node
    REGISTRY_DIR="/etc/containerd/certs.d/localhost:${REGISTRY_PORT}"
    for node in $(kind get nodes --name "$CLUSTER_NAME"); do
        log "Configuring registry on node: ${node}"
        docker exec "${node}" mkdir -p "${REGISTRY_DIR}"
        cat <<EOF | docker exec -i "${node}" cp /dev/stdin "${REGISTRY_DIR}/hosts.toml"
[host."http://${REGISTRY_NAME}:5000"]
EOF
    done
}

create_registry_configmap() {
    log "Creating registry ConfigMap..."
    
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: local-registry-hosting
  namespace: kube-public
data:
  localRegistryHosting.v1: |
    host: "localhost:${REGISTRY_PORT}"
    help: "https://kind.sigs.k8s.io/docs/user/local-registry/"
EOF
}

optimize_etcd_resources() {
    log "Optimizing etcd resources for better performance..."
    
    # Get the control plane node name
    local control_plane_node=$(kind get nodes --name "$CLUSTER_NAME" | grep control-plane | head -1)
    
    if [ -z "$control_plane_node" ]; then
        error "Could not find control plane node"
        return 1
    fi
    
    log "Found control plane node: $control_plane_node"
    
    # First ensure the cluster is stable before making changes
    log "Waiting for cluster to stabilize before optimizing etcd..."
    local stabilize_count=0
    while [ $stabilize_count -lt 30 ]; do
        if kubectl get nodes &>/dev/null && kubectl get pods -n kube-system &>/dev/null; then
            log "Cluster is stable"
            break
        fi
        sleep 2
        stabilize_count=$((stabilize_count + 1))
    done
    
    log "Current etcd resources (before optimization):"
    docker exec "$control_plane_node" grep -A4 "resources:" /etc/kubernetes/manifests/etcd.yaml || true
    
    # Create a temporary etcd manifest with increased resources
    cat <<'EOF' > /tmp/etcd-patch.yaml
- op: replace
  path: /spec/containers/0/resources
  value:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 1000m
      memory: 1Gi
EOF
    
    # Apply the patch to the etcd manifest
    docker exec "$control_plane_node" bash -c '
        # Backup original manifest
        cp /etc/kubernetes/manifests/etcd.yaml /etc/kubernetes/manifests/etcd.yaml.bak
        
        # Use a more precise sed command to update resources
        sed -i -e "/^    resources:$/{
            N
            :loop
            N
            s/resources:.*startupProbe:/resources:\n      requests:\n        cpu: 500m\n        memory: 512Mi\n      limits:\n        cpu: 1000m\n        memory: 1Gi\n    startupProbe:/
            t end
            b loop
            :end
        }" /etc/kubernetes/manifests/etcd.yaml
    '
    
    # Force etcd pod to restart by moving the manifest
    log "Forcing etcd to restart with new resources..."
    docker exec "$control_plane_node" bash -c '
        mv /etc/kubernetes/manifests/etcd.yaml /tmp/etcd.yaml
        sleep 5
        mv /tmp/etcd.yaml /etc/kubernetes/manifests/etcd.yaml
    '
    
    # Wait for the old etcd pod to terminate
    local retry_count=0
    while [ $retry_count -lt 30 ]; do
        if ! docker exec "$control_plane_node" crictl ps 2>/dev/null | grep -q etcd; then
            log "Old etcd pod has terminated, waiting for new one to start..."
            break
        fi
        sleep 2
        retry_count=$((retry_count + 1))
    done
    
    # Wait for new etcd pod to be running
    retry_count=0
    while [ $retry_count -lt 30 ]; do
        if docker exec "$control_plane_node" crictl ps 2>/dev/null | grep -q etcd; then
            log "New etcd pod is running"
            sleep 10  # Give it time to fully initialize
            break
        fi
        sleep 2
        retry_count=$((retry_count + 1))
    done
    
    # Verify etcd is running and show new resources
    log "Verifying etcd pod status..."
    
    # Wait a bit for pod to fully initialize
    sleep 5
    
    local etcd_pod=$(kubectl get pod -n kube-system 2>/dev/null | grep "^etcd-" | awk '{print $1}' | head -1)
    if [ -n "$etcd_pod" ]; then
        log "etcd pod found: $etcd_pod"
        
        # Get actual pod resources (not manifest)
        local actual_resources=$(kubectl get pod -n kube-system "$etcd_pod" -o jsonpath='{.spec.containers[0].resources}' 2>/dev/null)
        
        if echo "$actual_resources" | grep -q "500m"; then
            log "✓ etcd optimization successful!"
            log "New etcd resources (after optimization):"
            echo "$actual_resources" | jq '.' 2>/dev/null || echo "$actual_resources"
        else
            log "⚠ Warning: etcd pod resources may not have updated correctly"
            log "Pod resources:"
            echo "$actual_resources" | jq '.' 2>/dev/null || echo "$actual_resources"
            log "Manifest resources:"
            docker exec "$control_plane_node" grep -A6 "resources:" /etc/kubernetes/manifests/etcd.yaml || true
        fi
    else
        log "etcd resources updated (pod verification skipped - this is normal during initial setup)"
        log "Updated etcd manifest resources:"
        docker exec "$control_plane_node" grep -A6 "resources:" /etc/kubernetes/manifests/etcd.yaml || true
    fi
    
    log "etcd optimization complete!"
}


install_kubevirt() {
    log "Installing KubeVirt..."
    
    # Wait for API server to be fully ready after etcd optimization
    log "Ensuring API server is ready..."
    local retry_count=0
    while [ $retry_count -lt 60 ]; do
        if kubectl get --raw /healthz &>/dev/null; then
            log "API server is responding"
            break
        fi
        log "Waiting for API server to be ready... (attempt $((retry_count + 1))/60)"
        sleep 5
        retry_count=$((retry_count + 1))
    done
    
    if [ $retry_count -eq 60 ]; then
        error "API server did not become ready in time"
        return 1
    fi
    
    # Get KubeVirt version
    if [ -z "$KUBEVIRT_VERSION" ]; then
        KUBEVIRT_VERSION=$(curl -s https://storage.googleapis.com/kubevirt-prow/release/kubevirt/kubevirt/stable.txt)
        log "Using latest stable KubeVirt version: $KUBEVIRT_VERSION"
    else
        log "Using specified KubeVirt version: $KUBEVIRT_VERSION"
    fi
    
    # Deploy KubeVirt operator with retry logic
    log "Deploying KubeVirt operator..."
    retry_count=0
    while [ $retry_count -lt 3 ]; do
        if kubectl create -f "https://github.com/kubevirt/kubevirt/releases/download/${KUBEVIRT_VERSION}/kubevirt-operator.yaml" --validate=false 2>&1; then
            log "KubeVirt operator deployment initiated"
            break
        fi
        log "Failed to deploy KubeVirt operator, retrying... (attempt $((retry_count + 1))/3)"
        sleep 10
        retry_count=$((retry_count + 1))
    done
    
    if [ $retry_count -eq 3 ]; then
        error "Failed to deploy KubeVirt operator after 3 attempts"
        return 1
    fi
    
    # Wait for operator to be ready
    log "Waiting for KubeVirt operator to be ready..."
    kubectl wait -n kubevirt deployment/virt-operator --for=condition=Available --timeout=300s
    
    # Deploy KubeVirt CR with retry logic
    log "Deploying KubeVirt CR..."
    retry_count=0
    while [ $retry_count -lt 3 ]; do
        if kubectl create -f "https://github.com/kubevirt/kubevirt/releases/download/${KUBEVIRT_VERSION}/kubevirt-cr.yaml" --validate=false 2>&1; then
            log "KubeVirt CR deployment initiated"
            break
        fi
        log "Failed to deploy KubeVirt CR, retrying... (attempt $((retry_count + 1))/3)"
        sleep 10
        retry_count=$((retry_count + 1))
    done
    
    if [ $retry_count -eq 3 ]; then
        error "Failed to deploy KubeVirt CR after 3 attempts"
        return 1
    fi
    
    # Check if we need to enable emulation
    if ! grep -q -E 'vmx|svm' /proc/cpuinfo; then
        warning "No hardware virtualization detected. Enabling KubeVirt emulation mode..."
        kubectl -n kubevirt patch kubevirt kubevirt --type=merge --patch '{"spec":{"configuration":{"developerConfiguration":{"useEmulation":true}}}}'
    fi
    
    # Configure allowed machine types to support legacy OSes like Windows XP
    log "Configuring KubeVirt to allow additional machine types..."
    kubectl -n kubevirt patch kubevirt kubevirt --type=merge --patch '{"spec":{"configuration":{"architectureConfiguration":{"amd64":{"emulatedMachines":["q35*","pc-q35*","pc","pc-i440fx*"]}}}}}'
    
    # Configure increased log verbosity for debugging
    log "Configuring KubeVirt log verbosity for better debugging..."
    kubectl -n kubevirt patch kubevirt kubevirt --type=merge --patch '{"spec":{"configuration":{"developerConfiguration":{"logVerbosity":{"virtLauncher":6,"virtHandler":6,"virtController":6,"virtAPI":6,"virtOperator":4}}}}}'
    
    # Wait for KubeVirt to be ready
    log "Waiting for KubeVirt to be ready (this may take a few minutes)..."
    kubectl wait -n kubevirt kubevirt/kubevirt --for=condition=Available --timeout=600s
    
    # Verify deployment
    local phase=$(kubectl get kubevirt.kubevirt.io/kubevirt -n kubevirt -o=jsonpath="{.status.phase}")
    if [ "$phase" = "Deployed" ]; then
        log "KubeVirt successfully deployed!"
    else
        error "KubeVirt deployment failed. Current phase: $phase"
        exit 1
    fi
}

# CDI installation removed - not needed when using container disks exclusively
# Keeping function commented for reference if needed in future
: '
install_cdi() {
    log "Installing CDI (Containerized Data Importer)..."
    
    # Get CDI version - using a stable version compatible with KubeVirt
    local CDI_VERSION="${CDI_VERSION:-v1.60.3}"
    log "Using CDI version: $CDI_VERSION"
    
    # Deploy CDI operator with retry logic
    log "Deploying CDI operator..."
    retry_count=0
    while [ $retry_count -lt 3 ]; do
        if kubectl create -f "https://github.com/kubevirt/containerized-data-importer/releases/download/${CDI_VERSION}/cdi-operator.yaml" --validate=false 2>&1; then
            log "CDI operator deployment initiated"
            break
        fi
        log "Failed to deploy CDI operator, retrying... (attempt $((retry_count + 1))/3)"
        sleep 10
        retry_count=$((retry_count + 1))
    done
    
    if [ $retry_count -eq 3 ]; then
        error "Failed to deploy CDI operator after 3 attempts"
        return 1
    fi
    
    # Wait for operator to be ready
    log "Waiting for CDI operator to be ready..."
    kubectl wait -n cdi deployment/cdi-operator --for=condition=Available --timeout=300s
    
    # Deploy CDI CR with retry logic
    log "Deploying CDI CR..."
    retry_count=0
    while [ $retry_count -lt 3 ]; do
        if kubectl create -f "https://github.com/kubevirt/containerized-data-importer/releases/download/${CDI_VERSION}/cdi-cr.yaml" --validate=false 2>&1; then
            log "CDI CR deployment initiated"
            break
        fi
        log "Failed to deploy CDI CR, retrying... (attempt $((retry_count + 1))/3)"
        sleep 10
        retry_count=$((retry_count + 1))
    done
    
    if [ $retry_count -eq 3 ]; then
        error "Failed to deploy CDI CR after 3 attempts"
        return 1
    fi
    
    # Wait for CDI to be ready
    log "Waiting for CDI to be ready (this may take a few minutes)..."
    kubectl wait -n cdi cdi/cdi --for=condition=Available --timeout=600s
    
    # Verify deployment
    local cdi_phase=$(kubectl get cdi/cdi -n cdi -o=jsonpath="{.status.phase}" 2>/dev/null || echo "NotFound")
    if [ "$cdi_phase" = "Deployed" ]; then
        log "CDI successfully deployed!"
    else
        error "CDI deployment failed. Current phase: $cdi_phase"
        exit 1
    fi
    
    # Check CDI components
    log "CDI components status:"
    kubectl get all -n cdi
}
'

install_virtctl() {
    log "Installing virtctl CLI tool..."
    
    # Get virtctl version from deployed KubeVirt
    local VIRTCTL_VERSION=$(kubectl get kubevirt.kubevirt.io/kubevirt -n kubevirt -o=jsonpath="{.status.observedKubeVirtVersion}")
    
    # Detect OS and architecture
    local OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    local ARCH=$(uname -m)
    
    case "$ARCH" in
        x86_64)
            ARCH="amd64"
            ;;
        aarch64|arm64)
            ARCH="arm64"
            ;;
        *)
            error "Unsupported architecture: $ARCH"
            exit 1
            ;;
    esac
    
    # Download virtctl
    local VIRTCTL_URL="https://github.com/kubevirt/kubevirt/releases/download/${VIRTCTL_VERSION}/virtctl-${VIRTCTL_VERSION}-${OS}-${ARCH}"
    log "Downloading virtctl from: $VIRTCTL_URL"
    
    curl -L -o virtctl "$VIRTCTL_URL"
    chmod +x virtctl
    
    # Install to /usr/local/bin if we have permissions
    if [ -w /usr/local/bin ]; then
        sudo mv virtctl /usr/local/bin/
        log "virtctl installed to /usr/local/bin/virtctl"
    else
        mkdir -p "$HOME/.local/bin"
        mv virtctl "$HOME/.local/bin/"
        log "virtctl installed to $HOME/.local/bin/virtctl"
        warning "Add $HOME/.local/bin to your PATH if not already added"
    fi
}

print_cluster_info() {
    log "Cluster setup complete!"
    echo
    echo "Cluster Information:"
    echo "===================="
    echo "Cluster Name: $CLUSTER_NAME"
    echo "Context: kind-$CLUSTER_NAME"
    echo "Registry: localhost:${REGISTRY_PORT}"
    echo
    echo "KubeVirt Status:"
    kubectl get all -n kubevirt
    echo
    echo "To use this cluster:"
    echo "  kubectl config use-context kind-$CLUSTER_NAME"
    echo
    echo "To push images to local registry:"
    echo "  docker tag myimage:latest localhost:${REGISTRY_PORT}/myimage:latest"
    echo "  docker push localhost:${REGISTRY_PORT}/myimage:latest"
    echo
    echo "To use images in Kubernetes:"
    echo "  image: localhost:${REGISTRY_PORT}/myimage:latest"
    echo
    echo "To start Tilt development:"
    echo "  ./scripts/tilt-up.sh"
    echo
    echo "To create a VM:"
    echo "  kubectl apply -f <vm-manifest.yaml>"
    echo
    echo "To access a VM console:"
    echo "  virtctl console <vm-name>"
    echo
    echo "To delete this cluster:"
    echo "  kind delete cluster --name $CLUSTER_NAME"
    echo "  docker stop ${REGISTRY_NAME} && docker rm ${REGISTRY_NAME}"
}

# Main execution
main() {
    log "Starting Kind cluster setup with KubeVirt support and local registry..."
    
    check_prerequisites
    create_registry
    create_kind_cluster
    connect_registry_to_kind
    configure_registry_on_nodes
    create_registry_configmap
    # optimize_etcd_resources  # Disabled: causes cluster instability during initialization
    install_kubevirt
    # install_cdi  # Removed: not needed when using container disks exclusively
    install_virtctl
    print_cluster_info
    
    log "Setup completed successfully!"
}

# Run main function
main "$@"