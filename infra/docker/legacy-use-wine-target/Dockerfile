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

# Simple supervisor config (removed noVNC - now using shared proxy)
# VNC without password - removed -usepw and -rfbauth flags
RUN printf '[supervisord]\nnodaemon=true\nuser=root\n\n[program:xvfb]\ncommand=/usr/bin/Xvfb :1 -screen 0 1920x1080x24\nautorestart=true\nuser=root\npriority=100\n\n[program:x11vnc]\ncommand=/usr/bin/x11vnc -display :1 -forever -shared -rfbport 5900 -noshm\nautorestart=true\nuser=wineuser\npriority=200\n\n[program:fluxbox]\ncommand=/usr/bin/fluxbox -display :1\nautorestart=true\nuser=wineuser\nenvironment=HOME="/home/wineuser",DISPLAY=":1"\npriority=400\n' > /etc/supervisor/conf.d/supervisord.conf

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

# Create startup script  
USER root
RUN cat > /startup.sh << 'EOF'
#!/bin/bash
set -e
echo "Starting Wine container..."

# Create Desktop directory first
su - wineuser -c "mkdir -p /home/wineuser/Desktop"

# Fix ownership of .wine32 directory if it exists
chown -R wineuser:wineuser /home/wineuser/.wine32 2>/dev/null || true

# Initialize Wine32 at runtime
su - wineuser -c "WINEARCH=win32 WINEPREFIX=/home/wineuser/.wine32 wine wineboot --init 2>/dev/null || true" &

# Wait for Wine initialization
sleep 10

# Start Wine Explorer in background
su - wineuser -c "DISPLAY=:1 WINEPREFIX=/home/wineuser/.wine32 wine explorer /desktop=shell,1920x1080 2>/dev/null" &

# Create desktop shortcut for Lotus installer
su - wineuser -c 'cat > /home/wineuser/Desktop/Install_Lotus.desktop << EOD
[Desktop Entry]
Version=1.0
Type=Application
Name=Install Lotus Demo
Exec=env WINEPREFIX=/home/wineuser/.wine32 wine /home/wineuser/lotus/install.exe
Icon=system-software-install
Terminal=false
Categories=System;
EOD
chmod +x /home/wineuser/Desktop/Install_Lotus.desktop' || true

# Create desktop shortcut for TurboCASH installer
su - wineuser -c 'cat > /home/wineuser/Desktop/Install_TurboCASH.desktop << EOD
[Desktop Entry]
Version=1.0
Type=Application
Name=Install TurboCASH
Exec=env WINEPREFIX=/home/wineuser/.wine32 wine /home/wineuser/TurboCASH_Setup.exe
Icon=system-software-install
Terminal=false
Categories=System;
EOD
chmod +x /home/wineuser/Desktop/Install_TurboCASH.desktop' || true

# Create xterm launcher
su - wineuser -c 'cat > /home/wineuser/Desktop/Terminal.desktop << EOD
[Desktop Entry]
Version=1.0
Type=Application
Name=Terminal
Exec=xterm
Icon=utilities-terminal
Terminal=false
Categories=System;
EOD
chmod +x /home/wineuser/Desktop/Terminal.desktop' || true

# Create file manager launcher  
su - wineuser -c 'cat > /home/wineuser/Desktop/FileManager.desktop << EOD
[Desktop Entry]
Version=1.0
Type=Application
Name=Wine Explorer
Exec=env WINEPREFIX=/home/wineuser/.wine32 wine explorer
Icon=folder
Terminal=false
Categories=System;
EOD
chmod +x /home/wineuser/Desktop/FileManager.desktop' || true

# Start supervisor
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
EOF

RUN chmod +x /startup.sh

EXPOSE 5900
VOLUME /home/wineuser/.wine32

ENTRYPOINT ["/startup.sh"]