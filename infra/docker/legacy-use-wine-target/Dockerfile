# Download TurboCASH installer
FROM alpine:latest as turbocash-download
RUN apk add --no-cache curl && \
    curl -L -o /TurboCASH_Setup.exe "https://www.turbocash.co.za/Download/TurboCASH5/TurboCASH_Setup.exe"

# Fast Wine container for development - uses Ubuntu's wine package with 32-bit support
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:1
ENV WINEARCH=win32
ENV WINEPREFIX=/home/wineuser/.wine32

# Enable 32-bit architecture for Wine
RUN dpkg --add-architecture i386 && \
    apt-get update && apt-get install -y --no-install-recommends \
    # Essential tools
    wget curl ca-certificates lsb-release gnupg2 software-properties-common bzip2 \
    # VNC and desktop
    xvfb x11vnc fluxbox xterm \
    # Process management
    supervisor \
    # Additional libraries that applications might need
    lib32z1 lib32ncurses6 libc6:i386 libncurses6:i386 libstdc++6:i386 \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Add WineHQ repository and install latest stable Wine
RUN mkdir -pm755 /etc/apt/keyrings && \
    wget -nc -O /etc/apt/keyrings/winehq-archive.key https://dl.winehq.org/wine-builds/winehq.key && \
    wget -NP /etc/apt/sources.list.d/ "https://dl.winehq.org/wine-builds/ubuntu/dists/noble/winehq-noble.sources" && \
    apt-get update && \
    apt-get install -y --install-recommends winehq-stable && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create user and directories
RUN useradd -m -s /bin/bash wineuser && \
    echo "wineuser:wine" | chpasswd && \
    mkdir -p /home/wineuser/.vnc /var/log/supervisor && \
    chown -R wineuser:wineuser /home/wineuser

# Copy supervisor config
COPY infra/docker/legacy-use-wine-target/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Setup Wine environment
USER wineuser
ENV HOME=/home/wineuser

# Copy TurboCASH installer
USER root
COPY --from=turbocash-download /TurboCASH_Setup.exe /home/wineuser/
RUN chown wineuser:wineuser /home/wineuser/TurboCASH_Setup.exe

# Copy and extract Lotus demo application
COPY infra/docker/legacy-use-wine-target/demo.tar.bz2 /home/wineuser/
RUN cd /home/wineuser && \
    tar -xjf demo.tar.bz2 && \
    rm demo.tar.bz2 && \
    chown -R wineuser:wineuser /home/wineuser/lotus

# Set proper permissions
USER root
RUN mkdir -p /home/wineuser/Desktop && \
    chown -R wineuser:wineuser /home/wineuser/Desktop

EXPOSE 5900
VOLUME /home/wineuser/.wine32

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]