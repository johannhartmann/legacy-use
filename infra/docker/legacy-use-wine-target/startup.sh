#!/bin/bash
set -e
echo "Starting Wine container..."

# Create Desktop directory first
mkdir -p /home/wineuser/Desktop

# Fix ownership of .wine32 directory if it exists
chown -R wineuser:wineuser /home/wineuser/.wine32 2>/dev/null || true

# Initialize Wine32 at runtime
su - wineuser -c "WINEARCH=win32 WINEPREFIX=/home/wineuser/.wine32 wine wineboot --init 2>/dev/null || true" &

# Wait for Wine initialization
sleep 10

# Start Wine Explorer in background
su - wineuser -c "DISPLAY=:1 WINEPREFIX=/home/wineuser/.wine32 wine explorer /desktop=shell,1280x800 2>/dev/null" &

# Start supervisor
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf