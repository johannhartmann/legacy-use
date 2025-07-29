# Android in Docker (AinD) container for legacy-use
# Provides Android via Anbox with native VNC on port 5900
FROM ghcr.io/aind-containers/aind:latest

# AinD already includes:
# - Android 11 running in Anbox
# - VNC server on port 5900
# - VNC password in /home/user/.vnc/passwdfile

# Install additional tools for automation
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    jq \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Create directory for persistent data
RUN mkdir -p /data && \
    chown -R user:user /data

# Stay as root for privileged container
# The AinD scripts will handle user switching internally
WORKDIR /home/user

# Expose only VNC port
EXPOSE 5900

# Volume for persistent Android data
VOLUME ["/data"]

# Use the default entrypoint from AinD base image
# The container will automatically start Android and VNC server