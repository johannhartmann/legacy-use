"""
Target management routes.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from server.database import db
from server.models.base import Target, TargetCreate, TargetUpdate
from server.settings import settings

# Create router
target_router = APIRouter(prefix='/targets', tags=['Target Management'])


@target_router.get('/', response_model=List[Target])
async def list_targets(include_archived: bool = False):
    """List all available targets."""
    targets = db.list_targets(include_archived)

    # Add queue status and blocking jobs information to each target
    for target in targets:
        blocking_info = db.is_target_queue_paused(target['id'])
        target['queue_status'] = 'paused' if blocking_info['is_paused'] else 'running'
        target['blocking_jobs'] = blocking_info['blocking_jobs']
        target['has_blocking_jobs'] = blocking_info['is_paused']
        target['blocking_jobs_count'] = blocking_info['blocking_jobs_count']

        # Add active session status to each target
        target['has_active_session'] = db.has_active_session_for_target(target['id'])[
            'has_active_session'
        ]
        target['has_initializing_session'] = db.has_initializing_session_for_target(
            target['id']
        )

    return targets


@target_router.post('/', response_model=Target)
async def create_target(target: TargetCreate, request: Request):
    """Create a new target."""
    # Convert the Pydantic model to a dictionary and pass it to the database service
    result = db.create_target(target.dict())
    return result


@target_router.get('/{target_id}', response_model=Target)
async def get_target(target_id: UUID):
    """Get details of a specific target."""
    target = db.get_target(target_id)
    if not target:
        raise HTTPException(status_code=404, detail='Target not found')

    # Add queue status and blocking jobs information
    blocking_info = db.is_target_queue_paused(target_id)
    target['queue_status'] = 'paused' if blocking_info['is_paused'] else 'running'
    target['blocking_jobs'] = blocking_info['blocking_jobs']
    target['has_blocking_jobs'] = blocking_info['is_paused']
    target['blocking_jobs_count'] = blocking_info['blocking_jobs_count']

    return target


@target_router.put('/{target_id}', response_model=Target)
async def update_target(target_id: UUID, target: TargetUpdate, request: Request):
    """Update a target's configuration."""
    if not db.get_target(target_id):
        raise HTTPException(status_code=404, detail='Target not found')

    updated_target = db.update_target(target_id, target.dict(exclude_unset=True))

    # Add queue status and blocking jobs information
    blocking_info = db.is_target_queue_paused(target_id)
    updated_target['queue_status'] = (
        'paused' if blocking_info['is_paused'] else 'running'
    )
    updated_target['blocking_jobs'] = blocking_info['blocking_jobs']
    updated_target['has_blocking_jobs'] = blocking_info['is_paused']
    updated_target['blocking_jobs_count'] = blocking_info['blocking_jobs_count']

    return updated_target


@target_router.delete('/{target_id}')
async def delete_target(target_id: UUID, request: Request):
    """Archive a target (soft delete)."""
    if not db.get_target(target_id):
        raise HTTPException(status_code=404, detail='Target not found')
    db.delete_target(target_id)
    return {'message': 'Target archived'}


@target_router.delete(
    '/{target_id}/hard',
    include_in_schema=not settings.HIDE_INTERNAL_API_ENDPOINTS_IN_DOC,
)
async def hard_delete_target(target_id: UUID, request: Request):
    """Permanently delete a target (hard delete)."""
    if not db.get_target(target_id):
        raise HTTPException(status_code=404, detail='Target not found')
    db.hard_delete_target(target_id)
    return {'message': 'Target permanently deleted'}
