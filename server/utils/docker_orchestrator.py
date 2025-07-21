"""
Docker implementation of container orchestration.

This module implements container orchestration using Docker and docker-compose.
"""

import asyncio
import json
import logging
import subprocess
from typing import Dict, List, Optional

import httpx

from .container_orchestrator import ContainerOrchestrator, ContainerInfo

logger = logging.getLogger(__name__)


class DockerOrchestrator(ContainerOrchestrator):
    """Docker/docker-compose implementation of container orchestration."""
    
    # Mapping from target types to docker-compose service names
    SERVICE_MAPPING = {
        'linux': 'linux-machine',
        'wine': 'wine-target',
        'android': 'android-target',
        'windows': 'windows-target',
    }
    
    async def list_containers(self, label_filters: Optional[Dict[str, str]] = None) -> List[ContainerInfo]:
        """List all containers, optionally filtered by labels."""
        try:
            # Build docker ps command
            cmd = ['docker', 'ps', '--format', 'json']
            
            # Add label filters if provided
            if label_filters:
                for key, value in label_filters.items():
                    cmd.extend(['--filter', f'label={key}={value}'])
            
            # Run docker ps command
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                logger.error(f"Docker ps failed: {stderr.decode()}")
                return []
            
            containers = []
            for line in stdout.decode().strip().split('\n'):
                if line:
                    try:
                        data = json.loads(line)
                        # Parse labels from string format
                        labels = {}
                        if 'Labels' in data and data['Labels']:
                            for label in data['Labels'].split(','):
                                if '=' in label:
                                    key, value = label.split('=', 1)
                                    labels[key] = value
                        
                        # Get container details with docker inspect for IP
                        inspect_cmd = ['docker', 'inspect', data['ID']]
                        inspect_result = await asyncio.create_subprocess_exec(
                            *inspect_cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        inspect_stdout, _ = await inspect_result.communicate()
                        
                        ip = None
                        ports = {}
                        if inspect_result.returncode == 0:
                            inspect_data = json.loads(inspect_stdout.decode())[0]
                            # Get IP address
                            if 'NetworkSettings' in inspect_data and 'IPAddress' in inspect_data['NetworkSettings']:
                                ip = inspect_data['NetworkSettings']['IPAddress']
                            # Get port mappings
                            if 'NetworkSettings' in inspect_data and 'Ports' in inspect_data['NetworkSettings']:
                                for container_port, host_mappings in inspect_data['NetworkSettings']['Ports'].items():
                                    if host_mappings and len(host_mappings) > 0:
                                        port_num = container_port.split('/')[0]
                                        ports[port_num] = host_mappings[0]['HostPort']
                        
                        container = ContainerInfo(
                            id=data['ID'],
                            name=data['Names'],
                            labels=labels,
                            status=data['State'],
                            ip=ip,
                            ports=ports
                        )
                        containers.append(container)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse docker output: {line}")
                        
            return containers
            
        except Exception as e:
            logger.error(f"Failed to list containers: {e}")
            return []
    
    async def get_container(self, container_id: str) -> Optional[ContainerInfo]:
        """Get information about a specific container."""
        containers = await self.list_containers()
        for container in containers:
            if container.id == container_id or container.name == container_id:
                return container
        return None
    
    async def scale_service(self, service_name: str, replicas: int) -> bool:
        """Scale a docker-compose service to the specified number of replicas."""
        try:
            cmd = [
                'docker-compose',
                '--project-name', 'legacy-use',
                'up', '-d',
                '--scale', f'{service_name}={replicas}',
                '--no-recreate',
                service_name
            ]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                logger.info(f"Successfully scaled {service_name} to {replicas} containers")
                return True
            else:
                logger.error(f"Failed to scale {service_name}: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Error scaling {service_name}: {e}")
            return False
    
    async def check_health(self, container_id: str, health_check_url: str) -> bool:
        """Check if a container is healthy via HTTP endpoint."""
        try:
            container = await self.get_container(container_id)
            if not container:
                return False
                
            # Use container IP for health check
            url = f"http://{container.ip}:8088{health_check_url}"
            
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(url)
                return response.status_code == 200
                
        except Exception as e:
            logger.debug(f"Health check failed for {container_id}: {e}")
            return False
    
    def get_service_name_for_target(self, target_type: str) -> str:
        """Get the docker-compose service name for a given target type."""
        return self.SERVICE_MAPPING.get(target_type, target_type)
    
    def get_container_url(self, container_info: ContainerInfo, port: int = 8088) -> str:
        """Get the URL to access a container's service."""
        # In Docker, we use the container IP directly
        return f"http://{container_info.ip}:{port}"