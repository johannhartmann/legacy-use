#!/bin/bash
set -e

echo "Starting noVNC proxy service..."

# Start supervisord
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf