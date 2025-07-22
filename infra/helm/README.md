# Legacy-use Helm Chart

This Helm chart deploys the Legacy-use platform on Kubernetes, providing a scalable way to run legacy applications as modern REST APIs.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.2.0+
- PV provisioner support in the underlying infrastructure (for persistence)
- Optional: NGINX Ingress Controller
- Optional: cert-manager (for TLS certificates)

## Installation

### Add the Helm repository (if published)

```bash
helm repo add legacy-use https://your-repo-url
helm repo update
```

### Install from local directory

```bash
# Install with default values
helm install legacy-use ./infra/helm

# Install with custom values
helm install legacy-use ./infra/helm -f values-production.yaml

# Install in a specific namespace
helm install legacy-use ./infra/helm -n legacy-use --create-namespace
```

## Configuration

The following table lists the main configurable parameters:

### Global Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `imagePullSecrets` | Array of image pull secrets | `[]` |
| `nameOverride` | Override the chart name | `""` |
| `fullnameOverride` | Override the full chart name | `""` |

### Database Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `database.enabled` | Enable PostgreSQL database | `true` |
| `database.image.repository` | PostgreSQL image repository | `postgres` |
| `database.image.tag` | PostgreSQL image tag | `15-alpine` |
| `database.postgresUser` | PostgreSQL user | `postgres` |
| `database.postgresPassword` | PostgreSQL password | `postgres` |
| `database.postgresDatabase` | PostgreSQL database name | `legacy_use_demo` |
| `database.persistence.enabled` | Enable persistence | `true` |
| `database.persistence.size` | PVC size | `10Gi` |

### Management Service (Backend + Frontend)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `management.replicaCount` | Number of replicas | `1` |
| `management.image.repository` | Image repository | `legacy-use-mgmt` |
| `management.image.tag` | Image tag | `local` |
| `management.env.LEGACY_USE_DEBUG` | Enable debug mode | `"0"` |
| `management.env.ANTHROPIC_API_KEY` | Anthropic API key | `""` |
| `management.existingSecret` | Use existing secret for sensitive data | `""` |
| `management.service.backendPort` | Backend service port | `8088` |
| `management.service.frontendPort` | Frontend service port | `5173` |

### MCP Server Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `mcpServer.enabled` | Enable MCP server | `true` |
| `mcpServer.replicaCount` | Number of replicas | `1` |
| `mcpServer.image.repository` | Image repository | `legacy-use-mcp-server` |
| `mcpServer.logLevel` | Log level | `INFO` |
| `mcpServer.syncInterval` | Sync interval in seconds | `30` |

### Target Configurations

#### Wine Target (Lightweight Windows apps)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `wineTarget.enabled` | Enable Wine target | `true` |
| `wineTarget.replicas` | Number of replicas | `1` |
| `wineTarget.wineArch` | Wine architecture (win32/win64) | `win64` |
| `wineTarget.persistence.enabled` | Enable persistence | `true` |
| `wineTarget.persistence.wineSize` | Wine data volume size | `10Gi` |
| `wineTarget.persistence.appsSize` | Apps volume size | `5Gi` |

#### Linux Target

| Parameter | Description | Default |
|-----------|-------------|---------|
| `linuxTarget.enabled` | Enable Linux target | `true` |
| `linuxTarget.replicas` | Number of replicas | `1` |
| `linuxTarget.service.vncPort` | VNC port | `5900` |
| `linuxTarget.service.novncPort` | noVNC port | `80` |

#### Android Target

| Parameter | Description | Default |
|-----------|-------------|---------|
| `androidTarget.enabled` | Enable Android target | `true` |
| `androidTarget.replicas` | Number of replicas | `1` |
| `androidTarget.emulatorDevice` | Emulator device type | `Samsung Galaxy S10` |
| `androidTarget.persistence.androidSize` | Android data volume size | `20Gi` |
| `androidTarget.persistence.appsSize` | Apps volume size | `5Gi` |

#### Windows XP KubeVirt VM (Requires KubeVirt)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `windowsXpKubevirt.enabled` | Enable Windows XP KubeVirt VMs | `false` |
| `windowsXpKubevirt.replicas` | Number of VM instances | `1` |
| `windowsXpKubevirt.hostname` | VM hostname | `legacy-winxp` |
| `windowsXpKubevirt.cpu.cores` | CPU cores per VM | `4` |
| `windowsXpKubevirt.memory` | Memory per VM | `8Gi` |
| `windowsXpKubevirt.diskUrl` | URL for Windows XP image (CDI) | `https://intranet.mayflower.de/s/sPD3fEnNQGWATLC/download?path=%2F&files=winxp.qcow2` |
| `windowsXpKubevirt.containerDiskImage` | Windows XP container disk image | `""` |
| `windowsXpKubevirt.ephemeralDisk` | Use ephemeral disk | `false` |
| `windowsXpKubevirt.persistence.size` | Disk size | `100Gi` |
| `windowsXpKubevirt.service.rdpPort` | RDP service port | `3389` |
| `windowsXpKubevirt.service.vncPort` | VNC service port | `5900` |

#### Windows 10 KubeVirt VM (Requires KubeVirt)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `windows10Kubevirt.enabled` | Enable Windows 10 KubeVirt VMs | `false` |
| `windows10Kubevirt.replicas` | Number of VM instances | `1` |
| `windows10Kubevirt.hostname` | VM hostname | `legacy-win10` |
| `windows10Kubevirt.cpu.cores` | CPU cores per VM | `4` |
| `windows10Kubevirt.memory` | Memory per VM | `8Gi` |
| `windows10Kubevirt.diskUrl` | URL for Windows 10 image (CDI) | `https://intranet.mayflower.de/s/sPD3fEnNQGWATLC/download?path=%2F&files=win10.qcow2` |
| `windows10Kubevirt.containerDiskImage` | Windows 10 container disk image | `""` |
| `windows10Kubevirt.ephemeralDisk` | Use ephemeral disk | `false` |
| `windows10Kubevirt.persistence.size` | Disk size | `120Gi` |
| `windows10Kubevirt.service.rdpPort` | RDP service port | `3389` |
| `windows10Kubevirt.service.vncPort` | VNC service port | `5900` |

### Ingress Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.className` | Ingress class name | `""` |
| `ingress.hosts[0].host` | Hostname | `legacy-use.local` |
| `ingress.tls` | TLS configuration | `[]` |

## Usage Examples

### Minimal Installation

```bash
helm install legacy-use ./infra/helm -f values-minimal.yaml
```

### Development Installation

```bash
helm install legacy-use ./infra/helm -f values-dev.yaml
```

### Production Installation

```bash
# Create secrets first
kubectl create secret generic legacy-use-secrets \
  --from-literal=anthropic-api-key=$ANTHROPIC_API_KEY \
  --from-literal=legacy-use-api-key=$LEGACY_USE_API_KEY

# Install with production values
helm install legacy-use ./infra/helm -f values-production.yaml
```

### Enable Only Specific Targets

```bash
helm install legacy-use ./infra/helm \
  --set wineTarget.enabled=true \
  --set linuxTarget.enabled=false \
  --set androidTarget.enabled=false
```

### Use External Database

```bash
helm install legacy-use ./infra/helm \
  --set database.enabled=false \
  --set management.env.DATABASE_URL="postgresql://user:pass@external-db:5432/legacy_use"
```

## Upgrading

```bash
# Upgrade to a new version
helm upgrade legacy-use ./infra/helm

# Upgrade with new values
helm upgrade legacy-use ./infra/helm -f values-production.yaml

# Rollback if needed
helm rollback legacy-use
```

## Uninstallation

```bash
# Uninstall the release
helm uninstall legacy-use

# Delete the namespace (if created)
kubectl delete namespace legacy-use
```

## Persistence

The chart supports persistence for:
- PostgreSQL database
- Wine target data and applications
- Android target data and applications
- Windows target storage

To disable persistence (not recommended for production):

```bash
helm install legacy-use ./infra/helm \
  --set database.persistence.enabled=false \
  --set wineTarget.persistence.enabled=false \
  --set androidTarget.persistence.enabled=false
```

## Security Considerations

1. **Secrets Management**: Use Kubernetes secrets for sensitive data like API keys
2. **Network Policies**: Enable network policies in production
3. **Pod Security**: The Android and Windows targets require privileged access
4. **Docker Socket**: The management service requires access to Docker socket for container management

## Troubleshooting

### Check deployment status

```bash
kubectl get all -l app.kubernetes.io/name=legacy-use
```

### View logs

```bash
# Management service logs
kubectl logs -l app.kubernetes.io/component=management

# Database logs
kubectl logs -l app.kubernetes.io/component=database

# Target logs
kubectl logs -l app.kubernetes.io/component=wine-target
```

### Access the application

```bash
# Port forward to access locally
kubectl port-forward svc/legacy-use-mgmt 8088:8088 5173:5173

# Access the UI
open http://localhost:5173

# Access the API
curl http://localhost:8088/health
```

## Advanced Configuration

### Using with Kind + KubeVirt

For running actual Windows/macOS VMs, integrate with KubeVirt:

```bash
# First setup Kind with KubeVirt (see docs/kind-kubevirt.md)
./scripts/kind-setup.sh

# Then install legacy-use
helm install legacy-use ./infra/helm -f values-dev.yaml
```

### Windows VM with KubeVirt

To deploy Windows XP VM using KubeVirt:

```bash
# Option 1: Use pre-built Windows XP image with CDI (default)
helm install legacy-use ./infra/helm \
  --set windowsXpKubevirt.enabled=true
# Uses default diskUrl: https://intranet.mayflower.de/s/sPD3fEnNQGWATLC/download?path=%2F&files=winxp.qcow2

# Option 2: Use container disk image
helm install legacy-use ./infra/helm \
  --set windowsXpKubevirt.enabled=true \
  --set windowsXpKubevirt.containerDiskImage="your-registry/windows-xp:latest"

# Access Windows XP VMs
kubectl get vmirs -l legacy-use.target-type=windows-xp-vm  # List Windows XP VMs
kubectl get vmi -l legacy-use.target-type=windows-xp-vm    # List VM Instances
```

To deploy Windows 10 VM using KubeVirt:

```bash
# Option 1: Use pre-built Windows 10 image with CDI (default)
helm install legacy-use ./infra/helm \
  --set windows10Kubevirt.enabled=true
# Uses default diskUrl: https://intranet.mayflower.de/s/sPD3fEnNQGWATLC/download?path=%2F&files=win10.qcow2

# Option 2: Deploy both Windows XP and Windows 10
helm install legacy-use ./infra/helm \
  --set windowsXpKubevirt.enabled=true \
  --set windows10Kubevirt.enabled=true

# Access Windows 10 VMs
kubectl get vmirs -l legacy-use.target-type=windows-10-vm  # List Windows 10 VMs
kubectl get vmi -l legacy-use.target-type=windows-10-vm    # List VM Instances

# Option 3: Use custom values file
helm install legacy-use ./infra/helm -f values-windows10-example.yaml

# Scale Windows VMs
kubectl scale vmirs legacy-use-windows-xp-vmirs --replicas=3
kubectl scale vmirs legacy-use-windows-10-vmirs --replicas=2

# Access specific VM instance
kubectl virt console <vmi-name>  # Console access
kubectl virt vnc <vmi-name>      # VNC access

# Port forward for RDP (load-balanced across all instances)
kubectl port-forward svc/legacy-use-windows-kubevirt 3389:3389
```

### Scaling Targets

```bash
# Scale Wine targets
kubectl scale deployment legacy-use-wine-target --replicas=5

# Or use Helm
helm upgrade legacy-use ./helm --set wineTarget.replicas=5
```

### Custom Storage Classes

```yaml
# values-custom-storage.yaml
database:
  persistence:
    storageClass: "fast-ssd"
    
wineTarget:
  persistence:
    storageClass: "fast-ssd"
```

## Contributing

See the main [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines on contributing to this project.

## License

This chart is licensed under the MIT License. See the [LICENSE](../LICENSE) file for details.