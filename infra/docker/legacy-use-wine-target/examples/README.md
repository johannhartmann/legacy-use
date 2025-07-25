# Wine Target Example Applications

This directory contains example scripts for installing and running Windows applications in the Wine container.

## Usage

1. Start the Wine container:
```bash
# With Kubernetes/Tilt
./scripts/kind-setup.sh  # One-time setup  
./scripts/tilt-up.sh     # Start services
```

2. Copy installation scripts to the container:
```bash
docker cp examples/ legacy-use-wine-target:/home/wineuser/
```

3. Run installation scripts:
```bash
docker exec -it legacy-use-wine-target su - wineuser
cd examples
./install-notepad.sh
```

4. Access applications via VNC:
   - Web browser: http://localhost:6080/vnc.html (no password)
   - VNC client: localhost:5900 (no password)

## Example Applications

### Notepad++
Text editor with syntax highlighting
```bash
./install-notepad.sh
wine ~/.wine/drive_c/Program\ Files/Notepad++/notepad++.exe
```

### 7-Zip
File archiver and compression tool
```bash
./install-7zip.sh
wine ~/.wine/drive_c/Program\ Files/7-Zip/7zFM.exe
```

## Adding New Applications

1. Create installation script following the pattern:
```bash
#!/bin/bash
export DISPLAY=:1
export WINEPREFIX=/home/wineuser/.wine

# Download installer
wget -O /tmp/app.exe "https://example.com/app.exe"

# Install silently
wine /tmp/app.exe /S

# Create desktop shortcut (optional)
echo "[Desktop Entry]
Name=MyApp
Exec=wine /path/to/app.exe
Type=Application" > /home/wineuser/Desktop/myapp.desktop
```

2. Test the application works with VNC
3. Create legacy-use target pointing to the Wine container

## Common Wine Commands

```bash
# List installed programs
wine uninstaller

# Install .NET Framework
winetricks dotnet48

# Install Visual C++ runtime
winetricks vcrun2019

# Configure Wine
winecfg

# Registry editor
regedit

# Kill Wine processes
wineserver -k
```

## Troubleshooting

- Check Wine logs: `tail -f ~/.wine/drive_c/windows/wine.log`
- Verify display: `echo $DISPLAY` should show `:1`
- Test X11: `xclock` should show a clock
- Audio issues: Install pulseaudio or use `winetricks`