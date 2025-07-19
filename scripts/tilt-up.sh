#!/bin/bash
# Script to start Tilt development environment

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

check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check for required commands
    local required_commands=("docker" "kind" "kubectl" "tilt" "helm")
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
    
    # Check if Kind cluster exists
    if ! kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
        error "Kind cluster '$CLUSTER_NAME' not found. Run ./scripts/kind-setup.sh first."
        exit 1
    fi
    
    # Check kubectl context
    if ! kubectl config current-context | grep -q "kind-${CLUSTER_NAME}"; then
        log "Switching to kind-${CLUSTER_NAME} context..."
        kubectl config use-context "kind-${CLUSTER_NAME}"
    fi
    
    # Check if registry is running
    if [ "$(docker inspect -f '{{.State.Running}}' "kind-registry" 2>/dev/null || true)" != 'true' ]; then
        error "Local registry 'kind-registry' is not running. Run ./scripts/kind-setup.sh first."
        exit 1
    fi
    
    log "All prerequisites met!"
}

check_env_vars() {
    log "Checking environment variables..."
    
    # Check for required environment variables
    if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
        if [ -f .env ]; then
            log "Loading .env file..."
            export $(grep -v '^#' .env | xargs)
        fi
    fi
    
    if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
        warning "ANTHROPIC_API_KEY not set. AI functionality will be limited."
        warning "Set it in .env file or export ANTHROPIC_API_KEY=your-key"
    fi
    
    # Generate LEGACY_USE_API_KEY if not set
    if [ -z "${LEGACY_USE_API_KEY:-}" ]; then
        log "Generating LEGACY_USE_API_KEY..."
        export LEGACY_USE_API_KEY=$(openssl rand -hex 32)
        log "Generated LEGACY_USE_API_KEY: $LEGACY_USE_API_KEY"
        
        # Save to .env.local if it exists
        if [ -f .env.local ]; then
            echo "LEGACY_USE_API_KEY=$LEGACY_USE_API_KEY" >> .env.local
            log "Saved LEGACY_USE_API_KEY to .env.local"
        fi
    fi
}

prepare_namespace() {
    log "Preparing namespace..."
    
    # Create namespace if it doesn't exist
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        kubectl create namespace "$NAMESPACE"
        log "Created namespace: $NAMESPACE"
    fi
}

start_tilt() {
    log "Starting Tilt..."
    
    # Export environment variables for Tilt
    export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
    export LEGACY_USE_API_KEY="${LEGACY_USE_API_KEY:-}"
    export LEGACY_USE_DEBUG="1"
    
    # Check if Tiltfile exists
    if [ ! -f "Tiltfile" ]; then
        error "Tiltfile not found in current directory"
        exit 1
    fi
    
    # Start Tilt
    log "Starting Tilt UI at http://localhost:10350"
    log "Press Ctrl+C to stop"
    echo
    
    # Run Tilt
    tilt up --debug --verbose --stream=true --port 10350
}

# Main execution
main() {
    log "Starting Tilt development environment..."
    
    # Change to project root
    cd "$(dirname "$0")/.."
    
    check_prerequisites
    check_env_vars
    prepare_namespace
    start_tilt
}

# Run main function
main "$@"
