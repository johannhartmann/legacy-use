#!/bin/bash
# Download VM images from Mayflower intranet
# These images are used to create container disks for KubeVirt VMs

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Base URL for downloads
BASE_URL="https://intranet.mayflower.de/s/sPD3fEnNQGWATLC/download?path=%2F&files="

# Image definitions
declare -A IMAGES=(
    ["windows-xp/winxp.qcow2"]="winxp.qcow2"
    ["windows-10/win10.qcow2"]="win10.qcow2"
    ["macos-mojave/mojave.qcow2"]="mojave.qcow2"
)

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

download_image() {
    local path=$1
    local filename=$2
    local target_file="${SCRIPT_DIR}/${path}"
    local target_dir=$(dirname "$target_file")
    
    # Create directory if it doesn't exist
    mkdir -p "$target_dir"
    
    if [ -f "$target_file" ]; then
        log "Image already exists: $path ($(du -h "$target_file" | cut -f1))"
        return 0
    fi
    
    log "Downloading $filename to $path..."
    local url="${BASE_URL}${filename}"
    
    # Download with progress bar
    if command -v wget >/dev/null 2>&1; then
        wget --progress=bar:force -O "$target_file.tmp" "$url" || {
            error "Failed to download $filename"
            rm -f "$target_file.tmp"
            return 1
        }
    elif command -v curl >/dev/null 2>&1; then
        curl -L --progress-bar -o "$target_file.tmp" "$url" || {
            error "Failed to download $filename"
            rm -f "$target_file.tmp"
            return 1
        }
    else
        error "Neither wget nor curl is available. Please install one of them."
        return 1
    fi
    
    # Move temp file to final location
    mv "$target_file.tmp" "$target_file"
    log "Downloaded $path successfully ($(du -h "$target_file" | cut -f1))"
}

main() {
    log "Starting VM image downloads..."
    
    # Check if we're on the Mayflower network
    if ! ping -c 1 -W 2 intranet.mayflower.de >/dev/null 2>&1; then
        warning "Cannot reach intranet.mayflower.de - are you on the Mayflower network or VPN?"
        warning "Continuing anyway - downloads may fail"
    fi
    
    local failed=0
    
    # Download each image
    for path in "${!IMAGES[@]}"; do
        if ! download_image "$path" "${IMAGES[$path]}"; then
            ((failed++))
        fi
    done
    
    echo
    if [ $failed -eq 0 ]; then
        log "All images downloaded successfully!"
        log "Total size: $(du -sh "$SCRIPT_DIR" | cut -f1)"
    else
        error "$failed image(s) failed to download"
        exit 1
    fi
    
    echo
    log "Next steps:"
    echo "  1. Run ./build-vm-images.sh to build container disk images"
    echo "  2. The images will be pushed to localhost:5000 registry"
}

# Run main function
main "$@"