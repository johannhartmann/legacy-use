# Container disk for Windows 10 VM
# This creates a minimal container that holds the VM disk image
FROM scratch

# Add metadata
LABEL description="Windows 10 VM disk for KubeVirt"
LABEL version="1.0"
LABEL source="legacy-use"

# Add the qcow2 disk image
# The file must be at /disk/ for KubeVirt to find it
ADD win10.qcow2 /disk/