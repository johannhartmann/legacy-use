"""
Session management routes.
"""

import asyncio
import logging
import os
import re
from typing import Any, Dict
from uuid import UUID

import requests
import websockets
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from starlette.websockets import WebSocket, WebSocketDisconnect

from server.config.default_ports import DEFAULT_PORTS
from server.database import db
from server.models.base import Session, SessionCreate, SessionUpdate
from server.settings import settings
from server.utils.docker_manager import (
    launch_container,
    stop_container,
)
from server.utils.orchestrator_utils import get_container_status

logger = logging.getLogger(__name__)

# Create router
session_router = APIRouter(prefix='/sessions', tags=['Session Management'])

# Create a separate router for WebSocket endpoints (no API key required)
# TODO: Move the websocket to a different prefix -> e.g. /ws/sessions/
websocket_router = APIRouter(prefix='/sessions', tags=['WebSocket Endpoints'])


@session_router.get('/')
async def list_sessions(include_archived: bool = False):
    """List all active sessions."""
    sessions = db.list_sessions(include_archived)

    # Add container status to each session
    for session in sessions:
        if container_id := session.get('container_id'):
            container_status = await get_container_status(
                container_id, state=session.get('state')
            )
            session['container_status'] = container_status

    return sessions


@session_router.post('/', response_model=Session)
async def create_session(
    session: SessionCreate, request: Request, get_or_create: bool = False
):
    """
    Create a new session for a target.

    If get_or_create is True, will return an existing ready session for the target if one exists.
    """
    # Check if target exists
    target = db.get_target(session.target_id)
    if not target:
        raise HTTPException(status_code=404, detail='Target not found')

    # Check for existing active sessions for this target (unless get_or_create is True)
    if not get_or_create:
        active_session_info = db.has_active_session_for_target(session.target_id)
        if active_session_info['has_active_session']:
            existing_session = active_session_info['session']
            raise HTTPException(
                status_code=409,
                detail={
                    'message': 'An active session already exists for this target',
                    'existing_session': {
                        # converting to non json serializable types
                        'id': str(existing_session['id']),
                        'name': existing_session['name'],
                        'state': existing_session['state'],
                        'status': existing_session['status'],
                        'created_at': existing_session['created_at'].isoformat()
                        if existing_session['created_at']
                        else None,
                    },
                },
            )

    # If get_or_create is True, check for existing active sessions for this target
    if get_or_create:
        target_sessions = db.list_target_sessions(
            session.target_id, include_archived=False
        )

        # Filter for sessions in "ready" state
        ready_sessions = [s for s in target_sessions if s.get('state') == 'ready']

        if ready_sessions:
            # Return the first ready session
            session_data = ready_sessions[0]

            # Add container status
            if container_id := session_data.get('container_id'):
                container_status = await get_container_status(
                    container_id, state=session_data.get('state')
                )
                session_data['container_status'] = container_status

            return session_data

    # No ready session found or get_or_create is False, create a new one
    session_data = session.dict()
    session_data['state'] = 'initializing'  # Set initial state
    db_session = db.create_session(session_data)

    # Prepare container parameters
    session_target_type = target.get('type')
    # Split by the first occurrence of either '_' or '+'
    parts = re.split(r'[_+]', session_target_type, maxsplit=1)
    if len(parts) == 2:
        client_type, vpn_type = parts
    else:
        client_type = session_target_type
        vpn_type = 'direct'

    container_params = {
        'REMOTE_CLIENT_TYPE': client_type,
        'REMOTE_VPN_TYPE': vpn_type,
        'HOST_IP': target.get('host'),
        'HOST_PORT': target.get('port')
        or str(DEFAULT_PORTS.get(target.get('type'), 'unknown')),
        'VPN_CONFIG': target.get('vpn_config'),
        'VPN_USERNAME': target.get('vpn_username'),
        'VPN_PASSWORD': target.get('vpn_password'),
        'REMOTE_USERNAME': target.get('username'),
        'REMOTE_PASSWORD': target.get('password'),
        'WIDTH': str(target.get('width', 1024)),
        'HEIGHT': str(target.get('height', 768)),
    }

    # Always use container pool for scaling (both docker-compose and k8s)
    use_container_pool = True
    
    if use_container_pool:
        # Use container pool to allocate existing container
        from server.utils.container_pool import container_pool
        
        # Use pool_type from the target configuration, fallback to client_type
        pool_target_type = target.get('pool_type', client_type)
        
        # Allocate container from pool
        container_info = await container_pool.allocate_container(
            str(db_session['id']), pool_target_type
        )
        
        if container_info:
            # Get VNC and noVNC ports from container
            vnc_port = container_info.ports.get('5900', '5900')  # Default to 5900 if not found
            novnc_port = container_info.ports.get('6080', '') or container_info.ports.get('80', '')
            
            # Check if this is a KubeVirt VM (has vmi_name in ports)
            vmi_name = container_info.ports.get('vmi_name')
            
            # In Kubernetes, ports are not mapped - use internal ports directly
            if settings.CONTAINER_ORCHESTRATOR.lower() == 'kubernetes':
                # Regular containers
                vnc_port = '5900'
                # Linux target uses nginx on port 80
                if pool_target_type == 'linux':
                    novnc_port = '80'
                else:
                    # Other targets use port 6080 directly
                    novnc_port = '6080'
            
            # Update session with container info
            # Use container name as IP since containers can reach each other by name
            container_ip = container_info.ip or container_info.name
            db.update_session(
                db_session['id'],
                {
                    'container_id': container_info.id,
                    'container_ip': container_ip,
                    'status': 'running',
                    'state': 'ready',  # Containers in pool are already initialized
                    'vnc_port': vnc_port,
                    'novnc_port': novnc_port,
                },
            )
            # Get updated session
            db_session = db.get_session(db_session['id'])
            
            # Add container status
            container_status = await get_container_status(
                container_info.id, state=db_session.get('state')
            )
            db_session['container_status'] = container_status
        else:
            # No available containers in pool
            db.update_session(
                db_session['id'], 
                {
                    'status': 'error', 
                    'state': 'initializing',
                    'error_message': f'No available {pool_target_type} containers in pool'
                }
            )
            raise HTTPException(
                status_code=503,
                detail=f"No available {pool_target_type} containers. Please try again later or scale up the containers."
            )
    else:
        # Original container launch logic
        container_id, container_ip = launch_container(
            target['type'], str(db_session['id']), container_params=container_params
        )

        if container_id and container_ip:
            # Update session with container info
            db.update_session(
                db_session['id'],
                {
                    'container_id': container_id,
                    'container_ip': container_ip,
                    'status': 'running',
                    'state': 'initializing',  # Ensure state is set
                },
            )
            # Get updated session
            db_session = db.get_session(db_session['id'])

            # Add container status
            if container_id := db_session.get('container_id'):
                container_status = await get_container_status(
                    container_id, state=db_session.get('state')
                )
                db_session['container_status'] = container_status
        else:
            # Update session status to error if container launch failed
            db.update_session(
                db_session['id'], {'status': 'error', 'state': 'initializing'}
            )

    return db_session


@session_router.get('/{session_id}')
async def get_session(session_id: UUID):
    """Get details of a specific session."""
    if session := db.get_session(session_id):
        # If the session has a container_id, get container status
        if container_id := session.get('container_id'):
            container_status = await get_container_status(
                container_id, state=session.get('state')
            )
            # Add container status to session data
            session['container_status'] = container_status
        
        # Add target vnc_path for frontend VNC viewer
        if target_id := session.get('target_id'):
            target = db.get_target(target_id)
            if target:
                session['target_vnc_path'] = target.get('vnc_path', 'vnc.html')

        return session
    raise HTTPException(status_code=404, detail='Session not found')


@session_router.put('/{session_id}')
async def update_session(session_id: UUID, session: SessionUpdate):
    """Update a session's configuration."""
    if not db.get_session(session_id):
        raise HTTPException(status_code=404, detail='Session not found')

    # Update session
    updated_session = db.update_session(session_id, session.dict(exclude_unset=True))

    # Add container status if container_id exists
    if container_id := updated_session.get('container_id'):
        container_status = await get_container_status(
            container_id, state=updated_session.get('state')
        )
        updated_session['container_status'] = container_status

    return updated_session


@session_router.delete('/{session_id}')
async def delete_session(session_id: UUID, request: Request):
    """Archive a session."""
    # Check if session exists
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')

    # Update session state to destroying and set archive reason
    db.update_session(
        session_id,
        {
            'state': 'destroying',
            'is_archived': True,
            'archive_reason': 'user-initiated',
        },
    )

    # Always use container pool for scaling (both docker-compose and k8s)
    use_container_pool = True
    
    if use_container_pool:
        # Release container back to pool
        from server.utils.container_pool import container_pool
        await container_pool.release_container(str(session_id))
        logger.info(f'Released container for session {session_id} back to pool')
    else:
        # Stop the container if it exists (original logic)
        if container_id := session.get('container_id'):
            try:
                stop_container(container_id)
            except Exception as e:
                logger.error(f'Error stopping container: {str(e)}')

    # Return success message
    return {'message': 'Session archived successfully'}


@session_router.delete('/{session_id}/hard')
async def hard_delete_session(session_id: UUID, request: Request):
    """Permanently delete a session and stop its container (hard delete)."""
    # Get session
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')

    # Always use container pool for scaling (both docker-compose and k8s)
    use_container_pool = True
    
    if use_container_pool:
        # Release container back to pool
        from server.utils.container_pool import container_pool
        await container_pool.release_container(str(session_id))
    else:
        # Stop container if it exists (original logic)
        if session.get('container_id'):
            stop_container(session['container_id'])

    # Delete session from database
    db.hard_delete_session(session_id)

    return {'message': 'Session permanently deleted'}


@session_router.post('/{session_id}/execute', response_model=Dict[str, Any])
async def execute_api_on_session(
    session_id: UUID, api_request: Dict[str, Any], request: Request
):
    """
    Execute an API call on the session's container.

    This endpoint forwards API requests to the container running the session.
    """
    # Get session
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')

    # Check if container is running
    if not session.get('container_id') or not session.get('container_ip'):
        raise HTTPException(status_code=400, detail='Session has no active container')

    # Forward request to container
    try:
        container_url = f'http://{session["container_ip"]}:8088/api/execute'
        response = requests.post(container_url, json=api_request, timeout=30)

        # Return response from container
        return response.json()
    except requests.RequestException as e:
        logger.error(f'Error communicating with container: {str(e)}')
        raise HTTPException(
            status_code=502, detail=f'Error communicating with container: {str(e)}'
        ) from e


@session_router.get('/{session_id}/vnc/{path:path}', include_in_schema=True)
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
    
    # Use shared noVNC proxy
    novnc_proxy_url = os.getenv('NOVNC_PROXY_URL', 'http://novnc-proxy')
    
    # Get query parameters from the request
    params = dict(request.query_params)
    
    # For websockify connections, we need to pass target info
    if path == 'websockify':
        # Add target information as query parameters
        params['session_id'] = str(session_id)
        params['target_host'] = container_ip
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

        # Make the request to the container # TODO: Add auth to the request, but not critical
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

        # Return a streaming response
        return StreamingResponse(
            content=client_response.iter_content(chunk_size=8192),
            status_code=client_response.status_code,
            headers=response_headers,
            background=BackgroundTask(close_response),
        )
    except requests.RequestException as e:
        logger.error(f'Error proxying VNC request: {str(e)}')
        raise HTTPException(
            status_code=502, detail=f'Error proxying VNC request: {str(e)}'
        ) from e


# Move the WebSocket endpoint to the websocket_router
@websocket_router.websocket('/{session_id}/vnc/websockify')
async def proxy_vnc_websocket(websocket: WebSocket, session_id: UUID):
    """
    Proxy WebSocket connections for the VNC viewer.

    This endpoint forwards WebSocket connections to the container's VNC server.
    """
    logger.info(f'[VNC-WS] New WebSocket connection for session {session_id}')
    logger.info(
        '[VNC-WS] Clipboard monitor active (looking for message types 0x06/0x03 and prefix "Clipboard:")'
    )

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
    logger.info(f'[VNC-WS] Session details: container_ip={container_ip}, vnc_port={vnc_port}, container_id={container_id}')
    
    # Connect to shared noVNC proxy WebSocket with target information in headers
    novnc_proxy_host = os.getenv('NOVNC_PROXY_HOST', 'novnc-proxy')
    novnc_proxy_port = os.getenv('NOVNC_PROXY_PORT', '80')
    
    # Build WebSocket URL to shared proxy
    target_ws_url = f'ws://{novnc_proxy_host}:{novnc_proxy_port}/websockify'
    
    logger.info(f'[VNC-WS] Connecting to shared noVNC proxy: {target_ws_url}')

    # Accept the WebSocket connection with the same subprotocol if provided
    subprotocol = None
    if websocket.headers.get('sec-websocket-protocol'):
        # noVNC typically uses 'binary' or 'base64' subprotocol
        requested_protocols = websocket.headers.get('sec-websocket-protocol').split(',')
        # We'll accept the first protocol requested (usually 'binary')
        subprotocol = requested_protocols[0].strip()
        logger.info(f'[VNC-WS] Accepting WebSocket with subprotocol: {subprotocol}')
    
    await websocket.accept(subprotocol=subprotocol)

    def check_clipboard_content(data, direction_label):
        """Check if data contains clipboard filter string and log accordingly."""

        # Try to decode and check for filter string
        contains_filter = False
        try:
            text = None
            if isinstance(data, bytes):
                try:
                    text = data.decode('latin-1', errors='ignore')
                except Exception:
                    pass
            elif isinstance(data, str):
                text = data

            if text and 'Clipboard:' in text:
                contains_filter = True
                logger.info(f'[VNC-WS] 📋 Clipboard {direction_label} text="{text}"')
        except Exception:
            pass

        return contains_filter

    try:
        # Connect to the shared noVNC proxy with target information in headers
        headers = {
            'X-Session-Id': str(session_id),
            'X-Target-Host': container_ip,
            'X-Target-Port': vnc_port
        }
        
        # If this is a KubeVirt VM, pass the VMI name
        if container_ip == 'kubevirt-vm':
            headers['X-VMI-Name'] = container_id
            headers['X-Namespace'] = 'legacy-use'
        
        connect_kwargs = {}
        if subprotocol:
            connect_kwargs['subprotocols'] = [subprotocol]
            
        async with websockets.connect(target_ws_url, additional_headers=headers, **connect_kwargs) as ws_client:
            logger.info(f'[VNC-WS] Connected to container for session {session_id}')

            # Create tasks for bidirectional communication
            async def forward_to_target():
                try:
                    while True:
                        # Receive message from client
                        data = await websocket.receive_bytes()
                        check_clipboard_content(data, '⬆️')

                        # Forward message to target
                        await ws_client.send(data)
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
                    logger.error(f'[VNC-WS] Error forwarding to target: {str(e)}')
                    return

            async def forward_to_client():
                try:
                    while True:
                        # Receive message from target
                        data = await ws_client.recv()
                        check_clipboard_content(data, '⬇️')

                        # Forward message to client
                        if isinstance(data, str):
                            await websocket.send_text(data)
                        else:
                            await websocket.send_bytes(data)
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


# Add endpoint to check container pool status (for debugging)
@session_router.get('/pool/status')
async def get_pool_status():
    """Get container pool status for debugging."""
    from server.utils.container_pool import container_pool
    return await container_pool.get_pool_status()


# Add a new endpoint to update session state
@session_router.put('/{session_id}/state')
async def update_session_state(session_id: UUID, state: str):
    """Update the state of a session."""
    # Check if session exists
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')

    # Validate state
    valid_states = [
        'initializing',
        'authenticating',
        'ready',
        'destroying',
        'destroyed',
    ]
    if state not in valid_states:
        raise HTTPException(
            status_code=400,
            detail=f'Invalid state. Must be one of: {", ".join(valid_states)}',
        )

    # Update session state
    db.update_session(session_id, {'state': state})

    # If state is "destroying", also mark the session as archived
    if state == 'destroying':
        db.update_session(session_id, {'is_archived': True})

    # Return updated session
    return db.get_session(session_id)
