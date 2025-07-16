"""Main MCP server implementation for Legacy-Use."""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from fastmcp import FastMCP

from .converter import APIToToolConverter, MCPTool
from .database import DatabaseMonitor

logger = logging.getLogger(__name__)


class LegacyUseMCPServer:
    """MCP server that exposes Legacy-Use APIs as tools."""
    
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
        
        # Initialize server info
        self._setup_server_info()
    
    def _setup_server_info(self):
        """Set up server information."""
        @self.mcp.tool()
        async def list_legacy_use_apis() -> str:
            """List all available Legacy-Use APIs with their descriptions."""
            if not self.current_tools:
                return "No APIs currently available."
            
            api_list = []
            for tool_name, tool in self.current_tools.items():
                api_list.append(f"- **{tool_name}**: {tool.description}")
            
            return "Available Legacy-Use APIs:\n" + "\n".join(api_list)
    
    async def _reload_tools(self, apis: List[Dict[str, Any]]):
        """Reload tools based on current API definitions."""
        # Convert APIs to tools
        tools = self.converter.convert_apis_to_tools(apis)
        
        # Clear existing dynamic tools
        # Note: FastMCP doesn't have a direct way to remove tools,
        # so we'll track them and handle appropriately
        self.current_tools.clear()
        
        # Register new tools
        for tool in tools:
            self._register_tool(tool)
            self.current_tools[tool.name] = tool
        
        logger.info(f"Loaded {len(self.current_tools)} tools")
    
    def _register_tool(self, tool: MCPTool):
        """Register a single tool with the MCP server."""
        # Create a function with explicit parameters based on the tool schema
        param_names = [p.name for p in tool.parameters]
        
        # Create function code dynamically to avoid **kwargs
        func_params = []
        for param in tool.parameters:
            if param.default is not None:
                func_params.append(f"{param.name}={repr(param.default)}")
            else:
                func_params.append(param.name)
        
        func_signature = f"async def {tool.name}({', '.join(func_params)}) -> Dict[str, Any]:"
        
        # Create the function body
        func_body = f'''
{func_signature}
    """Execute Legacy-Use API: {tool.description}
    
Parameters:
{self._format_parameters_doc(tool.parameters)}

Returns:
    API response as defined in the API definition.
"""
    # Collect parameters into a dict
    params = {{}}
'''
        
        # Add parameter collection
        for param in tool.parameters:
            func_body += f"    if {param.name} is not None:\n"
            func_body += f"        params['{param.name}'] = {param.name}\n"
        
        func_body += f"    return await _execute_api_wrapper('{tool.name}', params)\n"
        
        # Create a wrapper function that can be referenced
        async def _execute_api_wrapper(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
            # Find the tool by name
            target_tool = self.current_tools.get(tool_name)
            if target_tool:
                return await self._execute_api(target_tool, params)
            return {"status": "error", "error": f"Tool {tool_name} not found"}
        
        # Store the wrapper in instance
        self._execute_api_wrapper = _execute_api_wrapper
        
        # Execute the function definition
        local_vars = {'Dict': Dict, 'Any': Any, '_execute_api_wrapper': _execute_api_wrapper}
        exec(func_body, local_vars)
        tool_function = local_vars[tool.name]
        
        # Register with FastMCP
        self.mcp.tool(name=tool.name)(tool_function)
    
    def _format_parameters_doc(self, parameters) -> str:
        """Format parameters for documentation."""
        if not parameters:
            return "    None"
        
        lines = []
        for param in parameters:
            req = " (required)" if param.required else ""
            default = f" [default: {param.default}]" if param.default is not None else ""
            lines.append(f"    - {param.name}: {param.description}{req}{default}")
        
        return "\n".join(lines)
    
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
            
            # Call Legacy-Use API
            # Note: This is a simplified version. In production, you'd need to:
            # 1. Create a job in the Legacy-Use system
            # 2. Poll for job completion
            # 3. Return the results
            
            logger.info(f"Executing API '{tool.name}' with parameters: {parameters}")
            
            # TODO: Implement actual Legacy-Use API execution
            # For now, return a mock response
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
            # Run the MCP server
            logger.info("Starting MCP server...")
            await self.mcp.run()
            
        finally:
            # Cancel monitor task
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass