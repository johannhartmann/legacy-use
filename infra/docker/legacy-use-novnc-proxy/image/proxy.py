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
import ssl
import base64
from aiohttp import web
from kubernetes import client, config
from kubernetes.stream import stream
import websockets

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
        
        # Initialize Kubernetes client
        try:
            # Try in-cluster config first
            config.load_incluster_config()
            self.k8s_client = client.ApiClient()
            self.k8s_custom = client.CustomObjectsApi(self.k8s_client)
            logger.info("Kubernetes client initialized with in-cluster config")
        except:
            try:
                # Fall back to kubeconfig
                config.load_kube_config()
                self.k8s_client = client.ApiClient()
                self.k8s_custom = client.CustomObjectsApi(self.k8s_client)
                logger.info("Kubernetes client initialized with kubeconfig")
            except Exception as e:
                logger.warning(f"Failed to initialize Kubernetes client: {e}")
                self.k8s_client = None
                self.k8s_custom = None
        
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
        
        # Check if target is a KubeVirt VM (indicated by special header or naming pattern)
        vmi_name = request.headers.get('X-VMI-Name')
        if vmi_name or 'virtvnc' in target_host:
            # Handle KubeVirt VM VNC connection
            return await self.handle_kubevirt_vnc(request, session_id, vmi_name or target_host)
            
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

    async def handle_kubevirt_vnc(self, request, session_id, vmi_identifier):
        """Handle VNC connection to a KubeVirt VM using the VNC subresource API."""
        if not self.k8s_custom:
            logger.error("Kubernetes client not initialized")
            return web.Response(status=500, text='Kubernetes client not available')
        
        # Extract VMI name and namespace
        # vmi_identifier could be just the name or a full service hostname
        if 'virtvnc' in vmi_identifier:
            # This is our virtvnc service, extract the actual VMI name from a different header
            vmi_name = request.headers.get('X-Target-Port', '')  # We stored VMI name in port field
            namespace = 'legacy-use'
        else:
            vmi_name = vmi_identifier
            namespace = request.headers.get('X-Namespace', 'legacy-use')
        
        logger.info(f"Connecting to KubeVirt VMI: {vmi_name} in namespace: {namespace}")
        
        # Prepare WebSocket response
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        try:
            # Create WebSocket URL for KubeVirt VNC subresource
            # Using the Kubernetes API server's websocket endpoint
            api_server = self.k8s_client.configuration.host
            
            # Build the VNC subresource URL
            vnc_url = f"{api_server}/apis/subresources.kubevirt.io/v1/namespaces/{namespace}/virtualmachineinstances/{vmi_name}/vnc"
            
            # Convert http(s) to ws(s)
            vnc_url = vnc_url.replace('https://', 'wss://').replace('http://', 'ws://')
            
            logger.info(f"Connecting to KubeVirt VNC URL: {vnc_url}")
            
            # Log Kubernetes client configuration for debugging
            logger.info(f"K8s client host: {self.k8s_client.configuration.host}")
            logger.info(f"K8s client verify_ssl: {self.k8s_client.configuration.verify_ssl}")
            logger.info(f"K8s client ssl_ca_cert: {self.k8s_client.configuration.ssl_ca_cert}")
            
            # Get auth headers from Kubernetes client
            headers = {}
            if hasattr(self.k8s_client.configuration, 'api_key') and self.k8s_client.configuration.api_key:
                if isinstance(self.k8s_client.configuration.api_key, dict):
                    for key, value in self.k8s_client.configuration.api_key.items():
                        headers[key] = value
                        
            # For in-cluster config, we typically use a bearer token
            if hasattr(self.k8s_client.configuration, 'api_key_prefix') and self.k8s_client.configuration.api_key_prefix:
                if 'authorization' in self.k8s_client.configuration.api_key_prefix:
                    auth_prefix = self.k8s_client.configuration.api_key_prefix['authorization']
                    if hasattr(self.k8s_client.configuration, 'api_key') and \
                       isinstance(self.k8s_client.configuration.api_key, dict) and \
                       'authorization' in self.k8s_client.configuration.api_key:
                        auth_token = self.k8s_client.configuration.api_key['authorization']
                        # Use capital Authorization header
                        headers['Authorization'] = f"{auth_prefix} {auth_token}".strip()
                        # Also try lowercase for compatibility
                        headers['authorization'] = f"{auth_prefix} {auth_token}".strip()
            
            # Log headers for debugging (mask the token)
            if headers:
                safe_headers = {}
                for k, v in headers.items():
                    if k.lower() == 'authorization':
                        # Mask the token part
                        parts = v.split(' ', 1)
                        if len(parts) == 2:
                            safe_headers[k] = f"{parts[0]} ***masked***"
                        else:
                            safe_headers[k] = "***masked***"
                    else:
                        safe_headers[k] = v
                logger.info(f"Headers to send: {safe_headers}")
            else:
                logger.warning("No authorization headers found - connection will likely fail")
            
            # Handle SSL verification
            ssl_context = None
            if vnc_url.startswith('wss://'):
                if self.k8s_client.configuration.verify_ssl and self.k8s_client.configuration.ssl_ca_cert:
                    # Use the Kubernetes CA certificate
                    ssl_context = ssl.create_default_context()
                    ssl_context.load_verify_locations(self.k8s_client.configuration.ssl_ca_cert)
                else:
                    # Disable SSL verification
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
            
            # Connect to KubeVirt VNC websocket
            # Note: websockets library uses 'extra_headers' in newer versions, 'subprotocols' in older
            connect_kwargs = {'ssl': ssl_context}
            if headers:
                connect_kwargs['extra_headers'] = headers
            
            # Try to connect with proper headers
            kubevirt_ws = None
            try:
                # Try with extra_headers first (newer websockets versions)
                kubevirt_ws = await websockets.connect(vnc_url, **connect_kwargs)
            except TypeError as e:
                if 'extra_headers' in str(e):
                    # Fall back to older websockets API - try with additional_headers instead
                    logger.warning("Falling back to older websockets API with additional_headers")
                    connect_kwargs.pop('extra_headers', None)
                    if headers:
                        connect_kwargs['additional_headers'] = headers
                    kubevirt_ws = await websockets.connect(vnc_url, **connect_kwargs)
                else:
                    raise
            
            logger.info(f"Connected to KubeVirt VNC for VMI: {vmi_name}")
            
            # Bidirectional proxy between client and KubeVirt
            async def forward_to_kubevirt():
                async for msg in ws:
                    if msg.type == web.WSMsgType.BINARY:
                        await kubevirt_ws.send(msg.data)
                    elif msg.type == web.WSMsgType.TEXT:
                        await kubevirt_ws.send(msg.data)
                    elif msg.type == web.WSMsgType.ERROR:
                        logger.error(f'Client WebSocket error: {ws.exception()}')
                        break
            
            async def forward_from_kubevirt():
                async for msg in kubevirt_ws:
                    if isinstance(msg, bytes):
                        await ws.send_bytes(msg)
                    else:
                        await ws.send_str(msg)
            
            # Run both forwarding tasks
            await asyncio.gather(forward_to_kubevirt(), forward_from_kubevirt())
            
            # Clean up
            await kubevirt_ws.close()
                
        except Exception as e:
            logger.error(f"KubeVirt VNC proxy error: {e}")
            await ws.close()
        
        return ws

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