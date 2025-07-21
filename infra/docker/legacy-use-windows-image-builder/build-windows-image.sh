#!/bin/bash
set -e

# Windows VM Image Builder Script
# Creates a Windows VM disk image for KubeVirt from dockur/windows container

echo "Starting Windows VM image build process..."

# Configuration
DISK_SIZE="${DISK_SIZE:-64G}"
WINDOWS_VERSION="${WINDOWS_VERSION:-win11}"
OUTPUT_DIR="/output"
TEMP_DIR="/tmp/windows-build"

# Create directories
mkdir -p "$OUTPUT_DIR" "$TEMP_DIR"

# Function to extract disk from dockur/windows
extract_dockur_disk() {
    echo "Extracting disk image from dockur/windows..."
    
    # Run dockur/windows container temporarily
    CONTAINER_ID=$(docker create dockurr/windows:latest)
    
    # Copy out the disk image
    docker cp "$CONTAINER_ID:/storage/windows.qcow2" "$TEMP_DIR/windows-base.qcow2" || {
        # If the direct copy fails, try extracting from running container
        echo "Direct copy failed, trying alternative method..."
        docker run -d --name windows-extractor \
            -e "VERSION=$WINDOWS_VERSION" \
            -e "DISK_SIZE=$DISK_SIZE" \
            dockurr/windows:latest
        
        # Wait for initial setup
        sleep 30
        
        # Copy the disk
        docker cp windows-extractor:/storage/windows.qcow2 "$TEMP_DIR/windows-base.qcow2"
        docker rm -f windows-extractor
    }
    
    docker rm -f "$CONTAINER_ID" || true
}

# Function to create KubeVirt-compatible disk
create_kubevirt_disk() {
    echo "Converting to KubeVirt-compatible format..."
    
    # Convert to raw format first (better compatibility)
    qemu-img convert -f qcow2 -O raw "$TEMP_DIR/windows-base.qcow2" "$TEMP_DIR/windows.raw"
    
    # Create final qcow2 with proper settings for KubeVirt
    qemu-img convert -f raw -O qcow2 -o lazy_refcounts=on,cluster_size=2M \
        "$TEMP_DIR/windows.raw" "$OUTPUT_DIR/windows-kubevirt.qcow2"
    
    # Resize if needed
    qemu-img resize "$OUTPUT_DIR/windows-kubevirt.qcow2" "$DISK_SIZE"
    
    # Create metadata file
    cat > "$OUTPUT_DIR/windows-kubevirt.yaml" <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: windows-vm-metadata
data:
  version: "$WINDOWS_VERSION"
  disk_size: "$DISK_SIZE"
  format: "qcow2"
  virtio_drivers: "included"
  build_date: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
EOF
}

# Function to create unattended installation ISO (optional)
create_unattend_iso() {
    echo "Creating unattended installation ISO..."
    
    mkdir -p "$TEMP_DIR/iso"
    cp /build/autounattend.xml "$TEMP_DIR/iso/"
    
    # Add virtio drivers to ISO
    7z x /virtio/virtio-win.iso -o"$TEMP_DIR/iso/virtio" -y
    
    # Create ISO
    genisoimage -J -l -R -V "UNATTEND" -iso-level 4 \
        -o "$OUTPUT_DIR/unattend.iso" "$TEMP_DIR/iso"
}

# Main build process
main() {
    echo "Building Windows VM image for KubeVirt"
    echo "Version: $WINDOWS_VERSION"
    echo "Disk size: $DISK_SIZE"
    
    # Check if we should use existing dockur image or build fresh
    if [ -n "$USE_DOCKUR_IMAGE" ]; then
        extract_dockur_disk
    else
        # Alternative: download Windows ISO and build from scratch
        echo "Building from scratch not implemented yet"
        echo "Set USE_DOCKUR_IMAGE=1 to use dockur/windows base"
        exit 1
    fi
    
    # Convert to KubeVirt format
    create_kubevirt_disk
    
    # Create unattended ISO if autounattend.xml exists
    if [ -f "/build/autounattend.xml" ]; then
        create_unattend_iso
    fi
    
    # Cleanup
    rm -rf "$TEMP_DIR"
    
    echo "Build complete! Output files:"
    ls -lh "$OUTPUT_DIR"
}

# Run main function
main