"""Simple MCP server implementation that works with FastMCP limitations."""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP
from pydantic import BaseModel

from .converter import APIToToolConverter, MCPTool
from .database import DatabaseMonitor

logger = logging.getLogger(__name__)


class LegacyUseMCPServer:
    """Simplified MCP server that exposes Legacy-Use APIs as tools."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.sync_interval = int(os.getenv("SYNC_INTERVAL", "30"))
        
        # Initialize components
        self.monitor = DatabaseMonitor(database_url, self.sync_interval)
        self.converter = APIToToolConverter()
        self.mcp = FastMCP("Legacy-Use MCP Server")
        
        # Store current tools
        self.current_tools: Dict[str, MCPTool] = {}
        
        # Legacy-Use backend URL (for executing APIs)
        self.legacy_use_url = os.getenv("LEGACY_USE_URL", "http://localhost:8088")
        self.api_key = os.getenv("LEGACY_USE_API_KEY", "")
        
        # Register static tools
        self._setup_static_tools()
    
    def _setup_static_tools(self):
        """Set up static tools that always exist."""
        
        @self.mcp.tool()
        async def list_legacy_use_apis() -> str:
            """List all available Legacy-Use APIs with their descriptions."""
            if not self.current_tools:
                return "No APIs currently available."
            
            api_list = []
            for tool_name, tool in self.current_tools.items():
                params_info = []
                for param in tool.parameters:
                    param_str = f"{param.name}: {param.type}"
                    if param.default is not None:
                        param_str += f" = {param.default}"
                    if param.required:
                        param_str += " (required)"
                    params_info.append(param_str)
                
                api_list.append(
                    f"- **{tool_name}**: {tool.description}\n"
                    f"  Parameters: {', '.join(params_info) if params_info else 'None'}"
                )
            
            return "Available Legacy-Use APIs:\n" + "\n".join(api_list)
        
        @self.mcp.tool()
        async def execute_legacy_use_api(api_name: str, parameters: str = "{}") -> Dict[str, Any]:
            """Execute a Legacy-Use API by name with JSON parameters.
            
            Args:
                api_name: Name of the API to execute (use list_legacy_use_apis to see available APIs)
                parameters: JSON string containing the API parameters (default: "{}")
            
            Returns:
                API execution result
            """
            # Parse parameters
            try:
                params = json.loads(parameters) if parameters else {}
            except json.JSONDecodeError as e:
                return {
                    "status": "error",
                    "error": f"Invalid JSON parameters: {str(e)}"
                }
            
            # Find the tool
            tool = self.current_tools.get(api_name)
            if not tool:
                return {
                    "status": "error",
                    "error": f"API '{api_name}' not found. Use list_legacy_use_apis to see available APIs."
                }
            
            # Validate parameters
            for param in tool.parameters:
                if param.required and param.name not in params:
                    return {
                        "status": "error",
                        "error": f"Missing required parameter: {param.name}"
                    }
            
            # Execute the API
            return await self._execute_api(tool, params)
    
    async def _reload_tools(self, apis: List[Dict[str, Any]]):
        """Reload tools based on current API definitions."""
        # Convert APIs to tools
        tools = self.converter.convert_apis_to_tools(apis)
        
        # Update current tools
        self.current_tools.clear()
        for tool in tools:
            self.current_tools[tool.name] = tool
        
        logger.info(f"Loaded {len(self.current_tools)} API definitions")
    
    async def _execute_api(self, tool: MCPTool, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a Legacy-Use API call."""
        try:
            # Build the prompt with parameters
            prompt = tool.prompt_template
            for param_name, param_value in parameters.items():
                placeholder = f"{{{{{param_name}}}}}"
                prompt = prompt.replace(placeholder, str(param_value))
            
            # For remaining placeholders, use defaults
            for param in tool.parameters:
                if param.name not in parameters and param.default is not None:
                    placeholder = f"{{{{{param.name}}}}}"
                    prompt = prompt.replace(placeholder, str(param.default))
            
            logger.info(f"Executing API '{tool.name}' with parameters: {parameters}")
            
            # Return mock response for now
            return {
                "status": "success",
                "api": tool.name,
                "parameters": parameters,
                "response": tool.response_example,
                "note": "This is a mock response. Real implementation would execute via Legacy-Use backend."
            }
            
        except Exception as e:
            logger.error(f"Error executing API '{tool.name}': {e}")
            return {
                "status": "error",
                "error": str(e),
                "api": tool.name,
                "parameters": parameters,
            }
    
    async def run(self):
        """Run the MCP server."""
        # Load initial tools
        logger.info("Loading initial API definitions...")
        apis = await self.monitor.get_active_apis()
        await self._reload_tools(apis)
        
        # Start monitoring task
        monitor_task = asyncio.create_task(
            self.monitor.monitor_changes(self._reload_tools)
        )
        
        try:
            # Run the MCP server with HTTP streaming transport
            logger.info("Starting MCP server with HTTP streaming...")
            host = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
            port = int(os.getenv("MCP_SERVER_PORT", "3000"))
            path = os.getenv("MCP_SERVER_PATH", "/mcp")
            
            # Use HTTP streaming transport instead of STDIO
            await self.mcp.run_async(
                transport="http",
                host=host,
                port=port,
                path=path
            )
            
        finally:
            # Cancel monitor task
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass