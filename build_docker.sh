#!/bin/bash

# Docker build script for legacy-use
# Builds all Docker images with parallel execution

set -e

echo "🚀 Starting parallel Docker builds..."

# Function to build and tag images
build_image() {
    local image_name=$1
    local dockerfile=$2
    local context=${3:-.}
    
    echo "📦 Building $image_name..."
    
    # Build with BuildKit for better caching
    # Only use cache-from if the image exists
    if docker image inspect "$image_name:local" >/dev/null 2>&1; then
        DOCKER_BUILDKIT=1 docker build \
            --tag "$image_name:local" \
            --file "$dockerfile" \
            --cache-from "$image_name:local" \
            "$context"
    else
        DOCKER_BUILDKIT=1 docker build \
            --tag "$image_name:local" \
            --file "$dockerfile" \
            "$context"
    fi
    
    echo "✅ Completed $image_name"
}

# Start parallel builds
echo "🔄 Starting parallel builds..."

# Fast builds (lightweight)
build_image "legacy-use-demo-db" "infra/docker/legacy-use-demo-db/Dockerfile" &
build_image "legacy-use-target" "infra/docker/legacy-use-target/Dockerfile" &

# Medium builds
build_image "legacy-use-frontend" "infra/docker/legacy-use-frontend/Dockerfile" &
build_image "legacy-use-backend" "infra/docker/legacy-use-backend/Dockerfile" &

# Wait for lightweight builds to complete
wait

echo "📱 Lightweight builds completed, starting heavier builds..."

# Heavy builds (after others complete to avoid resource contention)
build_image "legacy-use-mgmt" "infra/docker/legacy-use-mgmt/Dockerfile" &
build_image "linux-machine" "infra/docker/linux-machine/Dockerfile" &

# Wine build (now optimized)
echo "🍷 Starting Wine build..."
build_image "legacy-use-wine-target" "infra/docker/legacy-use-wine-target/Dockerfile" &

# Android build
echo "🤖 Starting Android build..."
build_image "legacy-use-android-target" "infra/docker/legacy-use-android-target/Dockerfile" &

# MCP server build
echo "🔌 Starting MCP server build..."
build_image "legacy-use-mcp-server" "mcp-server/Dockerfile" "mcp-server"

# Wait for remaining builds
wait

echo "🏷️  Creating additional tags..."

# Create additional tags for compatibility
docker tag legacy-use-backend:local legacy-use-core-backend:local
docker tag legacy-use-frontend:local legacy-use-core-frontend:local
docker tag linux-machine:local legacy-use-core-linux-machine:local
docker tag legacy-use-demo-db:local legacy-use-core-demo-db:local

echo "✅ All builds completed successfully!"
echo ""
echo "📊 Built images:"
docker images | grep -E "(legacy-use|linux-machine)" | grep local

echo ""
echo "🚀 Ready to start with:"
echo "  ./start_docker_compose.sh"