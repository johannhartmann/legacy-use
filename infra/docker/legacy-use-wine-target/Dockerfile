FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    wget \
    software-properties-common \
    gnupg2 \
    winbind \
    xvfb \
    x11vnc \
    novnc \
    websockify \
    supervisor \
    fluxbox \
    xterm \
    net-tools \
    nano \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Add Wine repository and install Wine
RUN dpkg --add-architecture i386 && \
    wget -nc https://dl.winehq.org/wine-builds/winehq.key && \
    apt-key add winehq.key && \
    add-apt-repository 'deb https://dl.winehq.org/wine-builds/ubuntu/ jammy main' && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    winehq-stable \
    winetricks \
    && rm -rf /var/lib/apt/lists/*

# Create user for Wine
RUN useradd -m -s /bin/bash wineuser && \
    echo "wineuser:wine" | chpasswd

# Setup VNC
RUN mkdir -p /home/wineuser/.vnc && \
    x11vnc -storepasswd wine /home/wineuser/.vnc/passwd && \
    chown -R wineuser:wineuser /home/wineuser/.vnc

# Configure supervisor
RUN mkdir -p /var/log/supervisor
RUN echo '[supervisord]\n\
nodaemon=true\n\
user=root\n\
\n\
[program:xvfb]\n\
command=/usr/bin/Xvfb :1 -screen 0 1920x1080x24\n\
autorestart=true\n\
user=root\n\
priority=100\n\
\n\
[program:x11vnc]\n\
command=/usr/bin/x11vnc -display :1 -usepw -forever -shared -rfbport 5900 -rfbauth /home/wineuser/.vnc/passwd\n\
autorestart=true\n\
user=wineuser\n\
priority=200\n\
\n\
[program:novnc]\n\
command=/usr/share/novnc/utils/launch.sh --vnc localhost:5900 --listen 6080\n\
autorestart=true\n\
user=root\n\
priority=300\n\
\n\
[program:fluxbox]\n\
command=/usr/bin/fluxbox -display :1\n\
autorestart=true\n\
user=wineuser\n\
environment=HOME="/home/wineuser",DISPLAY=":1"\n\
priority=400' > /etc/supervisor/conf.d/supervisord.conf

# Setup Wine environment
USER wineuser
ENV HOME=/home/wineuser
ENV DISPLAY=:1
ENV WINEARCH=win64
ENV WINEPREFIX=/home/wineuser/.wine

# Initialize Wine (skip heavy packages for now)
RUN wine wineboot --init && \
    wineserver -k

# Create startup script
USER root
RUN echo '#!/bin/bash\n\
echo "Starting Wine container services..."\n\
\n\
# Initialize Wine if needed\n\
su - wineuser -c "wineboot --init || true"\n\
\n\
# Start supervisor\n\
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf\n\
' > /startup.sh && chmod +x /startup.sh

# Expose ports
EXPOSE 5900 6080

# Volume for persistent Wine data
VOLUME /home/wineuser/.wine

ENTRYPOINT ["/startup.sh"]