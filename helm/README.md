# Legacy Use Helm Chart

This Helm chart deploys the Legacy Use application to Kubernetes with optional Windows target support.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- Docker images available (either built locally or from GitHub Container Registry)
- For Windows targets: Nodes with KVM support and /dev/kvm device

## Installation

### Basic Installation

```bash
# Install with production values
helm install legacy-use . -n legacy-use --create-namespace -f values-production.yaml

# Or upgrade existing installation
helm upgrade legacy-use . -n legacy-use -f values-production.yaml
```

### Installation with Wine Target (Recommended for Windows Apps)

To include a Wine container for lightweight Windows application automation:

```bash
# Install with Wine support
helm install legacy-use . -n legacy-use --create-namespace \
  -f values-production.yaml \
  -f values-wine.yaml

# Or enable Wine in existing installation
helm upgrade legacy-use . -n legacy-use \
  -f values-production.yaml \
  -f values-wine.yaml
```

### Installation with Windows Target (Full VM)

To include a Windows target for automating Windows applications:

```bash
# Create custom values file
cat > values-windows.yaml <<EOF
windowsTarget:
  enabled: true
  windowsVersion: "11"
  username: "MyUser"
  password: "MySecurePassword123!"
  nodeSelector:
    kubernetes.io/hostname: node-with-kvm
EOF

# Install with Windows support
helm install legacy-use . -n legacy-use --create-namespace \
  -f values-production.yaml \
  -f values-windows.yaml
```

## Wine Target (Lightweight Windows Apps)

The Wine container provides lightweight Windows application support without needing a full Windows VM:

### Access Methods

#### 1. VNC Access (Port 5900)
Direct VNC access for legacy-use automation:
```bash
kubectl port-forward -n legacy-use deployment/legacy-use-wine-target 5900:5900
# Connect with VNC client to localhost:5900 (password: wine)
```

#### 2. noVNC Web Interface (Port 6080)
Web-based VNC access:
```bash
kubectl port-forward -n legacy-use deployment/legacy-use-wine-target 6080:6080
# Access at http://localhost:6080/vnc.html (password: wine)
```

### Installing Windows Applications

```bash
# 1. Copy installer to Wine container
kubectl cp myapp.exe legacy-use/legacy-use-wine-target:/home/wineuser/apps/

# 2. Access Wine desktop via web browser
kubectl port-forward -n legacy-use deployment/legacy-use-wine-target 6080:6080
# Open http://localhost:6080/vnc.html

# 3. Install application in Wine desktop
# Open terminal and run: wine /home/wineuser/apps/myapp.exe
```

### Create Wine Target in Legacy Use

```json
{
  "name": "Wine Applications",
  "type": "vnc",
  "host": "legacy-use-wine-target",
  "port": 5900,
  "password": "wine",
  "width": 1920,
  "height": 1080
}
```

### Wine vs Windows VM Comparison

| Feature | Wine Container | Windows VM |
|---------|----------------|------------|
| Resource Usage | ~2GB RAM, 10GB disk | ~8GB RAM, 64GB disk |
| Startup Time | 30 seconds | 10-15 minutes |
| Compatibility | ~70% of Windows apps | 100% compatibility |
| License | Free | Requires Windows license |
| Performance | Near-native | VM overhead |

**Use Wine when:** You need lightweight Windows app support with fast startup
**Use Windows VM when:** You need full Windows compatibility or complex applications

## Linux Target (Example Machine)

The Linux target provides an example Linux machine for testing:

### Enable Linux Target

```bash
helm install legacy-use . -n legacy-use --create-namespace \
  -f values-production.yaml \
  -f values-linux.yaml
```

### Access Linux Target

```bash
# VNC access
kubectl port-forward -n legacy-use deployment/legacy-use-linux-target 5900:5900

# noVNC web access
kubectl port-forward -n legacy-use deployment/legacy-use-linux-target 6080:6080
# Access at http://localhost:6080/vnc.html
```

### Create Linux Target in Legacy Use

```json
{
  "name": "Linux Machine",
  "type": "vnc",
  "host": "legacy-use-linux-target",
  "port": 5900,
  "width": 1920,
  "height": 1080
}
```

## Android Target (Mobile App Automation)

The Android target provides an Android emulator for mobile app automation:

### Enable Android Target

```bash
helm install legacy-use . -n legacy-use --create-namespace \
  -f values-production.yaml \
  -f values-android.yaml
```

### Access Android Target

```bash
# ADB access for debugging
kubectl port-forward -n legacy-use deployment/legacy-use-android-target 5555:5555
adb connect localhost:5555

# VNC access
kubectl port-forward -n legacy-use deployment/legacy-use-android-target 5900:5900

# noVNC web access
kubectl port-forward -n legacy-use deployment/legacy-use-android-target 6080:6080
# Access at http://localhost:6080/vnc.html
```

### Create Android Target in Legacy Use

```json
{
  "name": "Android Emulator",
  "type": "vnc",
  "host": "legacy-use-android-target",
  "port": 5900,
  "width": 1080,
  "height": 2340
}
```

### Installing Android Apps

```bash
# 1. Copy APK to Android container
kubectl cp myapp.apk legacy-use/legacy-use-android-target:/home/androidusr/apps/

# 2. Install via ADB
kubectl port-forward -n legacy-use deployment/legacy-use-android-target 5555:5555
adb connect localhost:5555
adb install /home/androidusr/apps/myapp.apk

# 3. Or access Android desktop via web browser
kubectl port-forward -n legacy-use deployment/legacy-use-android-target 6080:6080
# Open http://localhost:6080/vnc.html
```

### Android vs Other Targets Comparison

| Feature | Android Emulator | Wine Container | Windows VM | Linux Machine |
|---------|-----------------|----------------|------------|---------------|
| Resource Usage | ~4GB RAM, 20GB disk | ~2GB RAM, 10GB disk | ~8GB RAM, 64GB disk | ~1GB RAM, 5GB disk |
| Startup Time | 2-3 minutes | 30 seconds | 10-15 minutes | 20 seconds |
| Use Case | Mobile apps | Windows apps | Full Windows | Linux apps |
| License | Free | Free | Windows license | Free |

**Use Android when:** You need to automate Android mobile applications
**Use Wine when:** You need lightweight Windows desktop app support
**Use Windows VM when:** You need full Windows compatibility
**Use Linux when:** You need to automate Linux desktop applications

## Windows Target Access Methods (Full VM)

The Windows target provides multiple ways to access the Windows desktop:

### 1. Web Viewer (Port 8006) - Built-in noVNC
Browser-based VNC access to Windows (provided by dockur/windows):
```bash
kubectl port-forward -n legacy-use statefulset/legacy-use-windows-target 8006:8006
# Access at http://localhost:8006
```
- Uses noVNC to connect to QEMU's VNC display
- Good for installation monitoring
- Limited quality, no audio/clipboard
- No authentication by default

### 2. RDP Access (Port 3389) - Recommended
Native Windows Remote Desktop for best performance:
```bash
kubectl port-forward -n legacy-use statefulset/legacy-use-windows-target 3389:3389
# Connect with any RDP client to localhost:3389
```
- Full Windows desktop experience
- Audio and clipboard support
- Better performance than VNC
- Use this for legacy-use automation

### 3. Direct VNC Access (Port 5900) - If Needed
Direct connection to QEMU's VNC server:
```bash
# Note: Requires QEMU to be configured with external VNC access
kubectl port-forward -n legacy-use statefulset/legacy-use-windows-target 5900:5900
# Connect with VNC client to localhost:5900
```
- Raw VNC protocol
- May require additional configuration

## Creating Windows Targets in Legacy Use

Once Windows is running (check installation progress at port 8006), create an RDP target in legacy-use:

```json
{
  "name": "Windows 11 Target",
  "type": "rdp",
  "host": "legacy-use-windows-target",
  "port": 3389,
  "username": "MyUser",
  "password": "MySecurePassword123!",
  "width": 1920,
  "height": 1080
}
```

**Note**: Use RDP for Windows automation. The VNC display (port 8006) is primarily for installation monitoring and uses QEMU's display, not the Windows desktop directly.

## Configuration Options

### Core Application
- `backend.image.repository` - Backend Docker image repository
- `backend.image.tag` - Backend Docker image tag
- `frontend.image.repository` - Frontend Docker image repository  
- `frontend.image.tag` - Frontend Docker image tag
- `ingress.enabled` - Enable/disable ingress
- `ingress.hosts` - Configure ingress hostnames

### Windows Target
- `windowsTarget.enabled` - Enable Windows target deployment
- `windowsTarget.windowsVersion` - Windows version (11, 10, 2022, 2019)
- `windowsTarget.diskSize` - Disk size (default: 64G)
- `windowsTarget.ramSize` - RAM allocation (default: 8G)
- `windowsTarget.cpuCores` - CPU cores (default: 4)
- `windowsTarget.username` - Windows username
- `windowsTarget.password` - Windows password
- `windowsTarget.storageSize` - PVC size (default: 100Gi)
- `windowsTarget.nodeSelector` - Node selection for KVM support

## Troubleshooting Windows Target

### KVM Not Available
```bash
# Check if node has KVM
kubectl get nodes -o json | jq '.items[].status.allocatable["devices.kubevirt.io/kvm"]'

# Label nodes with KVM support
kubectl label nodes <node-name> kvm-enabled=true
```

### Windows Installation Status
```bash
# Check logs
kubectl logs -n legacy-use statefulset/legacy-use-windows-target

# Watch installation progress
kubectl port-forward -n legacy-use statefulset/legacy-use-windows-target 8006:8006
# Open http://localhost:8006 in browser
```

### Storage Issues
```bash
# Check PVC status
kubectl get pvc -n legacy-use

# Increase storage if needed by editing values and upgrading
```

## Example: Automating Windows Calculator

1. Create Windows target (see above)
2. Create session via API
3. Use computer use API to automate:

```python
import requests

# Create session
session = requests.post(
    "http://legacy-use-api/sessions",
    json={"target_id": "windows-target-id"},
    headers={"X-API-Key": "your-api-key"}
).json()

# Send computer use command
result = requests.post(
    f"http://legacy-use-api/sessions/{session['id']}/computer",
    json={
        "action": "screenshot"  # Take screenshot
    },
    headers={"X-API-Key": "your-api-key"}
)

# Type to open calculator
result = requests.post(
    f"http://legacy-use-api/sessions/{session['id']}/computer",
    json={
        "action": "key",
        "text": "cmd+r"  # Windows key + R
    },
    headers={"X-API-Key": "your-api-key"}
)

result = requests.post(
    f"http://legacy-use-api/sessions/{session['id']}/computer",
    json={
        "action": "type",
        "text": "calc"
    },
    headers={"X-API-Key": "your-api-key"}
)
```

## MCP Server

Legacy-use includes an MCP (Model Context Protocol) server that exposes all APIs as tools for Claude Desktop.

### Enable MCP Server

```bash
helm install legacy-use . -n legacy-use --create-namespace \
  -f values-production.yaml \
  -f values-mcp.yaml
```

### MCP Server Configuration

The MCP server can be configured via values:

```yaml
mcpServer:
  enabled: true
  replicaCount: 2
  logLevel: "INFO"
  syncInterval: "30"  # Check for API changes every 30 seconds
```

### Using with Claude Desktop

1. Port-forward the MCP server (if not exposed via ingress):
```bash
kubectl port-forward -n legacy-use deployment/legacy-use-mcp-server 3000:3000
```

2. Configure Claude Desktop to use the MCP server. See [mcp-server/claude-desktop-config.md](../mcp-server/claude-desktop-config.md) for detailed instructions.

## Uninstall

```bash
helm uninstall legacy-use -n legacy-use
```