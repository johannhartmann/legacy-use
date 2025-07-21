"""
Kubernetes implementation of container orchestration.

This module implements container orchestration using Kubernetes API.
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional

import httpx
from kubernetes import client, config
from kubernetes.client.rest import ApiException

from .container_orchestrator import ContainerOrchestrator, ContainerInfo

logger = logging.getLogger(__name__)


class KubernetesOrchestrator(ContainerOrchestrator):
    """Kubernetes implementation of container orchestration."""
    
    # Mapping from target types to Kubernetes service names
    SERVICE_MAPPING = {
        'linux': 'legacy-use-linux-target',
        'wine': 'legacy-use-wine-target', 
        'android': 'legacy-use-android-target',
        'windows': 'legacy-use-windows-kubevirt',
    }
    
    # Mapping from target types to deployment/statefulset names
    DEPLOYMENT_MAPPING = {
        'linux': 'legacy-use-linux-target',
        'wine': 'legacy-use-wine-target',
        'android': 'legacy-use-android-target',
        'windows': 'legacy-use-windows-vmirs',  # VirtualMachineInstanceReplicaSet
    }
    
    def __init__(self, namespace: str = None):
        """Initialize Kubernetes client."""
        try:
            # Try to load in-cluster config first (when running in a pod)
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes config")
        except:
            # Fall back to kubeconfig file (for local development)
            try:
                config.load_kube_config()
                logger.info("Loaded kubeconfig from file")
            except Exception as e:
                logger.error(f"Failed to load Kubernetes config: {e}")
                raise
        
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.custom_api = client.CustomObjectsApi()
        
        # Get namespace from environment or use default
        self.namespace = namespace or os.getenv('KUBERNETES_NAMESPACE', 'legacy-use')
    
    async def list_containers(self, label_filters: Optional[Dict[str, str]] = None) -> List[ContainerInfo]:
        """List all pods and KubeVirt VMs, optionally filtered by labels."""
        containers = []
        
        try:
            # Build label selector
            label_selector = None
            if label_filters:
                label_parts = [f"{k}={v}" for k, v in label_filters.items()]
                label_selector = ",".join(label_parts)
            
            # List regular pods
            pods = await asyncio.to_thread(
                self.v1.list_namespaced_pod,
                namespace=self.namespace,
                label_selector=label_selector
            )
            
            for pod in pods.items:
                # Skip pods that aren't running
                if pod.status.phase != 'Running':
                    continue
                
                # Skip virt-launcher pods (they're for VMs, handled below)
                if pod.metadata.name.startswith('virt-launcher-'):
                    continue
                
                # Get pod IP
                ip = pod.status.pod_ip
                
                # Get labels
                labels = pod.metadata.labels or {}
                
                # For pods, we don't have port mappings like Docker
                # Services handle the port mapping
                ports = {}
                
                container = ContainerInfo(
                    id=pod.metadata.name,
                    name=pod.metadata.name,
                    labels=labels,
                    status=pod.status.phase,
                    ip=ip,
                    ports=ports
                )
                containers.append(container)
            
        except Exception as e:
            logger.error(f"Failed to list pods: {e}")
        
        # List KubeVirt VirtualMachineInstances
        try:
            vmis = await asyncio.to_thread(
                self.custom_api.list_namespaced_custom_object,
                group="kubevirt.io",
                version="v1",
                namespace=self.namespace,
                plural="virtualmachineinstances",
                label_selector=label_selector
            )
            
            for vmi in vmis.get('items', []):
                # Skip VMIs that aren't running
                if vmi.get('status', {}).get('phase') != 'Running':
                    continue
                
                # Get VMI metadata
                metadata = vmi.get('metadata', {})
                name = metadata.get('name', '')
                labels = metadata.get('labels', {})
                
                # Get IP address
                ip = None
                interfaces = vmi.get('status', {}).get('interfaces', [])
                if interfaces:
                    ip = interfaces[0].get('ipAddress')
                
                # VMIs expose VNC on port 5900
                ports = {'5900': '5900'}
                
                container = ContainerInfo(
                    id=name,
                    name=name,
                    labels=labels,
                    status='Running',  # We already filtered for Running VMIs
                    ip=ip,
                    ports=ports
                )
                containers.append(container)
                
        except Exception as e:
            logger.error(f"Failed to list KubeVirt VMs: {e}")
            
        return containers
    
    async def get_container(self, container_id: str) -> Optional[ContainerInfo]:
        """Get information about a specific pod or KubeVirt VM."""
        # First try to get it as a regular pod
        try:
            pod = await asyncio.to_thread(
                self.v1.read_namespaced_pod,
                name=container_id,
                namespace=self.namespace
            )
            
            # Skip virt-launcher pods
            if pod.metadata.name.startswith('virt-launcher-'):
                return None
            
            return ContainerInfo(
                id=pod.metadata.name,
                name=pod.metadata.name,
                labels=pod.metadata.labels or {},
                status=pod.status.phase,
                ip=pod.status.pod_ip,
                ports={}
            )
            
        except ApiException as e:
            if e.status != 404:
                logger.error(f"Failed to get pod {container_id}: {e}")
        
        # If not found as pod, try as KubeVirt VM
        try:
            vmi = await asyncio.to_thread(
                self.custom_api.get_namespaced_custom_object,
                group="kubevirt.io",
                version="v1",
                namespace=self.namespace,
                plural="virtualmachineinstances",
                name=container_id
            )
            
            # Get IP address
            ip = None
            interfaces = vmi.get('status', {}).get('interfaces', [])
            if interfaces:
                ip = interfaces[0].get('ipAddress')
            
            return ContainerInfo(
                id=vmi['metadata']['name'],
                name=vmi['metadata']['name'],
                labels=vmi['metadata'].get('labels', {}),
                status=vmi.get('status', {}).get('phase', 'Unknown'),
                ip=ip,
                ports={'5900': '5900'}
            )
            
        except ApiException as e:
            if e.status == 404:
                logger.debug(f"Container {container_id} not found as pod or VMI")
            else:
                logger.error(f"Failed to get VMI {container_id}: {e}")
            return None
    
    async def scale_service(self, service_name: str, replicas: int) -> bool:
        """Scale a deployment/statefulset to the specified number of replicas."""
        try:
            # Map service name to deployment name
            deployment_name = None
            for target_type, svc_name in self.SERVICE_MAPPING.items():
                if svc_name == service_name:
                    deployment_name = self.DEPLOYMENT_MAPPING.get(target_type)
                    break
            
            if not deployment_name:
                deployment_name = service_name
            
            # Special handling for Windows VirtualMachineInstanceReplicaSet
            if deployment_name.endswith('-vmirs'):
                return await self._scale_vmirs(deployment_name, replicas)
            
            # Try to scale as deployment first
            try:
                deployment = await asyncio.to_thread(
                    self.apps_v1.read_namespaced_deployment,
                    name=deployment_name,
                    namespace=self.namespace
                )
                
                # Update replicas
                deployment.spec.replicas = replicas
                await asyncio.to_thread(
                    self.apps_v1.patch_namespaced_deployment,
                    name=deployment_name,
                    namespace=self.namespace,
                    body=deployment
                )
                
                logger.info(f"Successfully scaled deployment {deployment_name} to {replicas} replicas")
                return True
                
            except ApiException as e:
                if e.status != 404:
                    raise
                
                # Try as statefulset
                try:
                    statefulset = await asyncio.to_thread(
                        self.apps_v1.read_namespaced_stateful_set,
                        name=deployment_name,
                        namespace=self.namespace
                    )
                    
                    # Update replicas
                    statefulset.spec.replicas = replicas
                    await asyncio.to_thread(
                        self.apps_v1.patch_namespaced_stateful_set,
                        name=deployment_name,
                        namespace=self.namespace,
                        body=statefulset
                    )
                    
                    logger.info(f"Successfully scaled statefulset {deployment_name} to {replicas} replicas")
                    return True
                    
                except ApiException:
                    logger.error(f"Resource {deployment_name} not found as deployment or statefulset")
                    return False
                    
        except Exception as e:
            logger.error(f"Error scaling {service_name}: {e}")
            return False
    
    async def _scale_vmirs(self, vmirs_name: str, replicas: int) -> bool:
        """Scale a VirtualMachineInstanceReplicaSet."""
        try:
            # Get current VMIRS
            vmirs = await asyncio.to_thread(
                self.custom_api.get_namespaced_custom_object,
                group="kubevirt.io",
                version="v1",
                namespace=self.namespace,
                plural="virtualmachineinstancereplicasets",
                name=vmirs_name
            )
            
            # Update replicas
            vmirs['spec']['replicas'] = replicas
            
            # Patch VMIRS
            await asyncio.to_thread(
                self.custom_api.patch_namespaced_custom_object,
                group="kubevirt.io",
                version="v1",
                namespace=self.namespace,
                plural="virtualmachineinstancereplicasets",
                name=vmirs_name,
                body=vmirs
            )
            
            logger.info(f"Successfully scaled VMIRS {vmirs_name} to {replicas} replicas")
            return True
            
        except Exception as e:
            logger.error(f"Error scaling VMIRS {vmirs_name}: {e}")
            return False
    
    async def check_health(self, container_id: str, health_check_url: str) -> bool:
        """Check if a pod is healthy via HTTP endpoint."""
        try:
            pod = await self.get_container(container_id)
            if not pod or not pod.ip:
                return False
            
            # Use pod IP for health check
            url = f"http://{pod.ip}:8088{health_check_url}"
            
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(url)
                return response.status_code == 200
                
        except Exception as e:
            logger.debug(f"Health check failed for {container_id}: {e}")
            return False
    
    def get_service_name_for_target(self, target_type: str) -> str:
        """Get the Kubernetes service name for a given target type."""
        return self.SERVICE_MAPPING.get(target_type, f"legacy-use-{target_type}")
    
    def get_container_url(self, container_info: ContainerInfo, port: int = 8088) -> str:
        """Get the URL to access a container's service."""
        # In Kubernetes, we should use the service name, not pod IP
        # Extract target type from pod name or labels
        target_type = None
        
        # Try to get target type from labels
        if 'legacy-use.target-type' in container_info.labels:
            target_type = container_info.labels['legacy-use.target-type']
        else:
            # Try to infer from pod name
            for t_type, svc_name in self.SERVICE_MAPPING.items():
                if svc_name in container_info.name:
                    target_type = t_type
                    break
        
        if target_type:
            service_name = self.get_service_name_for_target(target_type)
            return f"http://{service_name}.{self.namespace}.svc.cluster.local:{port}"
        else:
            # Fallback to pod IP
            return f"http://{container_info.ip}:{port}"