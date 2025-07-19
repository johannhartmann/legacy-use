# Kubernetes Deployment Guide for Legacy-use

This guide covers deploying Legacy-use on Kubernetes using Kind (Kubernetes in Docker) for local development and Tilt for rapid development cycles.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Architecture Overview](#architecture-overview)
- [Kind Setup](#kind-setup)
- [Tilt Development](#tilt-development)
- [Helm Deployment](#helm-deployment)
- [Troubleshooting](#troubleshooting)
- [Production Considerations](#production-considerations)

## Prerequisites

### Required Tools
- Docker (20.10+)
- kubectl (1.25+)
- Kind (0.20+)
- Tilt (0.33+)
- Helm (3.10+)

### Optional Tools
- k9s (for cluster management)
- kubectx/kubens (for context switching)

### System Requirements
- 16GB RAM minimum (32GB recommended)
- 50GB free disk space
- Linux, macOS, or Windows with WSL2

## Quick Start

```bash
# Clone the repository
git clone https://github.com/your-org/legacy-use.git
cd legacy-use

# Set required environment variables
export ANTHROPIC_API_KEY="your-api-key"

# Start Kind cluster with Tilt
./scripts/kind-setup.sh
./scripts/tilt-up.sh

# Access services
# Management UI: http://localhost:5173
# Backend API: http://localhost:8088
# Tilt UI: http://localhost:10350
```

## Architecture Overview

### Components

1. **Management Service** (`legacy-use-mgmt`)
   - FastAPI backend (port 8088)
   - React frontend (port 5173)
   - Handles API generation and job management

2. **MCP Server** (`legacy-use-mcp-server`)
   - Model Context Protocol server (port 3000)
   - Integrates with Claude Desktop

3. **Target Containers**
   - Wine Target: Windows applications via Wine
   - Linux Target: Ubuntu desktop with GnuCash
   - Android Target: Android emulator

4. **Database**
   - PostgreSQL 15 for persistent storage

### Kubernetes Resources

```
legacy-use/
├── Namespace: legacy-use
├── Deployments:
│   ├── legacy-use-mgmt
│   ├── legacy-use-mcp-server
│   ├── legacy-use-database
│   ├── legacy-use-wine-target
│   ├── legacy-use-linux-target
│   └── legacy-use-android-target
├── Services:
│   ├── legacy-use-mgmt (ClusterIP)
│   ├── legacy-use-mcp-server (ClusterIP)
│   ├── legacy-use-database (ClusterIP)
│   └── *-target services (ClusterIP)
├── PersistentVolumeClaims:
│   └── legacy-use-database-pvc
└── ConfigMaps:
    └── legacy-use-config
```

## Kind Setup

### Creating the Cluster

```bash
# Create Kind cluster with local registry
./scripts/kind-setup.sh
```

This script:
- Creates a Kind cluster named `legacy-use`
- Sets up a local Docker registry at `localhost:5000`
- Configures proper port mappings
- Installs KubeVirt (optional, for Windows VMs)

### Manual Kind Configuration

```yaml
# kind-config.yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: legacy-use
nodes:
- role: control-plane
  extraPortMappings:
  # Management ports
  - containerPort: 30088
    hostPort: 8088
    protocol: TCP
  - containerPort: 30173
    hostPort: 5173
    protocol: TCP
  # MCP Server
  - containerPort: 30300
    hostPort: 3000
    protocol: TCP
  # Database
  - containerPort: 30432
    hostPort: 5432
    protocol: TCP
  # VNC ports for targets
  - containerPort: 30900
    hostPort: 5900
    protocol: TCP
  - containerPort: 30901
    hostPort: 5901
    protocol: TCP
  - containerPort: 30902
    hostPort: 5902
    protocol: TCP
  # noVNC web interfaces
  - containerPort: 30080
    hostPort: 6080
    protocol: TCP
  - containerPort: 30081
    hostPort: 6081
    protocol: TCP
  - containerPort: 30082
    hostPort: 6082
    protocol: TCP
  # Android ADB
  - containerPort: 30555
    hostPort: 5555
    protocol: TCP
containerdConfigPatches:
- |-
  [plugins."io.containerd.grpc.v1.cri".registry]
    [plugins."io.containerd.grpc.v1.cri".registry.mirrors]
      [plugins."io.containerd.grpc.v1.cri".registry.mirrors."localhost:5000"]
        endpoint = ["http://kind-registry:5000"]
```

### Local Registry Setup

```bash
# Create local registry
docker run -d --restart=always -p 5000:5000 --name kind-registry registry:2

# Connect registry to Kind network
docker network connect kind kind-registry
```

## Tilt Development

### Starting Tilt

```bash
# Start Tilt with automatic setup
./scripts/tilt-up.sh

# Or manually
tilt up
```

### Tiltfile Configuration

The `Tiltfile` defines:
- Docker image builds with local registry
- Kubernetes resource management
- Port forwarding configuration
- Resource dependencies
- Development tools

### Key Features

1. **Hot Reload** (currently disabled for stability)
   - Frontend changes trigger rebuilds
   - Backend changes trigger pod restarts

2. **Resource Groups**
   - `core`: Management and MCP services
   - `targets`: VNC target containers
   - `tools`: Development utilities

3. **Dependencies**
   - Database starts first
   - Management waits for database
   - MCP waits for management

### Tilt Commands

```bash
# View logs for a service
tilt logs legacy-use-mgmt

# Trigger manual resource update
tilt trigger legacy-use-mgmt

# Run database migrations
tilt trigger db-migrations

# Generate API key
tilt trigger generate-api-key
```

## Helm Deployment

### Chart Structure

```
infra/helm/
├── Chart.yaml
├── values.yaml
├── values-tilt.yaml      # Tilt development values
├── values-production.yaml # Production values
└── templates/
    ├── configmap.yaml
    ├── legacy-use-mgmt-deployment.yaml
    ├── legacy-use-mgmt-service.yaml
    ├── mcp-server-deployment.yaml
    ├── mcp-server-service.yaml
    ├── *-target-deployment.yaml
    └── *-target-service.yaml
```

### Values Configuration

```yaml
# values-tilt.yaml
management:
  env:
    LEGACY_USE_DEBUG: "0"  # Disable reload in Kind
    ANTHROPIC_API_KEY: ""  # Set via --set flag
  
  # Disabled for Kind - host paths don't exist
  extraVolumes: []
  extraVolumeMounts: []
  
  resources:
    limits:
      cpu: 500m
      memory: 512Mi
    requests:
      cpu: 100m
      memory: 256Mi

database:
  enabled: true
  persistence:
    enabled: true
    size: 5Gi
```

### Manual Helm Deployment

```bash
# Install with Helm
helm install legacy-use ./infra/helm \
  --namespace legacy-use \
  --create-namespace \
  --values infra/helm/values-tilt.yaml \
  --set management.env.ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY

# Upgrade deployment
helm upgrade legacy-use ./infra/helm \
  --namespace legacy-use \
  --values infra/helm/values-tilt.yaml

# Uninstall
helm uninstall legacy-use -n legacy-use
```

## Troubleshooting

### Common Issues

1. **Container Restart Loops**
   ```bash
   # Check pod status
   kubectl get pods -n legacy-use
   
   # View pod events
   kubectl describe pod -n legacy-use <pod-name>
   
   # Check logs
   kubectl logs -n legacy-use <pod-name> --previous
   ```

2. **Health Check Failures**
   - Ensure `/health` endpoint is whitelisted in auth middleware
   - Check if services are actually starting
   - Verify database connectivity

3. **Migration Errors**
   ```bash
   # Run migrations manually
   kubectl exec -n legacy-use deployment/legacy-use-mgmt -- \
     uv run alembic -c server/alembic.ini upgrade head
   
   # Check migration status
   kubectl exec -n legacy-use deployment/legacy-use-mgmt -- \
     uv run alembic -c server/alembic.ini current
   ```

4. **Port Forwarding Issues**
   ```bash
   # Manual port forwarding
   kubectl port-forward -n legacy-use svc/legacy-use-mgmt 8088:8088
   ```

### Debug Commands

```bash
# Get all resources
kubectl get all -n legacy-use

# Check resource consumption
kubectl top pods -n legacy-use

# View recent events
kubectl get events -n legacy-use --sort-by='.lastTimestamp'

# Interactive shell
kubectl exec -it -n legacy-use deployment/legacy-use-mgmt -- bash

# Check service endpoints
kubectl get endpoints -n legacy-use
```

### Known Issues

1. **Hot Reload in Kind**
   - Disabled due to Uvicorn reload issues in containerized environment
   - Use `LEGACY_USE_DEBUG=0` for stable operation

2. **Volume Mounts**
   - Host path volumes don't work in Kind
   - Use ConfigMaps or build into images

3. **Resource Limits**
   - Android emulator requires significant resources
   - Adjust limits based on available hardware

## Production Considerations

### Security

1. **Secrets Management**
   ```bash
   # Create secrets
   kubectl create secret generic legacy-use-secrets \
     --from-literal=anthropic-api-key=$ANTHROPIC_API_KEY \
     -n legacy-use
   ```

2. **Network Policies**
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: legacy-use-mgmt
   spec:
     podSelector:
       matchLabels:
         app.kubernetes.io/name: legacy-use-mgmt
     policyTypes:
     - Ingress
     - Egress
     ingress:
     - from:
       - podSelector:
           matchLabels:
             app.kubernetes.io/name: legacy-use-mcp-server
       ports:
       - port: 8088
   ```

3. **RBAC**
   - Limit service account permissions
   - Use least privilege principle

### Scaling

1. **Horizontal Pod Autoscaling**
   ```yaml
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: legacy-use-mgmt
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: legacy-use-mgmt
     minReplicas: 2
     maxReplicas: 10
     metrics:
     - type: Resource
       resource:
         name: cpu
         target:
           type: Utilization
           averageUtilization: 70
   ```

2. **Resource Optimization**
   - Use init containers for one-time setup
   - Implement proper health checks
   - Configure resource requests/limits

### Monitoring

1. **Prometheus Metrics**
   ```yaml
   # Add to deployment
   annotations:
     prometheus.io/scrape: "true"
     prometheus.io/port: "8088"
     prometheus.io/path: "/metrics"
   ```

2. **Logging**
   - Use structured logging
   - Configure log aggregation
   - Set appropriate log levels

### Backup and Recovery

1. **Database Backups**
   ```bash
   # Backup database
   kubectl exec -n legacy-use deployment/legacy-use-database -- \
     pg_dump -U postgres legacy_use > backup.sql
   
   # Restore database
   kubectl exec -i -n legacy-use deployment/legacy-use-database -- \
     psql -U postgres legacy_use < backup.sql
   ```

2. **Persistent Volume Snapshots**
   - Use volume snapshot classes
   - Regular backup schedules

## Additional Resources

- [Kind Documentation](https://kind.sigs.k8s.io/)
- [Tilt Documentation](https://docs.tilt.dev/)
- [Helm Documentation](https://helm.sh/docs/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

## Contributing

When contributing to the Kubernetes deployment:

1. Test changes with Kind locally
2. Update Helm charts and values
3. Document any new environment variables
4. Add troubleshooting steps for new features
5. Update this documentation

## License

See the main project LICENSE file.