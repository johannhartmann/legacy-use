"""Main entry point for the Legacy-Use MCP server."""

import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .simple_server import LegacyUseMCPServer

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point."""
    try:
        # Get database URL
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logger.error("DATABASE_URL environment variable not set")
            sys.exit(1)
        
        # Create and run server
        server = LegacyUseMCPServer(database_url)
        logger.info("Starting Legacy-Use MCP server...")
        await server.run()
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())