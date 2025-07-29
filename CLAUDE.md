# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Legacy-use is a platform that turns legacy applications into modern REST APIs using AI. It uses Anthropic's Claude to automate interaction with legacy desktop applications via remote access protocols (VNC, RDP).

## Common Commands

### Build Commands
```bash
# Build all Docker images in parallel
./build_docker.sh

# Build individual services
docker build -t legacy-use-frontend -f infra/docker/legacy-use-frontend/Dockerfile .
docker build -t legacy-use-backend -f infra/docker/legacy-use-backend/Dockerfile .
docker build -t legacy-use-mgmt -f infra/docker/legacy-use-mgmt/Dockerfile .
docker build -t legacy-use-wine-target -f infra/docker/legacy-use-wine-target/Dockerfile .
docker build -t legacy-use-android-target -f infra/docker/legacy-use-android-target/Dockerfile .
docker build -t legacy-use-linux-machine -f infra/docker/linux-machine/Dockerfile .
```

### Development Commands
```bash
# Frontend development (port 5173)
cd app && npm run dev

# Backend development (port 8080)
cd server && uv run uvicorn server.server:app --reload --host 0.0.0.0 --port 8080

# Generate API key
uv run python generate_api_key.py

# Run database migrations
cd server && uv run alembic upgrade head

# MCP Server development
cd mcp-server
pip install -e .
python test_server.py  # Test database connection and API conversion
```

### Kubernetes Development with Kind & Tilt
```bash
# Quick development setup
make dev-setup    # Sets up Kind cluster with KubeVirt
make vm-preload   # Pre-load VM images (prevents re-downloading, optional)
make tilt-up      # Start Tilt (with auto-reload)
make tilt-down    # Stop Tilt (properly cleans up VMs)
make dev-teardown # Tear down everything

# Individual commands
make kind-setup    # Set up Kind cluster with KubeVirt and local registry
make kind-status   # Check Kind cluster and KubeVirt status
make kind-teardown # Tear down Kind cluster and registry

make tilt-up       # Start Tilt
make tilt-down     # Stop Tilt and clean up VMs (preserves Kind cluster)
make tilt-status   # Check Tilt status
make vm-preload    # Pre-load VM container images (prevents re-downloading)

make build         # Build all Docker images
make build-push    # Build and push images to registry

# Or use scripts directly
./scripts/kind-setup.sh
./scripts/preload-vm-images.sh  # Pre-load VM images
./scripts/tilt-up.sh
./scripts/tilt-down.sh
./scripts/kind-teardown.sh
./scripts/check-kubevirt.sh
./scripts/build-and-push.sh
```

### Code Quality Commands
```bash
# Frontend linting and formatting
npm run check     # Check for issues
npm run lint      # Lint with auto-fix
npm run format    # Format code

# Backend quality checks (Python)
make format       # Format code with black and ruff
make lint         # Run all linting checks
make vulture      # Find dead code
make check        # Run all quality checks
make test         # Run tests
make pre-commit   # Install and run pre-commit hooks

# Individual Python tools
uv run black .                    # Format with black
uv run ruff check . --fix         # Lint and fix with ruff
uv run ruff format .              # Format with ruff
uv run vulture server/ --min-confidence=60  # Find dead code
uv run mypy server/               # Type checking
```

### Testing Commands
```bash
# Frontend tests
npm run test

# No backend tests currently exist
```

## Architecture Overview

### Core Concepts
- **Target**: A running machine/application to be automated (VNC/RDP server)
- **Session**: A user session on a target with defined permissions
- **API**: REST API generated from a prompt describing desired capabilities
- **Job**: Execution of an API request turning it into tool calls
- **Tools**: Low-level operations (click, type, screenshot) performed on targets

### Request Flow
1. Client calls generated REST API endpoint
2. Backend creates a job from the request
3. AI agent analyzes request and current screen state
4. Agent executes tools (click, type, etc.) on the target
5. Results are returned via the API

### Directory Structure
- `app/` - React frontend (Material-UI, Vite)
- `server/` - FastAPI backend with AI automation
- `infra/docker/` - Docker configurations for all services
- `infra/helm/` - Kubernetes deployment charts
- `sample_prompts/` - Example automation prompts

### Key Services
- **Management UI**: http://localhost:5173 (frontend)
- **Backend API**: http://localhost:8088 (requires API key)
- **MCP Server**: http://localhost:3000/mcp (Model Context Protocol server for Claude Desktop integration)
- **Wine Target**: VNC on port 5900, noVNC on http://localhost:6080 (Windows apps via Wine, no password)
- **Linux Target**: VNC on port 5901, noVNC on http://localhost:6081/static/vnc.html (Linux desktop with GnuCash, no password)
- **Android Target**: ADB on port 5555, VNC on port 5902, noVNC on http://localhost:6082 (Android emulator)
- **Demo Database**: PostgreSQL on port 5432

## Development Tips

### Environment Setup
Required environment variables:
```bash
ANTHROPIC_API_KEY=your_api_key  # Required for AI functionality
LEGACY_USE_DEBUG=1              # Enable hot reloading
```

### Hot Reloading
- Frontend: Automatic via Vite when using `LEGACY_USE_DEBUG=1`
- Backend: Automatic via Uvicorn when using `LEGACY_USE_DEBUG=1`
- Changes in `app/` and `server/` directories are watched

### Working with Targets
- Wine target provides lightweight Windows app support
- Linux target runs full Ubuntu desktop
- Android target runs Android 11 emulator (Samsung Galaxy S10)
- All targets expose VNC for remote access
- Targets can be added/removed via Management UI

### Database
- Default: SQLite in development
- Production: PostgreSQL via Kubernetes
- Migrations: Alembic in `server/migrations/`

## Common Issues

1. **Port conflicts**: Services use ports 8001, 5555, 5900-5902, 5432, 6080-6082
2. **API key missing**: Set `ANTHROPIC_API_KEY` environment variable
3. **Docker permissions**: May need sudo or docker group membership
4. **Build failures**: Ensure Docker daemon is running

## Security Notes
- API keys are stored in database (generate with `generate_api_key.py`)
- VNC connections are not encrypted by default
- Consider VPN for production deployments
- Telemetry can be disabled via environment variables

## Kubernetes-specific Notes

### Container Pool
The container pool automatically discovers containers with the label `legacy-use.scalable=true`. Each container type is identified by:
- Label `legacy-use.target-type` (values: `wine`, `linux`, `android`)
- Fallback to container name pattern matching if label is missing

### Debugging Container Allocation
Check container pool status:
```bash
curl -H "X-API-Key: $API_KEY" http://localhost:8088/sessions/pool/status
```

Common issues:
- Container not detected: Check if pod has `legacy-use.scalable=true` label
- Container not available: May be already allocated to another session
- Session stuck in "initializing": No available containers of that type

### Important: Let Tilt Manage Kubernetes
- **DO NOT** manually restart pods or deployments with kubectl
- **DO NOT** use kubectl port-forward (Tilt manages port forwarding)
- **DO NOT** scale deployments manually (use Tilt or the app's scaling features)
- Tilt automatically rebuilds and redeploys when you change code

## Personal Memories
- Do not start and stop tilt on your own
- For scaling windows machines we need VirtualMachineInstanceReplicaSet. VirtualMachine is no option.
- DO NOT RESTART ANY KUBERNETES SERVICES WITH KUBECTL
- do not fix the currently running instance, fix tilt/helm and wait for your fix being applied
- do not rebuild and restart on your own but use tilt to do it
- you can monitor  tilt in tilt.log
- test before you commit
- never create files in dockerfiles by hand, always create files and copy them while buiding