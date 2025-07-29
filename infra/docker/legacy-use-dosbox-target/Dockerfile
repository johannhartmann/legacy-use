# DOSBox container for legacy-use
# Provides DOSBox environment with native VNC on port 5900
FROM shrizt/dosbox:latest

# VNC configuration (port 5901 is hardcoded in the base image)
ENV VNCGEOMETRY=1024x768
ENV VNCDEPTH=16
# No password for VNC (consistent with other legacy-use targets)
ENV VNCPASSWORD=""

# Install additional tools that might be useful
USER root
# Fix for Debian Buster EOL - use archive repositories
RUN echo "deb http://archive.debian.org/debian buster main" > /etc/apt/sources.list && \
    echo "deb http://archive.debian.org/debian-security buster/updates main" >> /etc/apt/sources.list && \
    apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Create directories for DOS programs and configuration
RUN mkdir -p /config/dos /config/autorun

# Create a default autorun.sh that just starts DOSBox
RUN echo '#!/bin/bash\necho "Starting DOSBox..."' > /config/autorun.sh && \
    chmod +x /config/autorun.sh

# Stay as root since base image might not have 'user'
# The base image's entrypoint will handle user switching if needed

# Copy our custom entrypoint to override VNC port
COPY infra/docker/legacy-use-dosbox-target/entrypoint.sh /custom-entrypoint.sh
RUN chmod +x /custom-entrypoint.sh

# Expose only VNC port
EXPOSE 5900

# Volume for persistent DOS programs and configuration
VOLUME ["/config"]

# Override entrypoint to use port 5900
ENTRYPOINT ["/custom-entrypoint.sh"]