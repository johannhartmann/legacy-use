# Legacy Use Windows Target Integration

This directory contains the integration between legacy-use and dockur/windows to enable automation of Windows applications.

## Overview

The dockur/windows project runs Windows inside Docker containers using QEMU/KVM virtualization. By integrating it with legacy-use, we can:

1. Automatically provision Windows environments
2. Connect to them via RDP (recommended for automation)
3. Use AI-powered computer use to automate Windows applications
4. Turn legacy Windows applications into REST APIs

## How dockur/windows Works

### Architecture
- **QEMU**: Runs Windows in a virtual machine with KVM acceleration
- **VNC Display**: QEMU is configured with VNC display (internal port 5900)
- **noVNC**: Web-based VNC client served on port 8006
- **Websockify**: Proxies VNC TCP to WebSocket for browser access
- **RDP**: Windows RDP is automatically enabled after installation

### Windows Bootstrap Process
1. Container starts and downloads Windows ISO automatically
2. QEMU launches with the Windows installer
3. Automated installation using answer files
4. Windows boots with:
   - Auto-login enabled for specified user
   - RDP service started
   - Network configured
5. Installation progress viewable via web browser on port 8006

## Architecture

```
┌─────────────────┐     RDP      ┌──────────────────┐
│  Legacy Use     │ ──────────► │ Windows Container │
│  Session        │              │  (dockur/windows) │
│  Container      │              │                   │
└─────────────────┘              └──────────────────┘
     │                                    │
     │ Computer Use API                   │ Web Viewer
     ▼                                    ▼
┌─────────────────┐              ┌──────────────────┐
│  Legacy Use     │              │    Browser       │
│  Backend API    │              │  (Port 8006)     │
└─────────────────┘              └──────────────────┘
```

## Usage

### 1. Build the Windows Target Image

```bash
cd infra/docker/legacy-use-windows-target
docker build -t legacy-use-windows-target .
```

### 2. Start Windows Container

```bash
# With Kubernetes/Tilt
./scripts/kind-setup.sh  # One-time setup
./scripts/tilt-up.sh     # Start all services including Windows target
```

This will:
- Download and install Windows automatically
- Make it accessible via RDP on port 3389
- Provide web viewer on port 8006

### 3. Create Legacy Use Target

Once Windows is running, create a target in legacy-use:

```json
{
  "name": "Windows 11 Target",
  "type": "rdp",
  "host": "localhost",
  "port": 3389,
  "username": "LegacyUser",
  "password": "LegacyPass123!",
  "width": 1920,
  "height": 1080
}
```

### 4. Create Session and Use API

Create a session for the Windows target and use the legacy-use API to automate Windows applications.

## Configuration Options

### Windows Version
Set the `VERSION` environment variable:
- `11` - Windows 11
- `10` - Windows 10
- `2022` - Windows Server 2022
- `2019` - Windows Server 2019

### Resources
- `DISK_SIZE` - Disk size (default: 64G)
- `RAM_SIZE` - RAM allocation (default: 4G)
- `CPU_CORES` - CPU cores (default: 2)

### Credentials
- `USERNAME` - Windows username
- `PASSWORD` - Windows password

## Integration Benefits

1. **Automated Setup** - No manual Windows installation required
2. **Container-based** - Easy to deploy and scale
3. **Multiple Access Methods**:
   - **RDP** (Port 3389) - Native Windows remote desktop protocol
   - **VNC** (Port 5900) - Direct VNC access for automation
   - **Web Viewer** (Port 8006) - QEMU web interface for installation
   - **noVNC** (Port 6080) - Browser-based VNC access
4. **AI Automation** - Use computer use API to control Windows apps
5. **Kubernetes Ready** - Full Helm chart support with StatefulSet

## Requirements

- Docker with KVM support
- Virtualization enabled in BIOS
- Sufficient resources (disk, RAM, CPU)

## Security Considerations

1. Change default passwords
2. Use proper network isolation
3. Limit exposed ports in production
4. Consider VPN integration for secure access

## Troubleshooting

1. **KVM not available**: Ensure virtualization is enabled in BIOS
2. **Connection refused**: Wait for Windows to fully boot (can take 10-15 minutes on first run)
3. **Performance issues**: Allocate more RAM/CPU cores

## Future Enhancements

1. VNC server integration for alternative access
2. Automated Windows application installation
3. Snapshot/restore functionality
4. Multi-user support