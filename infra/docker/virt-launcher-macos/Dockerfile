# Custom virt-launcher image with macOS support
# This wraps the standard virt-launcher to add Apple SMC device

FROM quay.io/kubevirt/virt-launcher:v1.1.0

# Install wrapper script
COPY infra/docker/virt-launcher-macos/qemu-wrapper.sh /usr/local/bin/qemu-wrapper.sh
RUN chmod +x /usr/local/bin/qemu-wrapper.sh

# Find and override the QEMU binary
# virt-launcher may have qemu in different locations
RUN which qemu-system-x86_64 || find /usr -name "qemu-system-x86_64" -type f 2>/dev/null || echo "QEMU not found"
RUN if [ -f /usr/libexec/qemu-kvm ]; then \
        mv /usr/libexec/qemu-kvm /usr/libexec/qemu-kvm.orig && \
        ln -s /usr/local/bin/qemu-wrapper.sh /usr/libexec/qemu-kvm; \
    elif [ -f /usr/bin/qemu-system-x86_64 ]; then \
        mv /usr/bin/qemu-system-x86_64 /usr/bin/qemu-system-x86_64.orig && \
        ln -s /usr/local/bin/qemu-wrapper.sh /usr/bin/qemu-system-x86_64; \
    elif [ -f /usr/libexec/qemu-system-x86_64 ]; then \
        mv /usr/libexec/qemu-system-x86_64 /usr/libexec/qemu-system-x86_64.orig && \
        ln -s /usr/local/bin/qemu-wrapper.sh /usr/libexec/qemu-system-x86_64; \
    else \
        echo "Warning: Could not find QEMU binary to wrap"; \
    fi

# The wrapper will check for macOS VMs and add the Apple SMC device