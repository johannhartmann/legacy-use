#!/bin/bash

# Example script to install Notepad++ via Wine
# Run this inside the Wine container

export DISPLAY=:1
export WINEPREFIX=/home/wineuser/.wine

echo "Installing Notepad++ via Wine..."

# Download Notepad++ installer
wget -O /tmp/notepad++.exe "https://github.com/notepad-plus-plus/notepad-plus-plus/releases/download/v8.5.8/npp.8.5.8.Installer.exe"

# Install Notepad++ silently
wine /tmp/notepad++.exe /S

# Create desktop shortcut
mkdir -p /home/wineuser/Desktop
echo "[Desktop Entry]
Name=Notepad++
Comment=Text Editor
Exec=wine /home/wineuser/.wine/drive_c/Program\\ Files/Notepad++/notepad++.exe
Icon=notepad++
Terminal=false
Type=Application
Categories=TextEditor;" > /home/wineuser/Desktop/notepad++.desktop

chmod +x /home/wineuser/Desktop/notepad++.desktop

echo "Notepad++ installation complete!"
echo "You can now run: wine ~/.wine/drive_c/Program\\ Files/Notepad++/notepad++.exe"