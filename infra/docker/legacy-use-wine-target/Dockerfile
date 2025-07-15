# Fast Wine container for development - uses Ubuntu's wine package
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:1
ENV WINEARCH=win64
ENV WINEPREFIX=/home/wineuser/.wine

# Install everything in one optimized layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Essential tools
    wget curl ca-certificates \
    # VNC and desktop
    xvfb x11vnc fluxbox xterm \
    # Process management
    supervisor \
    # Wine from Ubuntu repos (much faster than official Wine)
    wine \
    # Web VNC
    novnc websockify \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create user and directories
RUN useradd -m -s /bin/bash wineuser && \
    echo "wineuser:wine" | chpasswd && \
    mkdir -p /home/wineuser/.vnc /var/log/supervisor && \
    chown -R wineuser:wineuser /home/wineuser

# Setup VNC password
RUN x11vnc -storepasswd wine /home/wineuser/.vnc/passwd && \
    chown wineuser:wineuser /home/wineuser/.vnc/passwd

# Simple supervisor config
RUN printf '[supervisord]\nnodaemon=true\nuser=root\n\n[program:xvfb]\ncommand=/usr/bin/Xvfb :1 -screen 0 1920x1080x24\nautorestart=true\nuser=root\npriority=100\n\n[program:x11vnc]\ncommand=/usr/bin/x11vnc -display :1 -usepw -forever -shared -rfbport 5900 -rfbauth /home/wineuser/.vnc/passwd -noshm\nautorestart=true\nuser=wineuser\npriority=200\n\n[program:novnc]\ncommand=/usr/share/novnc/utils/launch.sh --vnc localhost:5900 --listen 6080\nautorestart=true\nuser=root\npriority=300\n\n[program:fluxbox]\ncommand=/usr/bin/fluxbox -display :1\nautorestart=true\nuser=wineuser\nenvironment=HOME="/home/wineuser",DISPLAY=":1"\npriority=400\n' > /etc/supervisor/conf.d/supervisord.conf

# Setup Wine environment
USER wineuser
ENV HOME=/home/wineuser

# Skip Wine initialization for faster builds
# Wine will be initialized at runtime

# Create startup script
USER root
RUN printf '#!/bin/bash\nset -e\necho "Starting Wine container..."\n\n# Initialize Wine at runtime\nsu - wineuser -c "wineboot --init 2>/dev/null || true" &\n\n# Start supervisor\nexec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf\n' > /startup.sh && chmod +x /startup.sh

EXPOSE 5900 6080
VOLUME /home/wineuser/.wine

ENTRYPOINT ["/startup.sh"]