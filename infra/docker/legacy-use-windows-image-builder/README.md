# Windows VM Image Builder for KubeVirt

This Docker image builds Windows VM disk images suitable for use with KubeVirt in Kubernetes.

## Overview

The image builder creates a Windows VM disk image by:
1. Extracting a base image from the dockur/windows container
2. Converting it to a KubeVirt-compatible format
3. Adding VirtIO drivers for better performance
4. Creating an unattended installation configuration

## Building the Image

```bash
docker build -t legacy-use-windows-image-builder .
```

## Running the Builder

```bash
# Create output directory
mkdir -p output

# Run the builder
docker run -v /var/run/docker.sock:/var/run/docker.sock \
           -v $(pwd)/output:/output \
           -e USE_DOCKUR_IMAGE=1 \
           -e WINDOWS_VERSION=win11 \
           -e DISK_SIZE=64G \
           legacy-use-windows-image-builder
```

## Environment Variables

- `USE_DOCKUR_IMAGE`: Set to 1 to use dockur/windows as base (recommended)
- `WINDOWS_VERSION`: Windows version (win11, win10, etc.)
- `DISK_SIZE`: Final disk size (default: 64G)

## Output Files

The builder creates:
- `windows-kubevirt.qcow2`: The VM disk image for KubeVirt
- `windows-kubevirt.yaml`: Metadata about the build
- `unattend.iso`: Optional unattended installation ISO

## Using with KubeVirt

1. Upload the disk image to a PVC:
```bash
virtctl image-upload pvc windows-disk \
  --size=64Gi \
  --image-path=output/windows-kubevirt.qcow2 \
  --storage-class=local-path
```

2. Create a VirtualMachine using the Helm templates in `infra/helm/legacy-use/`

## Notes

- The base dockur/windows image includes a pre-activated Windows installation
- VirtIO drivers are included for optimal performance in KubeVirt
- The unattended configuration sets up:
  - Computer name: LEGACY-WIN
  - Admin user: Admin/windows
  - RDP enabled by default
  - Auto-login configured