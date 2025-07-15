# Docker Compose Setup

This guide covers the Docker Compose setup for legacy-use, which provides a more integrated approach to running all services together.

## Overview

The Docker Compose setup includes:
- **legacy-use-mgmt** - Main application (backend + frontend)
- **demo-db** - PostgreSQL database with sample data
- **wine-target** - Wine container for Windows application support
- **windows-target** - Full Windows VM (optional, requires KVM)

## Quick Start

### 1. Build Images
```bash
./build_all_docker.sh
```

### 2. Start Services
```bash
# Development mode (with hot reloading)
LEGACY_USE_DEBUG=1 ./start_docker_compose.sh

# Production mode
./start_docker_compose.sh
```

### 3. Access Applications
- **Frontend**: http://localhost:8088
- **API Documentation**: http://localhost:8088/redoc
- **Wine VNC**: http://localhost:6080/vnc.html (password: wine)

## Service Configuration

### Main Application (legacy-use-mgmt)
- **Ports**: 8088 (backend), 5173 (frontend dev server)
- **Environment**: Configured via `.env` and `.env.local`
- **Development**: Source code mounted for hot reloading when `LEGACY_USE_DEBUG=1`

### Wine Target
- **Ports**: 5900 (VNC), 6080 (noVNC web interface)
- **Access**: Web browser or VNC client
- **Password**: `wine`
- **Storage**: Persistent Wine data and applications

### Windows Target (Optional)
- **Ports**: 8006 (web viewer), 3389 (RDP)
- **Requirements**: KVM support (`/dev/kvm` device)
- **Storage**: Persistent Windows disk image

## Environment Variables

Create `.env` file with:
```bash
# Required
ANTHROPIC_API_KEY=your-api-key-here
API_KEY=your-generated-api-key
VITE_API_KEY=your-generated-api-key

# Optional
LEGACY_USE_DEBUG=0
SQLITE_PATH=./server.db
```

## Common Commands

### Start Services
```bash
# Development mode
LEGACY_USE_DEBUG=1 ./start_docker_compose.sh

# Production mode
./start_docker_compose.sh

# Start specific service
docker-compose up wine-target
```

### Stop Services
```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f wine-target
```

### Restart Services
```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart wine-target
```

## Wine Container Usage

### Install Windows Applications
```bash
# Copy installer to container
docker cp myapp.exe legacy-use-wine-target:/home/wineuser/apps/

# Install via VNC
# 1. Open http://localhost:6080/vnc.html
# 2. Open terminal in Wine desktop
# 3. Run: wine /home/wineuser/apps/myapp.exe
```

### Create Wine Target in Legacy-Use
```json
{
  "name": "Wine Applications",
  "type": "vnc",
  "host": "wine-target",
  "port": 5900,
  "password": "wine"
}
```

## Windows VM Usage (Optional)

### Enable Windows Target
Uncomment the `windows-target` service in `docker-compose.yml`.

### Requirements
- KVM support (`/dev/kvm` device)
- Sufficient resources (8GB RAM, 64GB disk)

### Access
- **Web Viewer**: http://localhost:8006
- **RDP**: Connect to `localhost:3389`

## Development Mode

Enable development mode for hot reloading:

```bash
LEGACY_USE_DEBUG=1 ./start_docker_compose.sh
```

This mounts source code directories and enables automatic reloading when files change.

## Production Mode

For production deployment:

```bash
# Start in background
./start_docker_compose.sh

# Or manually
docker-compose up -d
```

## Troubleshooting

### Service Won't Start
```bash
# Check logs
docker-compose logs [service-name]

# Check service status
docker-compose ps
```

### Wine Container Issues
```bash
# Restart Wine container
docker-compose restart wine-target

# Check VNC is working
docker exec -it legacy-use-wine-target ps aux | grep vnc
```

### Port Conflicts
If ports are in use, modify `docker-compose.yml`:
```yaml
ports:
  - "8089:8088"  # Change external port
```

### Volume Permissions
```bash
# Fix Wine volume permissions
docker-compose exec wine-target chown -R wineuser:wineuser /home/wineuser/.wine
```

## Comparison with Individual Docker Run

| Feature | Docker Compose | Individual Run |
|---------|----------------|----------------|
| Multi-service | ✅ Easy | ❌ Complex |
| Service Discovery | ✅ Built-in | ❌ Manual |
| Volume Management | ✅ Automatic | ❌ Manual |
| Environment | ✅ Centralized | ❌ Scattered |
| Development | ✅ Hot reload | ⚠️ Manual |

## Next Steps

1. **Set up targets** - Create VNC targets for Wine applications
2. **Install apps** - Use example scripts in `infra/docker/legacy-use-wine-target/examples/`
3. **Create APIs** - Use legacy-use to turn Windows apps into REST APIs
4. **Deploy** - Use Kubernetes Helm charts for production