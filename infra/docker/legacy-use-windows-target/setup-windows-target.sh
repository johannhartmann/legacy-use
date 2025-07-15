#!/bin/bash

# Setup script for Windows target integration with legacy-use

set -e

echo "Legacy Use Windows Target Setup"
echo "==============================="

# Check for KVM support
if [ ! -e /dev/kvm ]; then
    echo "ERROR: KVM not available. Please enable virtualization in BIOS."
    exit 1
fi

# Parse command line arguments
VERSION=${1:-11}
USERNAME=${2:-LegacyUser}
PASSWORD=${3:-LegacyPass123!}

echo "Configuration:"
echo "  Windows Version: $VERSION"
echo "  Username: $USERNAME"
echo "  Password: ********"

# Create docker-compose override file with custom settings
cat > docker-compose.override.yml <<EOF
version: '3.8'

services:
  windows-target:
    environment:
      - VERSION=$VERSION
      - USERNAME=$USERNAME
      - PASSWORD=$PASSWORD
EOF

echo ""
echo "Starting Windows container..."
docker compose up -d windows-target

echo ""
echo "Windows is being installed. This may take 10-15 minutes."
echo "You can monitor progress at: http://localhost:8006"
echo ""
echo "Once Windows is ready, create a legacy-use target with:"
echo "  Type: rdp"
echo "  Host: localhost (or container name if using Docker network)"
echo "  Port: 3389"
echo "  Username: $USERNAME"
echo "  Password: $PASSWORD"
echo ""
echo "To stop the Windows container:"
echo "  docker compose down"