FROM quay.io/kubevirt/container-disk-v1alpha:latest

# Copy the Windows XP driver floppy disk image
COPY xp_q35_x64.img /disk/

# KubeVirt expects the disk image to be named 'disk.img'
RUN mv /disk/xp_q35_x64.img /disk/disk.img