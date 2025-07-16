"""Execute Legacy-Use APIs via the backend."""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

import httpx

from .converter import MCPTool

logger = logging.getLogger(__name__)


class APIExecutor:
    """Handles execution of Legacy-Use APIs via the backend."""
    
    def __init__(self, backend_url: str, api_key: str):
        self.backend_url = backend_url.rstrip('/')
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
            headers={"X-API-Key": api_key} if api_key else {}
        )
    
    async def execute_api(
        self,
        tool: MCPTool,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a Legacy-Use API and return the result."""
        try:
            # Step 1: Create a job
            job_data = {
                "api_name": tool.name,
                "parameters": parameters,
                "target_id": None,  # TODO: Get from configuration or tool metadata
                "session_id": None,  # TODO: Session management
            }
            
            # Create job endpoint
            create_url = f"{self.backend_url}/api/jobs"
            response = await self.client.post(create_url, json=job_data)
            
            if response.status_code != 200:
                return {
                    "status": "error",
                    "error": f"Failed to create job: {response.status_code}",
                    "details": response.text
                }
            
            job = response.json()
            job_id = job["id"]
            
            # Step 2: Poll for job completion
            poll_url = f"{self.backend_url}/api/jobs/{job_id}"
            max_polls = 60  # 5 minutes with 5-second intervals
            poll_interval = 5
            
            for _ in range(max_polls):
                await asyncio.sleep(poll_interval)
                
                response = await self.client.get(poll_url)
                if response.status_code != 200:
                    continue
                
                job_status = response.json()
                status = job_status.get("status", "pending")
                
                if status == "completed":
                    return {
                        "status": "success",
                        "result": job_status.get("result", {}),
                        "job_id": job_id
                    }
                elif status in ["failed", "error"]:
                    return {
                        "status": "error",
                        "error": job_status.get("error", "Job failed"),
                        "job_id": job_id
                    }
            
            # Timeout
            return {
                "status": "error",
                "error": "Job execution timed out",
                "job_id": job_id
            }
            
        except httpx.RequestError as e:
            logger.error(f"HTTP request error: {e}")
            return {
                "status": "error",
                "error": f"Request failed: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error executing API: {e}")
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}"
            }
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Example of how to integrate this with the MCP server:
"""
# In server.py, modify the __init__ method:

def __init__(self, database_url: str):
    # ... existing code ...
    
    # Initialize API executor if credentials are available
    if self.legacy_use_url and self.api_key:
        self.executor = APIExecutor(self.legacy_use_url, self.api_key)
    else:
        self.executor = None
        logger.warning("API execution disabled - missing LEGACY_USE_URL or LEGACY_USE_API_KEY")

# In _execute_api method:

async def _execute_api(self, tool: MCPTool, parameters: Dict[str, Any]) -> Dict[str, Any]:
    if self.executor:
        return await self.executor.execute_api(tool, parameters)
    else:
        # Return mock response as before
        return {
            "status": "error",
            "error": "API execution not configured",
            "note": "Set LEGACY_USE_URL and LEGACY_USE_API_KEY to enable real execution"
        }
"""