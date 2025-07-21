"""
Abstract base class for container orchestration.

This module defines the interface that both Docker and Kubernetes
orchestrators must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class ContainerInfo:
    """Information about a container/pod."""
    
    def __init__(self, id: str, name: str, labels: Dict[str, str], 
                 status: str, ip: Optional[str] = None, ports: Optional[Dict[str, str]] = None):
        self.id = id
        self.name = name
        self.labels = labels
        self.status = status
        self.ip = ip
        self.ports = ports or {}
        
    @property
    def is_healthy(self) -> bool:
        """Check if container/pod is healthy."""
        return self.status.lower() in ['running', 'healthy']


class ContainerOrchestrator(ABC):
    """Abstract base class for container orchestration."""
    
    @abstractmethod
    async def list_containers(self, label_filters: Optional[Dict[str, str]] = None) -> List[ContainerInfo]:
        """List all containers/pods, optionally filtered by labels."""
        pass
    
    @abstractmethod
    async def get_container(self, container_id: str) -> Optional[ContainerInfo]:
        """Get information about a specific container/pod."""
        pass
    
    @abstractmethod
    async def scale_service(self, service_name: str, replicas: int) -> bool:
        """Scale a service to the specified number of replicas."""
        pass
    
    @abstractmethod
    async def check_health(self, container_id: str, health_check_url: str) -> bool:
        """Check if a container/pod is healthy via HTTP endpoint."""
        pass
    
    @abstractmethod
    def get_service_name_for_target(self, target_type: str) -> str:
        """Get the service name for a given target type."""
        pass
    
    @abstractmethod
    def get_container_url(self, container_info: ContainerInfo, port: int = 8088) -> str:
        """Get the URL to access a container's service."""
        pass