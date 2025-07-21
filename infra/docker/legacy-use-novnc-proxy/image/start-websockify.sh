#!/bin/bash
# Script to start websockify with dynamic target based on URL parameters
# This will be called by nginx when a WebSocket connection is requested

SESSION_ID=$1
TARGET_HOST=$2
TARGET_PORT=${3:-5900}

if [ -z "$SESSION_ID" ] || [ -z "$TARGET_HOST" ]; then
    echo "Usage: $0 <session_id> <target_host> [target_port]"
    exit 1
fi

echo "Starting websockify for session $SESSION_ID to $TARGET_HOST:$TARGET_PORT"

# Start websockify
exec websockify --web /usr/share/novnc 6080 ${TARGET_HOST}:${TARGET_PORT}