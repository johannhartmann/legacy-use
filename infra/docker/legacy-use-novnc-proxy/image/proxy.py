#!/usr/bin/env python3
"""
Dynamic VNC WebSocket proxy for legacy-use.
This proxy runs websockify dynamically based on session information.
"""

import asyncio
import logging
import os
import sys
import subprocess
from aiohttp import web

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VNCProxy:
    def __init__(self):
        self.legacy_use_url = os.getenv('LEGACY_USE_URL', 'http://legacy-use-mgmt:8088')
        self.api_key = os.getenv('API_KEY', 'not-secure-api-key')
        self.websockify_processes = {}
        
    async def handle_websocket(self, request):
        """Handle incoming WebSocket connections by proxying directly."""
        # Get target information from headers (passed by nginx)
        session_id = request.headers.get('X-Session-Id')
        target_host = request.headers.get('X-Target-Host')
        target_port = request.headers.get('X-Target-Port', '5900')
        
        logger.info(f"Received headers: session_id={session_id}, target_host={target_host}, target_port={target_port}")
        
        if not all([session_id, target_host]):
            logger.error(f"Missing required parameters: session_id={session_id}, target_host={target_host}")
            return web.Response(status=400, text='Missing required parameters')
            
        # Start websockify as a subprocess that will handle the WebSocket connection
        websockify_port = await self.start_websockify(session_id, target_host, target_port)
        
        if websockify_port:
            # Proxy the WebSocket connection to websockify
            ws = web.WebSocketResponse()
            await ws.prepare(request)
            
            try:
                import websockets
                # Connect to the local websockify instance
                async with websockets.connect(f'ws://localhost:{websockify_port}/') as websockify:
                    # Create tasks for bidirectional proxying
                    async def forward_to_websockify():
                        async for msg in ws:
                            if msg.type == web.WSMsgType.BINARY:
                                await websockify.send(msg.data)
                            elif msg.type == web.WSMsgType.TEXT:
                                await websockify.send(msg.data)
                            elif msg.type == web.WSMsgType.ERROR:
                                logger.error(f'WebSocket error: {ws.exception()}')
                                break
                    
                    async def forward_from_websockify():
                        async for msg in websockify:
                            if isinstance(msg, bytes):
                                await ws.send_bytes(msg)
                            else:
                                await ws.send_str(msg)
                    
                    # Run both tasks concurrently
                    await asyncio.gather(forward_to_websockify(), forward_from_websockify())
                    
            except Exception as e:
                logger.error(f"WebSocket proxy error: {e}")
            finally:
                await ws.close()
            
            return ws
        else:
            return web.Response(status=500, text='Failed to start websockify')
    
    async def start_websockify(self, session_id, target_host, target_port):
        """Start a websockify process for the given target."""
        # Find an available port (in production, use a pool)
        port = 6100 + hash(session_id) % 1000
        
        # If already running for this session, return the port
        if session_id in self.websockify_processes:
            return port
            
        try:
            # Start websockify
            cmd = [
                'websockify',
                '--web', '/usr/share/novnc',
                f'localhost:{port}',
                f'{target_host}:{target_port}'
            ]
            
            logger.info(f"Starting websockify: {' '.join(cmd)}")
            process = subprocess.Popen(cmd)
            
            self.websockify_processes[session_id] = {
                'process': process,
                'port': port
            }
            
            # Give it a moment to start and verify it's listening
            for retry in range(10):  # Try for up to 5 seconds
                await asyncio.sleep(0.5)
                # Check if websockify is listening
                try:
                    test_conn = await asyncio.open_connection('localhost', port)
                    test_conn[1].close()
                    await test_conn[1].wait_closed()
                    logger.info(f"Websockify is ready on port {port}")
                    break
                except Exception:
                    if retry == 9:
                        logger.error(f"Websockify failed to start on port {port} after 5 seconds")
                        return None
                    continue
            
            return port
            
        except Exception as e:
            logger.error(f"Failed to start websockify: {e}")
            return None

    async def health(self, request):
        """Health check endpoint."""
        return web.Response(text="healthy\n")

def create_app():
    """Create the aiohttp application."""
    proxy = VNCProxy()
    app = web.Application()
    
    # Serve static noVNC files
    app.router.add_static('/', path='/usr/share/novnc', name='static')
    
    # WebSocket endpoint
    app.router.add_get('/websockify', proxy.handle_websocket)
    app.router.add_get('/health', proxy.health)
    
    return app

if __name__ == '__main__':
    app = create_app()
    web.run_app(app, host='0.0.0.0', port=6080)