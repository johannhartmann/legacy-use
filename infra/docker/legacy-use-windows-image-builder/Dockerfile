# Windows VM Image Builder for KubeVirt
# This builds a container that creates a Windows VM disk image for use with KubeVirt

FROM ubuntu:22.04

# Install required tools
RUN apt-get update && apt-get install -y \
    qemu-utils \
    curl \
    wget \
    p7zip-full \
    genisoimage \
    python3 \
    python3-pip \
    ca-certificates \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI for accessing host Docker daemon
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y docker-ce-cli && \
    rm -rf /var/lib/apt/lists/*

# Install virtio-win drivers
RUN mkdir -p /virtio && \
    wget -O /virtio/virtio-win.iso https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso

# Create working directory
WORKDIR /build

# Copy build scripts
COPY build-windows-image.sh /build/
COPY autounattend.xml /build/

# Make script executable
RUN chmod +x /build/build-windows-image.sh

# Default command
CMD ["/build/build-windows-image.sh"]