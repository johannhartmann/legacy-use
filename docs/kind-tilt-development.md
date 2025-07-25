# Kind + Tilt Development Workflow

This guide describes how to use Kind (Kubernetes in Docker) with Tilt for local development of Legacy-use.

## Overview

The development workflow combines:
- **Kind**: Local Kubernetes cluster running in Docker
- **Local Registry**: Docker registry on port 5001 for fast image updates
- **Tilt**: Development tool that watches files and automatically updates Kubernetes
- **KubeVirt**: Support for running actual Windows VMs (optional)

## Prerequisites

1. Install required tools:
   ```bash
   # Docker (required)
   # https://docs.docker.com/get-docker/

   # Kind
   curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
   chmod +x ./kind
   sudo mv ./kind /usr/local/bin/kind

   # kubectl
   curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
   chmod +x kubectl
   sudo mv kubectl /usr/local/bin/

   # Helm
   curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

   # Tilt
   curl -fsSL https://raw.githubusercontent.com/tilt-dev/tilt/master/scripts/install.sh | bash
   ```

2. Set up environment variables:
   ```bash
   # Create .env file
   cp .env.example .env
   
   # Add your Anthropic API key
   echo "ANTHROPIC_API_KEY=your-api-key" >> .env
   ```

## Quick Start

1. **Set up Kind cluster (includes registry and KubeVirt):**
   ```bash
   ./scripts/kind-setup.sh
   ```

2. **Start Tilt development environment:**
   ```bash
   ./scripts/tilt-up.sh
   ```

3. **Access services:**
   - Tilt UI: http://localhost:10350
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8088
   - PostgreSQL: localhost:5432

4. **Stop development environment:**
   ```bash
   ./scripts/tilt-down.sh
   ```

## Development Workflow

### File Watching and Hot Reload

Tilt automatically watches for changes and updates the cluster:

- **Frontend (app/)**: Changes trigger automatic rebuild and restart
- **Backend (server/)**: Changes trigger automatic restart
- **Docker images**: Changes to Dockerfiles trigger rebuilds
- **Helm charts**: Changes to values or templates trigger redeployment

### Building Images Manually

If you need to build images without Tilt:

```bash
# Build all images
./scripts/build-and-push.sh all

# Build specific image
./scripts/build-and-push.sh mgmt
./scripts/build-and-push.sh wine

# List images in registry
./scripts/build-and-push.sh --list
```

### Working with the Cluster

```bash
# Get cluster info
kubectl cluster-info --context kind-legacy-use

# List all resources
kubectl get all -n legacy-use

# View logs
kubectl logs -n legacy-use -l app.kubernetes.io/component=management

# Access a specific pod
kubectl exec -it -n legacy-use deployment/legacy-use-mgmt -- bash
```

### Database Operations

```bash
# Run migrations (via Tilt UI or manually)
cd server && uv run alembic upgrade head

# Generate API key
cd server && uv run python generate_api_key.py

# Access database
kubectl port-forward -n legacy-use svc/legacy-use-database 5432:5432
psql -h localhost -U postgres -d legacy_use_demo
```

## Target Access

### Wine Target (Windows Apps)
- VNC: vnc://localhost:5900 (no password)
- noVNC: http://localhost:6080

### Linux Target
- VNC: vnc://localhost:5901 (password: password123)
- noVNC: http://localhost:6081/static/vnc.html

### Android Target
- ADB: `adb connect localhost:5555`
- VNC: vnc://localhost:5902
- noVNC: http://localhost:6082

### Windows VM (KubeVirt)
If enabled in values-tilt.yaml:
- RDP: localhost:3389
- VNC: vnc://localhost:5903

## Configuration

### Tilt Configuration

Edit `Tiltfile` to customize:
- Port forwards
- Resource dependencies
- Build settings
- Live update rules

### Helm Values

Edit `infra/helm/values-tilt.yaml` to configure:
- Resource limits
- Replica counts
- Enable/disable services
- Volume mounts

### Kind Configuration

Edit `kind-config-with-registry.yaml` to modify:
- Node configuration
- Port mappings
- KubeVirt settings

## Troubleshooting

### Registry Connection Issues

```bash
# Check registry is running
docker ps | grep kind-registry

# Test registry
curl http://localhost:5001/v2/_catalog

# Restart registry
docker restart kind-registry
```

### Tilt Issues

```bash
# View Tilt logs
tilt logs

# Force rebuild
tilt trigger <resource-name>

# Restart Tilt
tilt down && tilt up
```

### Pod Issues

```bash
# Describe pod for errors
kubectl describe pod -n legacy-use <pod-name>

# View events
kubectl get events -n legacy-use --sort-by='.lastTimestamp'

# Force restart
kubectl rollout restart -n legacy-use deployment/<deployment-name>
```

### Clean Up

```bash
# Stop Tilt and clean resources (preserves cluster)
./scripts/tilt-down.sh

# Completely remove cluster and registry
./scripts/kind-teardown.sh
docker stop kind-registry && docker rm kind-registry
```

## Advanced Usage

### Scaling Targets

```bash
# Scale via kubectl
kubectl scale -n legacy-use deployment/legacy-use-wine-target --replicas=3

# Or update values-tilt.yaml and Tilt will apply changes
```

### Using Windows VMs with KubeVirt

1. Enable in `infra/helm/values-tilt.yaml`:
   ```yaml
   windowsKubevirt:
     enabled: true
     replicas: 2
   ```

2. Wait for VMs to start:
   ```bash
   kubectl get vmirs -n legacy-use
   kubectl get vmi -n legacy-use
   ```

3. Access VM console:
   ```bash
   virtctl console -n legacy-use <vmi-name>
   ```

### Custom Images

1. Build and push to local registry:
   ```bash
   docker build -t localhost:5001/my-image:latest .
   docker push localhost:5001/my-image:latest
   ```

2. Use in Kubernetes:
   ```yaml
   image: localhost:5001/my-image:latest
   ```

## Performance Tips

1. **Limit running targets**: Disable unused targets in values-tilt.yaml
2. **Reduce resource requests**: Lower CPU/memory for development
3. **Use ephemeral storage**: Disable persistence for faster startup
4. **Prune regularly**: `docker system prune -a` to free space

## Integration with IDEs

### VS Code
- Install Kubernetes extension
- Install Tilt extension
- Use port forwarding from IDE

### IntelliJ IDEA
- Configure Kubernetes plugin
- Set up remote debugging on port 5005

## CI/CD Integration

The same Helm charts work in production:

```bash
# Production deployment
helm install legacy-use ./infra/helm \
  -f values-production.yaml \
  -n production \
  --create-namespace
```

## Related Documentation

- [Kind + KubeVirt Setup](./kind-kubevirt.md)
- [Helm Chart README](../infra/helm/README.md)
- [Main README](../README.md)