"""
Orchestrator-aware utility functions that work with both Docker and Kubernetes.
"""

import logging
from typing import Dict, Optional
from server.settings import settings
from server.utils.docker_orchestrator import DockerOrchestrator
from server.utils.kubernetes_orchestrator import KubernetesOrchestrator
from server.utils.container_orchestrator import ContainerOrchestrator

logger = logging.getLogger(__name__)

# Global orchestrator instance
_orchestrator: Optional[ContainerOrchestrator] = None


def get_orchestrator() -> ContainerOrchestrator:
    """Get the appropriate orchestrator based on environment."""
    global _orchestrator
    if _orchestrator is None:
        orchestrator_type = settings.CONTAINER_ORCHESTRATOR.lower()
        if orchestrator_type == 'kubernetes':
            _orchestrator = KubernetesOrchestrator()
            logger.info("Using Kubernetes orchestrator")
        else:
            _orchestrator = DockerOrchestrator()
            logger.info("Using Docker orchestrator")
    return _orchestrator


async def get_container_status(container_id: str, state: str) -> Dict:
    """
    Get status information about a container using the appropriate orchestrator.
    
    This function handles all errors internally and never throws exceptions.
    If there is an error, it returns a dictionary with error information.
    
    Args:
        container_id: ID of the container
        state: Optional state of the session for logging context
        
    Returns:
        Dictionary with container status information. If there is an error,
        the dictionary will contain an 'error' field with the error message.
    """
    try:
        # Skip checking destroyed sessions
        if state in ['destroying', 'destroyed']:
            return {'id': container_id, 'state': {'Status': 'unavailable'}}
        
        orchestrator = get_orchestrator()
        container_info = await orchestrator.get_container(container_id)
        
        if not container_info:
            return {
                'id': container_id,
                'state': {'Status': 'not_found'},
                'error': f'Container {container_id} not found'
            }
        
        # Build status data
        status_data = {
            'id': container_id,
            'state': {
                'Status': container_info.status,
                'Running': container_info.is_healthy
            },
            'network_settings': {
                'IPAddress': container_info.ip or ''
            }
        }
        
        # For Kubernetes, we trust the pod status
        if settings.CONTAINER_ORCHESTRATOR.lower() == 'kubernetes':
            status_data['health'] = {
                'status': 'healthy' if container_info.is_healthy else 'unhealthy',
                'details': f'Pod status: {container_info.status}'
            }
        
        return status_data
        
    except Exception as e:
        logger.error(f'Error getting container status: {str(e)}')
        return {
            'id': container_id,
            'state': {'Status': 'error'},
            'error': str(e)
        }