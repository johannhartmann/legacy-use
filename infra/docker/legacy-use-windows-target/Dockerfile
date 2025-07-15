FROM dockurr/windows:latest

# Set environment variables for Windows configuration
ENV VERSION="11"
ENV DISK_SIZE="64G"
ENV RAM_SIZE="4G"
ENV CPU_CORES="2"
ENV USERNAME="LegacyUser"
ENV PASSWORD="LegacyPass123!"

# Expose ports
# 8006 - Existing noVNC web viewer from dockur/windows
# 3389 - RDP
# 5900 - Direct VNC access (if we expose QEMU's VNC)
EXPOSE 8006
EXPOSE 3389
EXPOSE 5900

# Note: dockur/windows already includes:
# - QEMU with VNC display enabled (internal port 5900)
# - noVNC web interface on port 8006
# - Websockify proxying VNC to WebSocket
# 
# The web viewer uses noVNC to connect to QEMU's VNC display
# For direct VNC access, we would need to expose QEMU's VNC port
# or modify the QEMU launch parameters

# For Windows bootstrap:
# 1. dockur/windows automatically downloads and installs Windows
# 2. It sets up auto-login with the specified username/password
# 3. Enables RDP automatically after installation
# 4. The installation process can be monitored via port 8006

# No additional VNC setup needed - dockur/windows provides it
# The original entrypoint handles everything