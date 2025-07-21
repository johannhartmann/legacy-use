# Ubuntu 24.04 desktop VNC image based on dorowu's architecture
FROM ubuntu:24.04
MAINTAINER Legacy-use Team

ENV DEBIAN_FRONTEND noninteractive

# Install packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        # Core packages
        supervisor \
        openssh-server pwgen sudo vim-tiny \
        net-tools \
        # Desktop environment
        lxde x11vnc xvfb \
        openbox lxpanel pcmanfm \
        gtk2-engines-murrine fonts-ubuntu fonts-ubuntu-console \
        # Python for web interface
        python3-pip python3-dev build-essential \
        # Graphics support
        mesa-utils libgl1-mesa-dri \
        adwaita-icon-theme gtk2-engines-pixbuf \
        dbus-x11 x11-utils \
        # Additional packages
        wget curl ca-certificates \
        # GnuCash specific
        gnucash \
        gnucash-docs \
        gnome-screenshot \
    && apt-get autoclean \
    && apt-get autoremove \
    && rm -rf /var/lib/apt/lists/*

# Remove packages we don't need
RUN apt-get remove -y \
    vim-tiny firefox \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# tini for subreap
ENV TINI_VERSION v0.19.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /bin/tini
RUN chmod +x /bin/tini

# Copy our image files
COPY infra/docker/linux-machine/image /

# Make startup script executable
RUN chmod +x /startup.sh

# Create necessary directories
RUN mkdir -p /root/.config/pcmanfm/LXDE/ && \
    mkdir -p /var/log/supervisor/

# Add GnuCash to supervisor services
COPY infra/docker/linux-machine/gnucash.conf /etc/supervisor/conf.d/gnucash.conf 

# Copy over GnuCash data file
RUN useradd -m -s /bin/bash developer
# Set the working directory
WORKDIR /workspace
RUN mkdir -p /gnucash
COPY infra/docker/linux-machine/data.gnucash /gnucash/data.gnucash
COPY infra/docker/linux-machine/data.qif /gnucash/data.qif
RUN chown developer:developer /gnucash/data.* && \
    chmod 644 /gnucash/data.* && \
    chown developer:developer /gnucash && \
    chmod 755 /gnucash

# Set environment for VNC
# No password needed - runs in secure Kubernetes namespace

# Expose VNC port only (noVNC handled by shared proxy)
EXPOSE 5900

# Set working directory
WORKDIR /root

# Set entrypoint
ENTRYPOINT ["/startup.sh"]

