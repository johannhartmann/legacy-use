# Custom virt-launcher image with macOS support
# This wraps the standard virt-launcher to add Apple SMC device

FROM quay.io/kubevirt/virt-launcher:v1.1.0

# Install wrapper script
COPY infra/docker/virt-launcher-macos/qemu-wrapper.sh /usr/local/bin/qemu-wrapper.sh
RUN chmod +x /usr/local/bin/qemu-wrapper.sh

# Override the default QEMU binary path
# virt-launcher looks for qemu-system-x86_64 in PATH
RUN mv /usr/bin/qemu-system-x86_64 /usr/bin/qemu-system-x86_64.orig && \
    ln -s /usr/local/bin/qemu-wrapper.sh /usr/bin/qemu-system-x86_64

# The wrapper will check for macOS VMs and add the Apple SMC device