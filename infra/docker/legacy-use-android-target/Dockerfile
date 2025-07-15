# Android emulator container for legacy-use
# Using a specific lighter version if available
FROM budtmo/docker-android:emulator_11.0

# Set environment variables for consistent emulator configuration
ENV EMULATOR_DEVICE="Samsung Galaxy S10"
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

# Fix log_web_shared service and configure proper container logging
# The base image uses custom supervisor configs in /home/androidusr/docker-android/mixins/configs/process/
# We need to override the specific config file that defines log_web_shared
COPY infra/docker/legacy-use-android-target/supervisord-base-override.conf /home/androidusr/docker-android/mixins/configs/process/supervisord-base.conf

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