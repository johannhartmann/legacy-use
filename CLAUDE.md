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
# Start all services with hot reloading
LEGACY_USE_DEBUG=1 ./start_docker_compose.sh

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

### Code Quality Commands
```bash
# Frontend linting and formatting
npm run check     # Check for issues
npm run lint      # Lint with auto-fix
npm run format    # Format code

# Backend formatting
uv run ruff format .
uv run ruff check . --fix
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
- `helm/` - Kubernetes deployment charts
- `sample_prompts/` - Example automation prompts

### Key Services
- **Management UI**: http://localhost:5173 (frontend)
- **Backend API**: http://localhost:8088 (requires API key)
- **Wine Target**: VNC on port 5900, noVNC on http://localhost:6080 (Windows apps via Wine, password: wine)
- **Linux Target**: VNC on port 5901, noVNC on http://localhost:6081 (Linux desktop with GnuCash, password: password123)
- **Android Target**: ADB on port 5555, VNC on port 5902, noVNC on http://localhost:6082 (Android emulator)
- **Demo Database**: PostgreSQL on port 5432
- **MCP Server**: Model Context Protocol server for Claude Desktop integration (see `mcp-server/`)

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
- Production: PostgreSQL via Docker Compose
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