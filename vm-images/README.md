# VM Container Disk Images

This directory contains scripts and Dockerfiles to create container disk images for KubeVirt VMs.

## Overview

Container disks are Docker images that contain VM disk files (qcow2 format) at `/disk/`. They provide:
- Fast VM deployment (no download wait time)
- Local registry caching
- Version control for VM images
- Offline operation capability

## Supported VMs

- **Windows XP** (`winxp.qcow2`) - 1GB RAM configured
- **Windows 10** (`win10.qcow2`) - 2GB RAM configured  
- **macOS Mojave** (`mojave.qcow2`) - Not yet configured in Helm

## Quick Start

1. **Download VM images** (requires Mayflower network/VPN):
   ```bash
   ./download-images.sh
   ```

2. **Build container disk images**:
   ```bash
   ./build-vm-images.sh
   ```
   
   Or to use a different registry:
   ```bash
   REGISTRY=localhost:5000 ./build-vm-images.sh
   ```

3. **Update Helm values** to use container disks instead of URLs:
   ```yaml
   windowsXpKubevirt:
     containerDiskImage: "registry.git.mayflower.de/legacy-use-windows-xp-containerdisk:latest"
     diskUrl: ""  # Clear this to use containerDisk
   ```

## How It Works

1. **Download**: The `download-images.sh` script downloads qcow2 files from Mayflower intranet
2. **Build**: Each Dockerfile creates a minimal image with the qcow2 file at `/disk/`
3. **Push**: Images are pushed to the Mayflower registry (`registry.git.mayflower.de`)
4. **Deploy**: KubeVirt pulls the container image and extracts the disk

## Benefits vs Direct URLs

- **Speed**: No download wait during VM creation (images cached in registry)
- **Reliability**: No dependency on intranet availability
- **Efficiency**: Docker layer caching means updates only transfer differences

## Disk Space Requirements

- Windows XP: ~5GB compressed
- Windows 10: ~15GB compressed
- macOS Mojave: ~10GB compressed

Total: ~30GB for all three images

## Switching Between Modes

### Using Container Disks (Registry)
```yaml
windowsXpKubevirt:
  containerDiskImage: "registry.git.mayflower.de/legacy-use-windows-xp-containerdisk:latest"
  diskUrl: ""
```

### Using CDI with URLs (Remote)
```yaml
windowsXpKubevirt:
  containerDiskImage: ""
  diskUrl: "https://intranet.mayflower.de/s/sPD3fEnNQGWATLC/download?path=%2F&files=winxp.qcow2"
```

## Troubleshooting

- **Download fails**: Check VPN connection to Mayflower network
- **Build fails**: Ensure qcow2 files exist in subdirectories
- **Push fails**: Check registry connectivity and authentication
- **Registry login fails**: Ensure the token is correct and not expired

## Advanced Usage

To optimize/compress images before building:
```bash
qemu-img convert -O qcow2 -c original.qcow2 compressed.qcow2
```

To check image size in registry:
```bash
curl -s -H "Authorization: Bearer RhyUy66eyTi6va1f76xC" \
  https://registry.git.mayflower.de/v2/legacy-use-windows-xp-containerdisk/manifests/latest | jq '.config.size'
```

## Registry Configuration

The build script uses the Mayflower GitLab registry by default:
- **Registry**: `registry.git.mayflower.de`
- **Authentication**: Token-based (configured in script)

To use a different registry:
```bash
REGISTRY=localhost:5000 ./build-vm-images.sh
```