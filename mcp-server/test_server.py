#!/usr/bin/env python3
"""Test script for Legacy-Use MCP server."""

import asyncio
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from src.database import DatabaseMonitor
from src.converter import APIToToolConverter

# Load environment variables
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_database_connection():
    """Test database connection and API retrieval."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL not set")
        return
    
    monitor = DatabaseMonitor(database_url)
    
    # Test getting APIs
    logger.info("Testing database connection...")
    apis = await monitor.get_active_apis()
    logger.info(f"Found {len(apis)} active APIs")
    
    for api in apis:
        logger.info(f"  - {api['name']}: {api['description']}")
        if "active_version" in api:
            version = api["active_version"]
            logger.info(f"    Version: {version['version_number']}")
            logger.info(f"    Parameters: {len(version['parameters'])}")
    
    # Test change detection
    logger.info("\nTesting change detection...")
    has_changes = await monitor.check_for_changes()
    logger.info(f"Initial check - has changes: {has_changes}")
    
    # Second check should show no changes
    await asyncio.sleep(1)
    has_changes = await monitor.check_for_changes()
    logger.info(f"Second check - has changes: {has_changes}")
    
    return apis


async def test_api_conversion(apis):
    """Test API to tool conversion."""
    converter = APIToToolConverter()
    
    logger.info("\nTesting API to tool conversion...")
    tools = converter.convert_apis_to_tools(apis)
    logger.info(f"Converted {len(tools)} tools")
    
    for tool in tools:
        logger.info(f"\nTool: {tool.name}")
        logger.info(f"  Original API: {tool.api_definition_id}")
        logger.info(f"  Description: {tool.description}")
        logger.info(f"  Parameters:")
        for param in tool.parameters:
            logger.info(f"    - {param.name} ({param.type}): {param.description}")
            if param.default is not None:
                logger.info(f"      Default: {param.default}")
        
        # Generate schema
        schema = converter.generate_tool_schema(tool)
        logger.info(f"  Schema: {json.dumps(schema, indent=2)}")


async def main():
    """Run all tests."""
    logger.info("Starting Legacy-Use MCP server tests...\n")
    
    # Test database
    apis = await test_database_connection()
    
    if apis:
        # Test conversion
        await test_api_conversion(apis)
    
    logger.info("\nTests completed!")


if __name__ == "__main__":
    asyncio.run(main())