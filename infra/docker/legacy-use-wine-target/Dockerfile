# Fast Wine container for development - uses Ubuntu's wine package with 32-bit support
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:1
ENV WINEARCH=win32
ENV WINEPREFIX=/home/wineuser/.wine32

# Enable 32-bit architecture for Wine
RUN dpkg --add-architecture i386 && \
    apt-get update && apt-get install -y --no-install-recommends \
    # Essential tools
    wget curl ca-certificates \
    # VNC and desktop
    xvfb x11vnc fluxbox xterm \
    # Process management
    supervisor \
    # Wine32 support for TurboCASH
    wine32 wine64 \
    # Wine dependencies for Windows apps
    winbind fonts-wine \
    # Additional libraries that TurboCASH might need
    lib32z1 lib32ncurses6 libc6:i386 libncurses5:i386 libstdc++6:i386 \
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

# Download TurboCASH installer
USER root
RUN wget -q -O /home/wineuser/TurboCASH_Setup.exe "https://sourceforge.net/projects/turbocash/files/TurboCASH%20Accounting/TurboCASH%205.0.8.0/TurboCASH5_Setup_5.0.8.0.exe/download" || \
    wget -q -O /home/wineuser/TurboCASH_Setup.exe "https://sourceforge.net/projects/turbocash/files/latest/download" && \
    chown wineuser:wineuser /home/wineuser/TurboCASH_Setup.exe

# Create startup script  
USER root
RUN cat > /startup.sh << 'EOF'
#!/bin/bash
set -e
echo "Starting Wine container..."

# Initialize Wine32 at runtime
su - wineuser -c "WINEARCH=win32 WINEPREFIX=/home/wineuser/.wine32 wineboot --init 2>/dev/null || true" &

# Wait for Wine initialization
sleep 10

# Create desktop shortcut for installer
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

EXPOSE 5900 6080
VOLUME /home/wineuser/.wine32

ENTRYPOINT ["/startup.sh"]