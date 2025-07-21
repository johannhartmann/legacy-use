#!/bin/bash
set -e

echo "Running migrations"
uv run alembic -c server/alembic.ini upgrade head

echo "Starting FastAPI server"
FASTAPI_SERVER_PORT=8088

# Check if debug mode is enabled
if [ "${LEGACY_USE_DEBUG:-0}" = "1" ]; then
    echo "Debug mode enabled: Using hot reload"
    # Debug mode with reload enabled
    UVICORN_CMD="uv run uvicorn server.server:app --host 0.0.0.0 --port $FASTAPI_SERVER_PORT --reload --reload-dir $(pwd)/server"
else
    echo "Production mode: Using workers without reload"
    # Production mode with workers
    UVICORN_CMD="uv run gunicorn -w 1 -k uvicorn.workers.UvicornH11Worker server.server:app --threads 4 --bind 0.0.0.0:$FASTAPI_SERVER_PORT"
fi

LOG_FILE="/tmp/fastapi_stdout.log"
touch $LOG_FILE

# Function to stop uvicorn
stop_uvicorn() {
    if [ ! -z "$UVICORN_PID" ]; then
        echo "Stopping Uvicorn process group $UVICORN_PID..."
        pkill -P $UVICORN_PID || true
        kill -9 $UVICORN_PID 2>/dev/null || true
        wait $UVICORN_PID 2>/dev/null || true
    fi
}

# Function to start uvicorn
start_uvicorn() {
    $UVICORN_CMD > "$LOG_FILE" 2>&1 &
    UVICORN_PID=$!
    echo "Started new Uvicorn instance with PID $UVICORN_PID"
}

# Start initial Uvicorn instance
start_uvicorn

echo "Starting React app"
# Set the path to include node_modules/.bin
export PATH="$HOME/node_modules/.bin:$PATH"

# Pass API_KEY to frontend as VITE_API_KEY if not already set
if [ -n "$API_KEY" ] && [ -z "$VITE_API_KEY" ]; then
    export VITE_API_KEY="$API_KEY"
    echo "Setting VITE_API_KEY from API_KEY environment variable"
fi

# Check if debug mode is enabled
if [ "${LEGACY_USE_DEBUG:-0}" = "1" ]; then
    echo "Installing node dependencies"
    npm install
fi
npm start | cat &

echo "✨ legacy-use is ready!"
echo "➡️  Open http://localhost:5173 in your browser to begin"

# Keep the container running
tail -f /tmp/fastapi_stdout.log
