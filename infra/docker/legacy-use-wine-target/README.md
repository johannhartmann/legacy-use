# Legacy Use Wine Target

This provides a lightweight alternative to full Windows VMs using Wine (Wine Is Not an Emulator) to run Windows applications in Linux containers.

## Overview

Unlike the Windows VM approach (dockur/windows), this solution:
- Runs as a regular Linux container (no KVM required)
- Much smaller footprint (~2GB vs 64GB+)
- Faster startup (seconds vs minutes)
- Lower resource usage
- Compatible with any container runtime

## Features

- **Wine**: Runs many Windows applications
- **VNC Server**: Direct VNC access on port 5900
- **noVNC**: Web-based access on port 6080
- **Desktop Environment**: Fluxbox window manager
- **Pre-installed**: .NET Framework 4.8, Visual C++ 2019

## Limitations

- Not all Windows applications work with Wine
- No Windows kernel/driver support
- Some APIs may be incomplete
- GUI might behave differently

## Usage

### 1. Build and Start

```bash
# Build the image
docker build -t legacy-use-wine-target -f infra/docker/legacy-use-wine-target/Dockerfile .

# Start with Kubernetes/Tilt
./scripts/kind-setup.sh  # One-time setup
./scripts/tilt-up.sh     # Start services
```

### 2. Access Methods

**Web Browser (noVNC)**:
```bash
http://localhost:6080/vnc.html
No password required
```

**VNC Client**:
```bash
vncviewer localhost:5900
No password required
```

### 3. Install Windows Applications

1. Copy installer to container:
```bash
docker cp myapp.exe legacy-use-wine-target:/home/wineuser/apps/
```

2. Connect via VNC and run installer:
```bash
docker exec -it legacy-use-wine-target su - wineuser
wine /home/wineuser/apps/myapp.exe
```

### 4. Create Legacy Use Target

```json
{
  "name": "Wine Application",
  "type": "vnc",
  "host": "legacy-use-wine-target",
  "port": 5900,
  "password": "",
  "width": 1920,
  "height": 1080
}
```

## Kubernetes Deployment

See the Helm chart configuration for Wine targets in the infra/helm directory.

## Supported Applications

Wine has good support for:
- .NET Framework applications
- Legacy Win32 applications
- Many business applications
- Simple GUI tools

Check [WineHQ AppDB](https://appdb.winehq.org/) for compatibility.

## Troubleshooting

### Application Won't Start
```bash
# Check Wine output
docker exec -it legacy-use-wine-target su - wineuser
wine myapp.exe
```

### Missing Dependencies
```bash
# Install additional libraries
docker exec -it legacy-use-wine-target su - wineuser
winetricks dotnet40 vcrun2015
```

### Performance Issues
- Reduce screen resolution
- Disable visual effects
- Use native Linux alternatives when possible

## Comparison with Windows VM

| Feature | Wine Container | Windows VM |
|---------|---------------|------------|
| Startup Time | Seconds | 10-15 minutes |
| Disk Usage | ~2GB | 64GB+ |
| RAM Usage | ~500MB | 4GB+ |
| Compatibility | ~70% | 100% |
| Performance | Near native | Virtualized |
| License | Free | Windows license |

## When to Use

**Use Wine Container when:**
- Running simple Windows applications
- Resource constraints exist
- Fast startup is needed
- Running many instances

**Use Windows VM when:**
- Full Windows compatibility required
- Running complex applications
- Need Windows-specific features
- Driver support needed