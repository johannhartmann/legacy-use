"""
VNC proxy routes.

This module handles VNC viewer proxy requests, keeping them separate from the main API routes.
"""

import asyncio
import logging
import os
from typing import Any, Dict
from uuid import UUID

import requests
import websockets
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.background import BackgroundTasks
from fastapi.responses import StreamingResponse

from server.database import db

logger = logging.getLogger(__name__)

vnc_router = APIRouter(prefix='/vnc', tags=['VNC Proxy'])


@vnc_router.get('/{session_id}/{path:path}', include_in_schema=False)
async def proxy_vnc(session_id: UUID, path: str, request: Request):
    """
    Proxy VNC viewer requests to the shared noVNC proxy service.

    This endpoint forwards VNC viewer requests to the shared noVNC proxy which handles all VNC connections.
    """
    # Get session
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')

    # Check if container is running
    if not session.get('container_id') or not session.get('container_ip'):
        raise HTTPException(status_code=400, detail='Session has no active container')

    # Get container IP and VNC port
    container_ip = session.get('container_ip')
    vnc_port = session.get('vnc_port', '5900')  # Default VNC port
    
    # For Kubernetes deployments, translate pod IPs to service names
    target_host = container_ip
    if container_ip and container_ip.startswith('10.244.'):  # Pod IP range
        # Get target type from session
        target = db.get_target(session.get('target_id'))
        if target:
            target_type = target.get('type')
            # Map to service names
            service_mapping = {
                'linux': 'legacy-use-linux-target',
                'wine': 'legacy-use-wine-target', 
                'android': 'legacy-use-android-target',
                'dosbox': 'legacy-use-dosbox-target',
                'android-aind': 'legacy-use-android-aind-target'
            }
            if target_type in service_mapping:
                target_host = service_mapping[target_type]
    
    # Use shared noVNC proxy
    novnc_proxy_url = os.getenv('NOVNC_PROXY_URL', 'http://novnc-proxy')
    
    # Get query parameters from the request
    params = dict(request.query_params)
    
    # For websockify connections, we need to pass target info
    if path == 'websockify':
        # Add target information as query parameters
        params['session_id'] = str(session_id)
        params['target_host'] = target_host
        params['target_port'] = vnc_port
    
    # Build target URL
    target_url = f'{novnc_proxy_url}/{path}'

    # Get headers from the request, excluding host
    headers = dict(request.headers)
    headers.pop('host', None)

    try:
        # Get the method from the request
        method = request.method

        # Get the request body if it exists
        body = await request.body() if method in ['POST', 'PUT', 'PATCH'] else None

        # Make the request to the container
        client_response = requests.request(
            method=method,
            url=target_url,
            params=params,
            headers=headers,
            data=body,
            stream=True,
            timeout=60,
        )

        # Create a function to close the response when done
        def close_response():
            client_response.close()

        # Filter out problematic headers that can cause decoding issues
        response_headers = dict(client_response.headers)
        headers_to_remove = ['content-encoding', 'content-length', 'transfer-encoding']
        for header in headers_to_remove:
            response_headers.pop(header, None)
            response_headers.pop(header.title(), None)

        # Return a streaming response with background task
        background_tasks = BackgroundTasks()
        background_tasks.add_task(close_response)
        
        return StreamingResponse(
            content=client_response.iter_content(chunk_size=8192),
            status_code=client_response.status_code,
            headers=response_headers,
            background=background_tasks,
        )
    except requests.RequestException as e:
        logger.error(f'Error proxying VNC request: {str(e)}')
        raise HTTPException(
            status_code=502, detail=f'Error proxying VNC request: {str(e)}'
        ) from e


@vnc_router.websocket('/{session_id}/websockify')
async def proxy_vnc_websocket(websocket: WebSocket, session_id: UUID):
    """
    Proxy WebSocket connections for the VNC viewer.

    This endpoint forwards WebSocket connections to the container's VNC server via the noVNC proxy.
    """
    logger.info(f'[VNC-WS] New WebSocket connection for session {session_id}')
    
    # Get session
    session = db.get_session(session_id)
    if not session:
        logger.warning(f'[VNC-WS] Session {session_id} not found')
        await websocket.close(code=1008, reason='Session not found')
        return

    # Check if session is in ready state
    if session.get('state') != 'ready':
        logger.warning(
            f'[VNC-WS] Session {session_id} not ready (state: {session.get("state")})'
        )
        await websocket.close(
            code=1008,
            reason=f'Session is not ready (current state: {session.get("state")})',
        )
        return

    # Get container details
    container_ip = session.get('container_ip')
    vnc_port = session.get('vnc_port', '5900')  # Default VNC port
    container_id = session.get('container_id')
    
    # For Kubernetes deployments, translate pod IPs to service names
    # This handles existing sessions that have pod IPs stored
    target_host = container_ip
    if container_ip and container_ip.startswith('10.244.'):  # Pod IP range
        # Get target type from session
        target = db.get_target(session.get('target_id'))
        if target:
            target_type = target.get('type')
            # Map to service names
            service_mapping = {
                'linux': 'legacy-use-linux-target',
                'wine': 'legacy-use-wine-target', 
                'android': 'legacy-use-android-target',
                'dosbox': 'legacy-use-dosbox-target',
                'android-aind': 'legacy-use-android-aind-target'
            }
            if target_type in service_mapping:
                target_host = service_mapping[target_type]
                logger.info(f'[VNC-WS] Translated pod IP {container_ip} to service {target_host} for {target_type} target')
    
    logger.info(f'[VNC-WS] Session details: target_host={target_host}, vnc_port={vnc_port}, container_id={container_id}')
    
    # Connect to shared noVNC proxy WebSocket with target information in headers
    novnc_proxy_host = os.getenv('NOVNC_PROXY_HOST', 'novnc-proxy')
    novnc_proxy_port = os.getenv('NOVNC_PROXY_PORT', '80')
    
    # Build WebSocket URL to shared proxy
    novnc_ws_url = f'ws://{novnc_proxy_host}:{novnc_proxy_port}/websockify'
    
    # Headers for the noVNC proxy to know which target to connect to
    proxy_headers = {
        'X-Target-Host': target_host,
        'X-Target-Port': str(vnc_port),
        'X-Session-Id': str(session_id),
    }
    
    # Accept the WebSocket connection with the same subprotocol if provided
    subprotocol = None
    if websocket.headers.get('sec-websocket-protocol'):
        # noVNC typically uses 'binary' or 'base64' subprotocol
        requested_protocols = websocket.headers.get('sec-websocket-protocol').split(',')
        # We'll accept the first protocol requested (usually 'binary')
        subprotocol = requested_protocols[0].strip()
        logger.info(f'[VNC-WS] Accepting WebSocket with subprotocol: {subprotocol}')
    
    await websocket.accept(subprotocol=subprotocol)
    
    logger.info(f'[VNC-WS] Connecting to shared noVNC proxy: {novnc_ws_url}')

    try:
        # Connect to the shared noVNC proxy with target information in headers
        headers = proxy_headers
        
        # If this is a KubeVirt VM, pass the VMI name
        if container_ip == 'kubevirt-vm':
            headers['X-VMI-Name'] = container_id
            headers['X-Namespace'] = 'legacy-use'
        
        connect_kwargs = {}
        if subprotocol:
            connect_kwargs['subprotocols'] = [subprotocol]
            
        async with websockets.connect(novnc_ws_url, additional_headers=headers, **connect_kwargs) as ws_client:
            logger.info(f'[VNC-WS] Connected to container for session {session_id}')

            # Create tasks for bidirectional communication
            async def forward_to_target():
                try:
                    logger.info(f'[VNC-WS] Starting forward_to_target task for session {session_id}')
                    message_count = 0
                    while True:
                        # Receive message from client
                        logger.debug(f'[VNC-WS] Waiting for client message for session {session_id}')
                        data = await websocket.receive_bytes()
                        message_count += 1
                        logger.info(f'[VNC-WS] Received message #{message_count} from client ({len(data)} bytes) for session {session_id}')
                        logger.debug(f'[VNC-WS] First 20 bytes: {data[:20].hex() if data else "empty"}')

                        # Forward message to target
                        await ws_client.send(data)
                        logger.debug(f'[VNC-WS] Forwarded message to noVNC proxy for session {session_id}')
                except WebSocketDisconnect:
                    logger.info(
                        f'[VNC-WS] Client disconnected for session {session_id} after {message_count} messages'
                    )
                    return
                except websockets.exceptions.ConnectionClosed as e:
                    if e.code == 1001:
                        logger.info(
                            f'[VNC-WS] Target container going away for session {session_id} (normal shutdown)'
                        )
                    elif e.code == 1000:
                        logger.info(
                            f'[VNC-WS] Normal closure from target for session {session_id}'
                        )
                    else:
                        logger.warning(
                            f'[VNC-WS] Target connection closed with code {e.code}: {e.reason} for session {session_id}'
                        )
                    return
                except Exception as e:
                    logger.error(f'[VNC-WS] Error forwarding to target: {str(e)}')
                    return

            async def forward_to_client():
                try:
                    logger.info(f'[VNC-WS] Starting forward_to_client task for session {session_id}')
                    message_count = 0
                    while True:
                        # Receive message from target
                        logger.debug(f'[VNC-WS] Waiting for noVNC proxy message for session {session_id}')
                        data = await ws_client.recv()
                        message_count += 1
                        logger.info(f'[VNC-WS] Received message #{message_count} from noVNC proxy ({len(data) if isinstance(data, bytes) else len(data.encode())} bytes) for session {session_id}')
                        logger.debug(f'[VNC-WS] Data type: {type(data).__name__}, First 20 bytes: {(data[:20].hex() if isinstance(data, bytes) else data[:20]) if data else "empty"}')

                        # Forward message to client
                        if isinstance(data, str):
                            await websocket.send_text(data)
                            logger.debug(f'[VNC-WS] Sent text message to client for session {session_id}')
                        else:
                            await websocket.send_bytes(data)
                            logger.debug(f'[VNC-WS] Sent binary message to client for session {session_id}')
                except WebSocketDisconnect:
                    logger.info(
                        f'[VNC-WS] Client disconnected for session {session_id}'
                    )
                    return
                except websockets.exceptions.ConnectionClosed as e:
                    if e.code == 1001:
                        logger.info(
                            f'[VNC-WS] Target container going away for session {session_id} (normal shutdown)'
                        )
                    elif e.code == 1000:
                        logger.info(
                            f'[VNC-WS] Normal closure from target for session {session_id}'
                        )
                    else:
                        logger.warning(
                            f'[VNC-WS] Target connection closed with code {e.code}: {e.reason} for session {session_id}'
                        )
                    return
                except Exception as e:
                    logger.error(f'[VNC-WS] Error forwarding to client: {str(e)}')
                    return

            # Run both forwarding tasks concurrently
            forward_client_task = asyncio.create_task(forward_to_target())
            forward_target_task = asyncio.create_task(forward_to_client())

            # Wait for either task to complete (which means a connection was closed)
            done, pending = await asyncio.wait(
                [forward_client_task, forward_target_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancel the pending task
            for task in pending:
                task.cancel()

    except websockets.exceptions.ConnectionClosed:
        logger.info(f'[VNC-WS] WebSocket connection closed for session {session_id}')
    except Exception as e:
        logger.error(
            f'[VNC-WS] Error in WebSocket proxy for session {session_id}: {str(e)}'
        )
    finally:
        # Only try to close the WebSocket if it's still connected
        try:
            if websocket.client_state.CONNECTED:
                await websocket.close()
                logger.info(f'[VNC-WS] WebSocket closed for session {session_id}')
        except Exception as e:
            # Log but don't raise the error since this is cleanup code
            logger.debug(f'[VNC-WS] Error closing WebSocket in cleanup: {str(e)}')