# macOS Mojave Container Disks

This directory contains the build configuration for macOS Mojave container disks used by KubeVirt.

## Container Disks

The macOS VM requires multiple container disks:

1. **Main OS Disk** (`legacy-use-macos-mojave-containerdisk`)
   - Contains the main macOS Mojave installation
   - Built from `mojave.qcow2`

2. **OVMF CODE** (`macos-ovmf-code`)
   - UEFI firmware code
   - Built from `OVMF_CODE.fd`
   - Published to: `registry.git.mayflower.de/legacy-use/legacy-use/macos-ovmf-code:latest`

3. **OVMF VARS** (`macos-ovmf-vars`)
   - UEFI firmware variables
   - Built from `OVMF_VARS-1920x1080.fd`
   - Published to: `registry.git.mayflower.de/legacy-use/legacy-use/macos-ovmf-vars:latest`

4. **OpenCore** (`macos-opencore`)
   - OpenCore bootloader for macOS
   - Built from `OpenCore.qcow2`
   - Published to: `registry.git.mayflower.de/legacy-use/legacy-use/macos-opencore:latest`

## Building

To build all macOS container disks:

```bash
# Build only (no push)
./build-macos-disks.sh

# Build and push to registry
./build-macos-disks.sh --push
# or
PUSH=true ./build-macos-disks.sh
```

The main VM image is built using the parent directory's build script:

```bash
cd ..
./build-vm-images.sh
```

## Source Files

The build process expects the following files from `../../vms/macos-mojave/`:
- `OVMF_CODE.fd` - UEFI firmware code
- `OVMF_VARS-1920x1080.fd` - UEFI firmware variables
- `OpenCore.qcow2` - OpenCore bootloader
- `mojave.qcow2` - Main macOS disk (for the main container disk)

## Usage in KubeVirt

These container disks are referenced in the VM definition to provide all necessary components for running macOS in KubeVirt.