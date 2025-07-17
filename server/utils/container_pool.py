"""
Container pool management for scalable Docker Compose deployments.

This module provides functionality to discover, allocate, and manage
containers in a scaled Docker Compose environment.
"""

import asyncio
import json
import logging
import subprocess
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

import httpx

logger = logging.getLogger(__name__)


class ContainerState(str, Enum):
    """States a container can be in within the pool."""
    AVAILABLE = "available"
    ALLOCATED = "allocated"
    INITIALIZING = "initializing"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ContainerInfo:
    """Information about a container in the pool."""
    
    def __init__(self, container_id: str, container_data: dict):
        self.id = container_id
        # Handle both docker ps --format json (Names is string) and docker inspect (Names is list)
        names = container_data.get('Names', '')
        if isinstance(names, list):
            self.name = names[0].lstrip('/') if names else ''
        else:
            self.name = names.lstrip('/')
        # Parse labels from string format if needed
        labels = container_data.get('Labels', {})
        if isinstance(labels, str):
            # Parse label string format: "key1=value1,key2=value2"
            self.labels = {}
            if labels:
                for label in labels.split(','):
                    if '=' in label:
                        key, value = label.split('=', 1)
                        self.labels[key] = value
        else:
            self.labels = labels
        self.state = container_data.get('State', 'unknown')
        self.status = container_data.get('Status', '')
        self.created = container_data.get('Created', 0)
        
        # Extract network info
        # docker ps --format json has Networks as a string, not nested dict
        networks = container_data.get('Networks', '')
        self.ip_address = None
        # For docker ps output, we'll need to get IP differently
        # For now, we'll leave it as None and use container name for connections
        
        # Extract port mappings
        self.ports = self._parse_ports(container_data.get('Ports', []))
        
        # Container type from labels or container name
        self.target_type = self.labels.get('legacy-use.target-type', 'unknown')
        
        # Check Kubernetes-style labels
        if self.target_type == 'unknown':
            k8s_component = self.labels.get('app.kubernetes.io/component', '')
            if 'wine-target' in k8s_component:
                self.target_type = 'wine'
            elif 'linux-target' in k8s_component or 'linux-machine' in k8s_component:
                self.target_type = 'linux'
            elif 'android-target' in k8s_component:
                self.target_type = 'android'
        
        # If still unknown, try to determine from container name
        if self.target_type == 'unknown':
            if 'wine-target' in self.name:
                self.target_type = 'wine'
            elif 'linux-machine' in self.name or 'linux-target' in self.name:
                self.target_type = 'linux'
            elif 'android-target' in self.name:
                self.target_type = 'android'
        
        # Check if container is one of our target containers
        self.is_scalable = (
            self.target_type in ['wine', 'linux', 'android'] or
            any(target in self.name for target in ['wine-target', 'linux-machine', 'linux-target', 'android-target'])
        )
        
        # Allocation info (stored in our tracking, not in Docker)
        self.allocated_to: Optional[str] = None
        self.allocated_at: Optional[datetime] = None
        self.pool_state = ContainerState.UNKNOWN
    
    def _parse_ports(self, ports_data) -> dict:
        """Parse Docker port data into a usable format."""
        port_map = {}
        # Handle string format from docker ps --format json
        if isinstance(ports_data, str):
            # Parse "0.0.0.0:5900->5900/tcp, [::]:5900->5900/tcp" format
            for port_spec in ports_data.split(', '):
                if '->' in port_spec:
                    parts = port_spec.split('->')
                    if len(parts) == 2 and ':' in parts[0]:
                        # Extract public port from "0.0.0.0:5900" or "[::]:5900"
                        public_part = parts[0].split(':')[-1]
                        # Extract private port from "5900/tcp"
                        private_part = parts[1].split('/')[0]
                        port_map[private_part] = public_part
        # Handle list format from docker inspect
        elif isinstance(ports_data, list):
            for port_info in ports_data:
                if isinstance(port_info, dict) and port_info.get('PublicPort') and port_info.get('PrivatePort'):
                    private = port_info['PrivatePort']
                    public = port_info['PublicPort']
                    port_map[str(private)] = str(public)
        return port_map
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'target_type': self.target_type,
            'state': self.state,
            'pool_state': self.pool_state.value,
            'ip_address': self.ip_address,
            'ports': self.ports,
            'allocated_to': self.allocated_to,
            'allocated_at': self.allocated_at.isoformat() if self.allocated_at else None,
            'is_scalable': self.is_scalable,
        }


class ContainerPool:
    """Manages a pool of containers for session allocation."""
    
    def __init__(self):
        self._containers: Dict[str, ContainerInfo] = {}
        self._allocations: Dict[str, str] = {}  # session_id -> container_id
        self._lock = asyncio.Lock()
        self._last_refresh = datetime.min
        self._refresh_interval = timedelta(seconds=5)
    
    async def refresh(self, force: bool = False) -> None:
        """Refresh the container pool from Docker."""
        async with self._lock:
            now = datetime.now()
            if not force and (now - self._last_refresh) < self._refresh_interval:
                return
            
            try:
                # Get all containers
                result = subprocess.run(
                    ['docker', 'ps', '--format', 'json', '--no-trunc'],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                
                new_containers = {}
                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    
                    container_data = json.loads(line)
                    container_info = ContainerInfo(container_data['ID'], container_data)
                    
                    # Only track scalable legacy-use containers
                    if container_info.is_scalable:
                        # Preserve allocation info from existing tracking
                        if container_info.id in self._containers:
                            old_info = self._containers[container_info.id]
                            container_info.allocated_to = old_info.allocated_to
                            container_info.allocated_at = old_info.allocated_at
                            container_info.pool_state = old_info.pool_state
                        else:
                            # New container, check if it's healthy
                            if container_info.state == 'running':
                                container_info.pool_state = ContainerState.AVAILABLE
                            else:
                                container_info.pool_state = ContainerState.INITIALIZING
                        
                        new_containers[container_info.id] = container_info
                
                self._containers = new_containers
                self._last_refresh = now
                
                # Update allocations based on current state
                self._update_allocations()
                
                logger.info(f"Container pool refreshed: {len(self._containers)} containers")
                
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to refresh container pool: {e.stderr}")
            except Exception as e:
                logger.error(f"Unexpected error refreshing container pool: {e}")
    
    def _update_allocations(self) -> None:
        """Update allocation tracking based on container states."""
        # Remove allocations for containers that no longer exist
        current_container_ids = set(self._containers.keys())
        dead_allocations = []
        
        for session_id, container_id in self._allocations.items():
            if container_id not in current_container_ids:
                dead_allocations.append(session_id)
        
        for session_id in dead_allocations:
            del self._allocations[session_id]
    
    async def get_available_containers(self, target_type: Optional[str] = None) -> List[ContainerInfo]:
        """Get all available containers, optionally filtered by target type."""
        # Refresh before getting containers
        await self.refresh()
        
        containers = []
        for container in self._containers.values():
            if container.pool_state == ContainerState.AVAILABLE:
                if target_type is None or container.target_type == target_type:
                    containers.append(container)
        
        return containers
    
    def _get_available_containers_locked(self, target_type: Optional[str] = None) -> List[ContainerInfo]:
        """Get available containers without acquiring lock (for use within locked methods)."""
        containers = []
        for container in self._containers.values():
            if container.pool_state == ContainerState.AVAILABLE:
                if target_type is None or container.target_type == target_type:
                    containers.append(container)
        
        return containers
    
    async def allocate_container(self, session_id: str, target_type: str) -> Optional[ContainerInfo]:
        """Allocate a container for a session."""
        # Refresh pool before allocation (outside of lock)
        await self.refresh()
        
        async with self._lock:
            # Check if session already has an allocation
            if session_id in self._allocations:
                container_id = self._allocations[session_id]
                if container_id in self._containers:
                    return self._containers[container_id]
            
            # Find available container of the right type (use locked version)
            available = self._get_available_containers_locked(target_type)
            if not available:
                logger.info(f"No available containers for type: {target_type}, attempting to scale up")
                # Scale up the service
                if await self._scale_up_service(target_type):
                    # Wait a moment for the new container to be ready
                    await asyncio.sleep(5)
                    # Can't refresh within lock, so we'll need to exit and retry
                    logger.info(f"Scaled up {target_type}, but need to retry allocation")
                    return None
                else:
                    logger.error(f"Failed to scale up {target_type} service")
                    return None
            
            # Allocate the first available container
            container = available[0]
            container.allocated_to = session_id
            container.allocated_at = datetime.now()
            container.pool_state = ContainerState.ALLOCATED
            
            self._allocations[session_id] = container.id
            
            # Update container label to mark it as allocated
            try:
                result = subprocess.run(
                    ['docker', 'container', 'update', '--label', 'legacy-use.allocated=true', container.id],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    logger.warning(f"Failed to label container as allocated: {result.stderr}")
            except Exception as e:
                logger.warning(f"Error labeling container: {e}")
            
            logger.info(f"Allocated container {container.id} to session {session_id}")
            return container
    
    async def release_container(self, session_id: str) -> bool:
        """Release a container back to the pool."""
        async with self._lock:
            if session_id not in self._allocations:
                return False
            
            container_id = self._allocations[session_id]
            if container_id in self._containers:
                container = self._containers[container_id]
                target_type = container.target_type
                
                container.allocated_to = None
                container.allocated_at = None
                container.pool_state = ContainerState.AVAILABLE
                
                del self._allocations[session_id]
                
                # Update container label to mark it as available
                try:
                    result = subprocess.run(
                        ['docker', 'container', 'update', '--label', 'legacy-use.allocated=false', container_id],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode != 0:
                        logger.warning(f"Failed to label container as available: {result.stderr}")
                except Exception as e:
                    logger.warning(f"Error labeling container: {e}")
                
                logger.info(f"Released container {container_id} from session {session_id}")
                
                # Check if we should scale down
                # Run scale down in background to not block the release
                asyncio.create_task(self._check_scale_down(target_type))
                
                return True
            
            return False
    
    async def _check_scale_down(self, target_type: str) -> None:
        """Check if we should scale down after releasing a container."""
        try:
            # Wait a bit to allow other operations to complete
            await asyncio.sleep(10)
            
            # Refresh to get latest state
            await self.refresh(force=True)
            
            # Try to scale down if we have excess containers
            await self._scale_down_service(target_type)
        except Exception as e:
            logger.error(f"Error in scale down check: {e}")
    
    async def get_container_for_session(self, session_id: str) -> Optional[ContainerInfo]:
        """Get the container allocated to a session."""
        await self.refresh()
        
        if session_id in self._allocations:
            container_id = self._allocations[session_id]
            return self._containers.get(container_id)
        
        return None
    
    async def get_pool_status(self) -> dict:
        """Get status information about the container pool."""
        await self.refresh()
        
        status = {
            'total_containers': len(self._containers),
            'available': 0,
            'allocated': 0,
            'initializing': 0,
            'unhealthy': 0,
            'by_type': {},
        }
        
        for container in self._containers.values():
            # Count by state
            if container.pool_state == ContainerState.AVAILABLE:
                status['available'] += 1
            elif container.pool_state == ContainerState.ALLOCATED:
                status['allocated'] += 1
            elif container.pool_state == ContainerState.INITIALIZING:
                status['initializing'] += 1
            elif container.pool_state == ContainerState.UNHEALTHY:
                status['unhealthy'] += 1
            
            # Count by type
            if container.target_type not in status['by_type']:
                status['by_type'][container.target_type] = {
                    'total': 0,
                    'available': 0,
                    'allocated': 0,
                }
            
            status['by_type'][container.target_type]['total'] += 1
            if container.pool_state == ContainerState.AVAILABLE:
                status['by_type'][container.target_type]['available'] += 1
            elif container.pool_state == ContainerState.ALLOCATED:
                status['by_type'][container.target_type]['allocated'] += 1
        
        return status
    
    async def check_container_health(self, container: ContainerInfo) -> bool:
        """Check if a container is healthy."""
        if not container.ip_address:
            return False
        
        health_url = f'http://{container.ip_address}:8088/health'
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(health_url)
                return response.status_code == 200
        except Exception:
            return False
    
    async def _scale_up_service(self, target_type: str) -> bool:
        """Scale up a service by one container."""
        # Map target type to service name
        service_map = {
            'wine': 'wine-target',
            'linux': 'linux-machine',
            'android': 'android-target',
        }
        
        service_name = service_map.get(target_type)
        if not service_name:
            logger.error(f"Unknown target type for scaling: {target_type}")
            return False
        
        try:
            # Get current count
            current_count = len([c for c in self._containers.values() 
                               if c.target_type == target_type])
            new_count = current_count + 1
            
            logger.info(f"Scaling {service_name} from {current_count} to {new_count} containers")
            
            # Use docker-compose to scale up
            cmd = [
                'docker-compose',
                'up',
                '--scale', f'{service_name}={new_count}',
                '--no-recreate',
                '-d'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Successfully scaled {service_name} to {new_count} containers")
                return True
            else:
                logger.error(f"Failed to scale {service_name}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error scaling {service_name}: {e}")
            return False
    
    async def _scale_down_service(self, target_type: str) -> bool:
        """Scale down a service if there are excess available containers."""
        # Map target type to service name
        service_map = {
            'wine': 'wine-target',
            'linux': 'linux-machine',
            'android': 'android-target',
        }
        
        service_name = service_map.get(target_type)
        if not service_name:
            logger.error(f"Unknown target type for scaling: {target_type}")
            return False
        
        try:
            # Count containers by state
            containers = [c for c in self._containers.values() 
                         if c.target_type == target_type]
            
            if len(containers) <= 1:
                # Don't scale below 1 container
                return False
            
            available_count = sum(1 for c in containers 
                                if c.pool_state == ContainerState.AVAILABLE)
            
            # Only scale down if we have at least 2 available containers
            if available_count >= 2:
                new_count = len(containers) - 1
                logger.info(f"Scaling down {service_name} from {len(containers)} to {new_count} containers")
                
                # Use docker-compose to scale down
                cmd = [
                    'docker-compose',
                    'up',
                    '--scale', f'{service_name}={new_count}',
                    '--no-recreate',
                    '-d'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    logger.info(f"Successfully scaled {service_name} to {new_count} containers")
                    return True
                else:
                    logger.error(f"Failed to scale {service_name}: {result.stderr}")
                    return False
            
            return False
                
        except Exception as e:
            logger.error(f"Error scaling down {service_name}: {e}")
            return False


# Global container pool instance
container_pool = ContainerPool()