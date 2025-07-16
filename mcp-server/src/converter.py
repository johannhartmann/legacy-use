"""Converts Legacy-Use API definitions to MCP tools."""

import json
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MCPToolParameter(BaseModel):
    """MCP tool parameter definition."""
    
    name: str
    type: str
    description: str
    required: bool = False
    default: Optional[Any] = None


class MCPTool(BaseModel):
    """MCP tool definition."""
    
    name: str
    description: str
    parameters: List[MCPToolParameter]
    api_definition_id: str
    version_id: str
    version_number: str
    prompt_template: str
    prompt_cleanup: str
    response_example: Dict[str, Any]


class APIToToolConverter:
    """Converts Legacy-Use API definitions to MCP tools."""
    
    @staticmethod
    def convert_parameter_type(param_type: str) -> str:
        """Convert Legacy-Use parameter type to MCP/JSON schema type."""
        type_mapping = {
            "string": "string",
            "integer": "number",
            "float": "number",
            "boolean": "boolean",
            "object": "object",
            "array": "array",
        }
        return type_mapping.get(param_type.lower(), "string")
    
    @staticmethod
    def sanitize_tool_name(api_name: str) -> str:
        """Convert API name to valid MCP tool name."""
        # Replace spaces and special characters with underscores
        # Keep only alphanumeric and underscores
        import re
        name = re.sub(r'[^a-zA-Z0-9_]', '_', api_name)
        # Remove consecutive underscores
        name = re.sub(r'_+', '_', name)
        # Remove leading/trailing underscores
        name = name.strip('_')
        # Ensure it starts with a letter
        if name and name[0].isdigit():
            name = f"api_{name}"
        return name or "unnamed_api"
    
    def convert_api_to_tool(self, api_data: Dict[str, Any]) -> Optional[MCPTool]:
        """Convert a Legacy-Use API definition to an MCP tool."""
        try:
            if "active_version" not in api_data:
                logger.warning(f"API '{api_data['name']}' has no active version")
                return None
            
            version = api_data["active_version"]
            
            # Convert parameters
            mcp_params = []
            for param in version["parameters"]:
                mcp_param = MCPToolParameter(
                    name=param["name"],
                    type=self.convert_parameter_type(param.get("type", "string")),
                    description=param.get("description", ""),
                    required=param.get("required", False),
                    default=param.get("default"),
                )
                mcp_params.append(mcp_param)
            
            # Create tool
            tool = MCPTool(
                name=self.sanitize_tool_name(api_data["name"]),
                description=api_data["description"],
                parameters=mcp_params,
                api_definition_id=api_data["id"],
                version_id=version["id"],
                version_number=version["version_number"],
                prompt_template=version["prompt"],
                prompt_cleanup=version["prompt_cleanup"],
                response_example=version["response_example"],
            )
            
            return tool
            
        except Exception as e:
            logger.error(f"Error converting API '{api_data.get('name')}': {e}")
            return None
    
    def convert_apis_to_tools(self, apis: List[Dict[str, Any]]) -> List[MCPTool]:
        """Convert multiple API definitions to MCP tools."""
        tools = []
        for api_data in apis:
            tool = self.convert_api_to_tool(api_data)
            if tool:
                tools.append(tool)
        
        logger.info(f"Converted {len(tools)} APIs to MCP tools")
        return tools
    
    def generate_tool_schema(self, tool: MCPTool) -> Dict[str, Any]:
        """Generate JSON schema for tool parameters."""
        properties = {}
        required = []
        
        for param in tool.parameters:
            param_schema = {
                "type": param.type,
                "description": param.description,
            }
            
            if param.default is not None:
                param_schema["default"] = param.default
            
            properties[param.name] = param_schema
            
            if param.required:
                required.append(param.name)
        
        schema = {
            "type": "object",
            "properties": properties,
        }
        
        if required:
            schema["required"] = required
        
        return schema