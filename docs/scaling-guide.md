# Container Pool Management Guide

This guide explains how the container pool feature works to manage sessions across existing containers.

## Overview

Legacy-Use uses a container pool architecture for Kubernetes deployments. Sessions are allocated to existing containers rather than creating new containers for each session. This provides:

- **Better Performance**: No container startup overhead - sessions start instantly
- **Resource Efficiency**: Containers are reused across sessions
- **Consistent Architecture**: Same approach across all deployments
- **Simplified Scaling**: Add more containers to handle more concurrent sessions

## Quick Start

1. **Start Services**:
```bash
./scripts/kind-setup.sh  # One-time setup
./scripts/tilt-up.sh     # Start services
```

2. **Create Sessions**:
Sessions will automatically be allocated to available containers.

3. **Monitor Pool Status**:
```bash
curl -H "X-API-Key: $LEGACY_USE_API_KEY" http://localhost:8088/containers/status
```

## Architecture

### Container Pool Management

When container pool mode is enabled:

1. **Service Discovery**: The system automatically discovers all scaled containers
2. **Container Allocation**: When a session is created, an available container is allocated
3. **Container Release**: When a session ends, the container is released back to the pool
4. **Health Monitoring**: Unhealthy containers are marked and not allocated

### Port Management

Containers are accessed through the following ports:

- Wine VNC: 5900
- Wine noVNC: 6080
- Linux VNC: 5901
- Linux noVNC: 6081
- Android VNC: 5902
- Android noVNC: 6082

## Container Pool API

### List All Containers
```bash
curl -H "X-API-Key: $API_KEY" http://localhost:8088/containers
```

### Get Pool Status
```bash
curl -H "X-API-Key: $API_KEY" http://localhost:8088/containers/status
```

Response:
```json
{
  "total_containers": 7,
  "available": 5,
  "allocated": 2,
  "by_type": {
    "wine": {"total": 3, "available": 2, "allocated": 1},
    "linux": {"total": 2, "available": 2, "allocated": 0},
    "android": {"total": 2, "available": 1, "allocated": 1}
  }
}
```

### List Available Containers by Type
```bash
curl -H "X-API-Key: $API_KEY" http://localhost:8088/containers?target_type=wine&available_only=true
```

## Container Management

### View Running Containers
```bash
kubectl get pods -l app.kubernetes.io/name=legacy-use
```

### Restart a Container
```bash
# Note: Let Tilt handle restarts automatically
# Manual restart if needed:
kubectl delete pod <pod-name>
```

### View Container Logs
```bash
kubectl logs -f -l legacy-use.target-type=wine
```

## Monitoring

### Container Logs
View logs for all Wine targets:
```bash
kubectl logs -f -l legacy-use.target-type=wine
```

View logs for a specific pod:
```bash
kubectl logs -f <pod-name>
```

### Resource Usage
```bash
kubectl top pods -l app.kubernetes.io/name=legacy-use
```

## Best Practices

1. **Monitor Pool Status**: Keep track of container allocation
2. **Health Checks**: Ensure containers are healthy before creating sessions
3. **Session Cleanup**: Always properly delete sessions to release containers
4. **Container Restart**: Restart containers if they become unresponsive

## Troubleshooting

### No Available Containers

If sessions fail with "No available containers":

1. Check pool status: `curl -H "X-API-Key: $API_KEY" http://localhost:8088/containers/status`
2. Check if containers are running: `kubectl get pods -l app.kubernetes.io/name=legacy-use`
3. Check Tilt UI for any issues: http://localhost:10350
4. Check for existing sessions using the container: `curl -H "X-API-Key: $API_KEY" http://localhost:8088/sessions/`

### Port Conflicts

If you see port binding errors:

1. Ensure port ranges don't overlap with other services
2. Check for conflicting services: `kubectl get svc`
3. Tilt handles port forwarding automatically

### Container Not Released

If containers remain allocated after session deletion:

1. Force refresh the pool: `curl -X POST -H "X-API-Key: $API_KEY" http://localhost:8088/containers/refresh`
2. Check session status: `curl -H "X-API-Key: $API_KEY" http://localhost:8088/sessions/`

## Scaling Containers

### Kubernetes

Scaling is built-in with Kubernetes:

```bash
# Scale a specific target type
kubectl scale deployment wine-target --replicas=3

# Or use Tilt's scaling features
# Edit the replica count in Tiltfile and Tilt will handle the update
```

## Configuration

### Container Pool Architecture

The container pool is always active and provides:

- **Automatic Discovery**: Finds all running target containers
- **Session Allocation**: Assigns sessions to available containers
- **Health Monitoring**: Tracks container health status
- **Resource Management**: Releases containers when sessions end

## Performance Considerations

- Containers remain running and use memory even when idle
- Session start time is nearly instant (< 1s) since containers are pre-warmed
- Only one session can use each container at a time
- Container pool mode works best for development and testing environments

## Limitations

- Container pool requires proper labeling of containers
- Each container can only handle one session at a time
- Scaling requires sufficient cluster resources