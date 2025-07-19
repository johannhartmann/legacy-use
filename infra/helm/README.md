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

#### Windows KubeVirt VM (Requires KubeVirt)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `windowsKubevirt.enabled` | Enable Windows KubeVirt VMs | `false` |
| `windowsKubevirt.replicas` | Number of VM instances | `1` |
| `windowsKubevirt.hostname` | VM hostname prefix | `legacy-win` |
| `windowsKubevirt.cpu.cores` | CPU cores per VM | `4` |
| `windowsKubevirt.memory` | Memory per VM | `8Gi` |
| `windowsKubevirt.containerDiskImage` | Windows container disk image | `quay.io/kubevirt/windows11:latest` |
| `windowsKubevirt.ephemeralDisk` | Use ephemeral disk instead | `false` |
| `windowsKubevirt.persistence.size` | Disk size (ephemeral mode) | `100Gi` |
| `windowsKubevirt.service.rdpPort` | RDP service port | `3389` |
| `windowsKubevirt.service.vncPort` | VNC service port | `5900` |

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

To deploy a Windows VM using KubeVirt instead of Docker:

```bash
# Option 1: Use pre-built Windows image
helm install legacy-use ./infra/helm \
  --set windowsKubevirt.enabled=true \
  --set windowsKubevirt.dataVolumeTemplate.enabled=true \
  --set windowsKubevirt.dataVolumeTemplate.source.http.url="http://example.com/windows.qcow2"

# Option 2: Use existing PVC with Windows image
helm install legacy-use ./infra/helm \
  --set windowsKubevirt.enabled=true \
  --set windowsKubevirt.dataVolumeTemplate.enabled=true \
  --set windowsKubevirt.dataVolumeTemplate.source.pvc.name="windows-golden-image" \
  --set windowsKubevirt.dataVolumeTemplate.source.pvc.namespace="default"

# Access Windows VMs
kubectl get vmirs  # List VirtualMachineInstanceReplicaSets
kubectl get vmi    # List Virtual Machine Instances

# Scale Windows VMs
kubectl scale vmirs legacy-use-windows-vmirs --replicas=3

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