"""
Container pool manager.

This module provides a clean way to manage container allocation
for both Docker Compose and Kubernetes environments.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set

from server.settings import settings
from .docker_orchestrator import DockerOrchestrator
from .kubernetes_orchestrator import KubernetesOrchestrator
from .container_orchestrator import ContainerOrchestrator, ContainerInfo

logger = logging.getLogger(__name__)


class ContainerPool:
    """Container pool that tracks available containers and their allocations."""
    
    def __init__(self):
        # Choose orchestrator based on environment
        if settings.CONTAINER_ORCHESTRATOR.lower() == 'kubernetes':
            self._orchestrator: ContainerOrchestrator = KubernetesOrchestrator()
            logger.info("Using Kubernetes orchestrator")
        else:
            self._orchestrator: ContainerOrchestrator = DockerOrchestrator()
            logger.info("Using Docker orchestrator")
        
        # Simple allocation tracking: session_id -> container_id
        self._allocations: Dict[str, str] = {}
        # Reverse mapping: container_id -> session_id
        self._container_to_session: Dict[str, str] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def allocate_container(self, session_id: str, target_type: str) -> Optional[ContainerInfo]:
        """
        Allocate a container for a session.
        
        Returns the allocated container info, or None if no container is available.
        """
        async with self._lock:
            # Check if session already has an allocation
            if session_id in self._allocations:
                container_id = self._allocations[session_id]
                # Get fresh container info
                container = await self._orchestrator.get_container(container_id)
                if container and container.is_healthy:
                    return container
                else:
                    # Container is gone or unhealthy, clean up allocation
                    self._deallocate(session_id)
            
            # Find an available container of the right type
            container = await self._find_available_container(target_type)
            
            if container:
                # Allocate it
                self._allocations[session_id] = container.id
                self._container_to_session[container.id] = session_id
                logger.info(f"Allocated container {container.id} ({container.name}) to session {session_id}")
                return container
            else:
                logger.warning(f"No available {target_type} containers")
                return None
    
    async def release_container(self, session_id: str) -> None:
        """Release a container allocation."""
        async with self._lock:
            self._deallocate(session_id)
    
    async def _find_available_container(self, target_type: str) -> Optional[ContainerInfo]:
        """Find an available container of the specified type."""
        # Get all containers - we'll filter for scalable ones ourselves
        all_containers = await self._orchestrator.list_containers()
        
        for container in all_containers:
            # Skip non-scalable containers
            if container.labels.get('legacy-use.scalable') != 'true':
                continue
                
            # Check if it's the right type
            container_type = container.labels.get('legacy-use.target-type', 'unknown')
            
            # For backwards compatibility, also check container name
            if container_type == 'unknown':
                if 'wine-target' in container.name:
                    container_type = 'wine'
                elif 'linux-target' in container.name or 'linux-machine' in container.name:
                    container_type = 'linux'
                elif 'android-aind-target' in container.name:
                    container_type = 'android-aind'
                elif 'android-target' in container.name:
                    container_type = 'android'
                elif 'dosbox-target' in container.name:
                    container_type = 'dosbox'
                elif 'windows' in container.name:
                    container_type = 'windows-vm'
            
            # Skip if wrong type
            if container_type != target_type:
                continue
            
            # Skip if not healthy
            if not container.is_healthy:
                logger.debug(f"Container {container.name} is not healthy (status: {container.status})")
                continue
            
            # Skip if already allocated
            if container.id in self._container_to_session:
                logger.debug(f"Container {container.name} is already allocated")
                continue
            
            # Found an available container!
            logger.info(f"Found available {target_type} container: {container.name}")
            return container
        
        return None
    
    def _deallocate(self, session_id: str) -> None:
        """Remove allocation for a session (internal, assumes lock is held)."""
        if session_id in self._allocations:
            container_id = self._allocations[session_id]
            del self._allocations[session_id]
            if container_id in self._container_to_session:
                del self._container_to_session[container_id]
            logger.info(f"Deallocated container {container_id} from session {session_id}")
    
    async def get_pool_status(self) -> Dict:
        """Get current pool status for debugging."""
        async with self._lock:
            all_containers = await self._orchestrator.list_containers()
            
            status = {
                'total_containers': 0,  # Will count scalable ones
                'allocated': len(self._allocations),
                'available': 0,
                'by_type': {}
            }
            for container in all_containers:
                # Only count scalable containers
                if container.labels.get('legacy-use.scalable') != 'true':
                    continue
                    
                status['total_containers'] += 1
                container_type = container.labels.get('legacy-use.target-type', 'unknown')
                if container_type == 'unknown':
                    if 'wine-target' in container.name:
                        container_type = 'wine'
                    elif 'linux-target' in container.name or 'linux-machine' in container.name:
                        container_type = 'linux'
                    elif 'android-aind-target' in container.name:
                        container_type = 'android-aind'
                    elif 'android-target' in container.name:
                        container_type = 'android'
                    elif 'dosbox-target' in container.name:
                        container_type = 'dosbox'
                    elif 'windows-xp' in container.name:
                        container_type = 'windows-xp-vm'
                    elif 'windows' in container.name:
                        container_type = 'windows-vm'
                
                if container_type not in status['by_type']:
                    status['by_type'][container_type] = {'total': 0, 'available': 0, 'allocated': 0}
                
                status['by_type'][container_type]['total'] += 1
                
                if container.id not in self._container_to_session and container.is_healthy:
                    status['available'] += 1
                    status['by_type'][container_type]['available'] += 1
                elif container.id in self._container_to_session:
                    status['by_type'][container_type]['allocated'] += 1
            
            return status


# Global instance
container_pool = ContainerPool()