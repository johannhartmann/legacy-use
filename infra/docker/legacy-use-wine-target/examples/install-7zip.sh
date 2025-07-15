#!/bin/bash

# Example script to install 7-Zip via Wine
# Run this inside the Wine container

export DISPLAY=:1
export WINEPREFIX=/home/wineuser/.wine

echo "Installing 7-Zip via Wine..."

# Download 7-Zip installer
wget -O /tmp/7z-installer.exe "https://www.7-zip.org/a/7z2301-x64.exe"

# Install 7-Zip silently
wine /tmp/7z-installer.exe /S

# Create desktop shortcut
mkdir -p /home/wineuser/Desktop
echo "[Desktop Entry]
Name=7-Zip
Comment=File Archiver
Exec=wine /home/wineuser/.wine/drive_c/Program\\ Files/7-Zip/7zFM.exe
Icon=7zip
Terminal=false
Type=Application
Categories=Archiving;" > /home/wineuser/Desktop/7zip.desktop

chmod +x /home/wineuser/Desktop/7zip.desktop

echo "7-Zip installation complete!"
echo "You can now run: wine ~/.wine/drive_c/Program\\ Files/7-Zip/7zFM.exe"