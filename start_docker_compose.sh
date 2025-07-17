#!/bin/bash

set -e

# Default to debug mode for development
# Use --production or -p flag for production mode
if [[ "$1" == "--production" ]] || [[ "$1" == "-p" ]]; then
    export LEGACY_USE_DEBUG=0
else
    export LEGACY_USE_DEBUG=${LEGACY_USE_DEBUG:-1}
fi


echo "Starting legacy-use with Docker Compose..."
echo "🔄 Container pool enabled - sessions will use existing containers"

# Check if .env.local exists, else create empty file
if [ ! -f .env.local ]; then
    touch .env.local
fi

# Generate API key if needed
uv run python generate_api_key.py

# Check for required images
required_images=(
    "legacy-use-mgmt:local"
    "legacy-use-demo-db:local"
    "legacy-use-wine-target:local"
    "legacy-use-mcp-server:local"
)

missing_images=()
for image in "${required_images[@]}"; do
    if ! docker image inspect "$image" > /dev/null 2>&1; then
        missing_images+=("$image")
    fi
done

if [ ${#missing_images[@]} -gt 0 ]; then
    echo "❌ Missing required Docker images:"
    for image in "${missing_images[@]}"; do
        echo "   - $image"
    done
    echo ""
    echo "Please run: ./build_all_docker.sh"
    exit 1
fi

# Start services
if [ "$LEGACY_USE_DEBUG" = "1" ]; then
    echo "🔧 Starting in DEBUG mode with hot reloading..."
    docker compose up --remove-orphans
else
    echo "🚀 Starting in PRODUCTION mode..."
    docker compose up -d --remove-orphans
fi

echo ""
echo "✅ Services started successfully!"
echo ""
echo "🌐 Access points:"
echo "   - Frontend: http://localhost:8088"
echo "   - API Docs: http://localhost:8088/redoc"
echo "   - Wine VNC: http://localhost:6080/vnc.html (password: wine)"
echo "   - MCP Server: http://localhost:3000/mcp"
echo ""
echo "🎯 Additional services:"
echo "   - Linux machine: http://localhost:6081/static/vnc.html"
echo "   - Windows VM: uncomment windows-target in docker-compose.yml"
echo ""
echo "📝 To stop services:"
echo "   docker compose down"
echo ""
echo "📊 To view logs:"
echo "   docker compose logs -f [service-name]"

echo ""
echo "🔄 Container Pool API endpoints:"
echo "   - View pool status: curl -H \"X-API-Key: \$LEGACY_USE_API_KEY\" http://localhost:8088/containers/status"
echo "   - List containers: curl -H \"X-API-Key: \$LEGACY_USE_API_KEY\" http://localhost:8088/containers"