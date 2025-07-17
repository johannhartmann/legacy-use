"""
Container pool management routes for scalable deployments.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from server.utils.container_pool import container_pool

logger = logging.getLogger(__name__)

# Create router
container_router = APIRouter(prefix='/containers', tags=['Container Pool Management'])


@container_router.get('/')
async def list_containers(
    target_type: Optional[str] = Query(None, description="Filter by target type"),
    available_only: bool = Query(False, description="Only show available containers"),
):
    """List all containers in the pool."""
    await container_pool.refresh()
    
    if available_only:
        containers = await container_pool.get_available_containers(target_type)
    else:
        containers = []
        for container in container_pool._containers.values():
            if target_type is None or container.target_type == target_type:
                containers.append(container)
    
    return {
        'containers': [c.to_dict() for c in containers],
        'total': len(containers),
    }


@container_router.get('/status')
async def get_pool_status():
    """Get overall container pool status."""
    status = await container_pool.get_pool_status()
    return status


@container_router.post('/{target_type}/allocate')
async def allocate_container(target_type: str, session_id: str):
    """Allocate a container for a session."""
    container = await container_pool.allocate_container(session_id, target_type)
    
    if not container:
        raise HTTPException(
            status_code=503,
            detail=f"No available containers for target type: {target_type}",
        )
    
    return {
        'allocated': True,
        'container': container.to_dict(),
    }


@container_router.post('/{session_id}/release')
async def release_container(session_id: str):
    """Release a container back to the pool."""
    released = await container_pool.release_container(session_id)
    
    if not released:
        raise HTTPException(
            status_code=404,
            detail=f"No container allocated to session: {session_id}",
        )
    
    return {
        'released': True,
        'session_id': session_id,
    }


@container_router.get('/session/{session_id}')
async def get_session_container(session_id: str):
    """Get the container allocated to a specific session."""
    container = await container_pool.get_container_for_session(session_id)
    
    if not container:
        raise HTTPException(
            status_code=404,
            detail=f"No container allocated to session: {session_id}",
        )
    
    return container.to_dict()


@container_router.post('/refresh')
async def refresh_pool():
    """Force refresh the container pool from Docker."""
    await container_pool.refresh(force=True)
    status = await container_pool.get_pool_status()
    
    return {
        'refreshed': True,
        'status': status,
    }