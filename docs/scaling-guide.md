# Container Pool Management Guide

This guide explains how the container pool feature works to manage sessions across existing containers.

## Overview

Legacy-Use uses a container pool architecture for both development (Docker Compose) and production (Kubernetes). Sessions are allocated to existing containers rather than creating new containers for each session. This provides:

- **Better Performance**: No container startup overhead - sessions start instantly
- **Resource Efficiency**: Containers are reused across sessions
- **Consistent Architecture**: Same approach for both development and production
- **Simplified Scaling**: Add more containers to handle more concurrent sessions

## Quick Start

1. **Start Services**:
```bash
./start_docker_compose.sh
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

With the current docker-compose setup, containers use fixed ports:

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
docker-compose ps
```

### Restart a Container
```bash
docker-compose restart wine-target
```

### View Container Logs
```bash
docker-compose logs -f wine-target
```

## Monitoring

### Container Logs
View logs for all Wine targets:
```bash
docker-compose logs -f wine-target
```

View logs for a specific instance:
```bash
docker logs -f legacy-use_wine-target_3
```

### Resource Usage
```bash
docker stats $(docker-compose ps -q wine-target)
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
2. Check if containers are running: `docker-compose ps`
3. Restart containers if needed: `docker-compose restart`
4. Check for existing sessions using the container: `curl -H "X-API-Key: $API_KEY" http://localhost:8088/sessions/`

### Port Conflicts

If you see port binding errors:

1. Ensure port ranges don't overlap with other services
2. Check for stale containers: `docker ps -a`
3. Clean up if needed: `docker-compose down`

### Container Not Released

If containers remain allocated after session deletion:

1. Force refresh the pool: `curl -X POST -H "X-API-Key: $API_KEY" http://localhost:8088/containers/refresh`
2. Check session status: `curl -H "X-API-Key: $API_KEY" http://localhost:8088/sessions/`

## Scaling Containers

### Docker Compose (Development)

With the current setup, you have one container per target type. To add more containers, you would need to:

1. Modify `docker-compose.yml` to remove fixed container names
2. Use port ranges instead of fixed ports
3. Run with `--scale` flag: `docker-compose up -d --scale wine-target=3`

### Kubernetes (Production)

In Kubernetes, scaling is built-in:

```bash
kubectl scale deployment wine-target --replicas=3
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

With the current docker-compose setup:
- Only one instance of each target type (Wine, Linux, Android) can run
- To support multiple instances, you would need to modify docker-compose.yml to remove fixed container names and use port ranges