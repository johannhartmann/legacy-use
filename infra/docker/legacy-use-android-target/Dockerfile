# Android emulator container for legacy-use
# Note: Android emulator requires KVM which is not available in Kind
# Consider using this only on bare metal Kubernetes or with nested virtualization
FROM budtmo/docker-android:emulator_11.0

# Set environment variables for consistent emulator configuration
# Use Nexus 7 (2012) which has 800x1280 resolution - exactly our target when in portrait
ENV EMULATOR_DEVICE="Nexus 7 2012"
ENV WEB_VNC=true
ENV DATAPARTITION=2g
ENV EMULATOR_NO_BOOT_ANIM=1

# Install additional tools that might be useful for automation
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Fix log_web_shared service by creating a dummy script that exits successfully
# This is less invasive than replacing the entire supervisor configuration
RUN echo '#!/bin/bash\nexit 0' > /usr/local/bin/docker-android-share-log-dummy && \
    chmod +x /usr/local/bin/docker-android-share-log-dummy && \
    # Replace the problematic command with our dummy script
    sed -i 's|/usr/local/bin/docker-android share log|/usr/local/bin/docker-android-share-log-dummy|g' \
        /home/androidusr/docker-android/mixins/configs/process/supervisord-base.conf

# Create a directory for app storage
RUN mkdir -p /home/androidusr/apps && \
    chown -R androidusr:androidusr /home/androidusr/apps

# Switch back to the default user
USER androidusr
WORKDIR /home/androidusr

# The base image already has its own entrypoint, so we don't need a custom one
# Just use the default entrypoint from the base image

# Expose ports
# 5555 - ADB
# 6080 - noVNC web interface
EXPOSE 5555 6080

# Volume for persistent data
VOLUME /home/androidusr/apps
VOLUME /home/androidusr/.android

# Use the default entrypoint from the base image