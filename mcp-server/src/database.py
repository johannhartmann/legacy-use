"""Database connection and API monitoring."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)


class APIDefinition:
    """Simple API definition model."""
    
    def __init__(self, data: Dict[str, Any]):
        self.id = data["id"]
        self.name = data["name"]
        self.description = data["description"]
        self.is_archived = data.get("is_archived", False)
        self.updated_at = data.get("updated_at")


class APIDefinitionVersion:
    """Simple API definition version model."""
    
    def __init__(self, data: Dict[str, Any]):
        self.id = data["id"]
        self.api_definition_id = data["api_definition_id"]
        self.version_number = data["version_number"]
        self.parameters = data["parameters"]
        self.prompt = data["prompt"]
        self.prompt_cleanup = data.get("prompt_cleanup", "")
        self.response_example = data.get("response_example", {})
        self.is_active = data.get("is_active", False)


class DatabaseMonitor:
    """Monitors the Legacy-Use database for API changes."""
    
    def __init__(self, database_url: str, sync_interval: int = 30):
        self.database_url = database_url
        self.sync_interval = sync_interval
        self.last_check = None
        self._engine = None
        self._session_maker = None
        
    def _init_db(self):
        """Initialize database connection."""
        if not self._engine:
            # Use NullPool to avoid connection pool issues
            self._engine = create_engine(self.database_url, poolclass=NullPool)
            self._session_maker = sessionmaker(bind=self._engine)
    
    def _get_session(self) -> Session:
        """Get a new database session."""
        self._init_db()
        return self._session_maker()
    
    async def get_active_apis(self) -> List[Dict[str, Any]]:
        """Get all active API definitions with their active versions."""
        await asyncio.sleep(0)  # Make it async
        
        session = self._get_session()
        try:
            # Get all non-archived API definitions
            api_query = text("""
                SELECT id, name, description, is_archived, updated_at
                FROM api_definitions
                WHERE is_archived = false
            """)
            
            apis = []
            for row in session.execute(api_query):
                api_data = {
                    "id": str(row.id),
                    "name": row.name,
                    "description": row.description,
                    "is_archived": row.is_archived,
                    "updated_at": row.updated_at,
                }
                
                # Get active version for this API
                version_query = text("""
                    SELECT id, api_definition_id, version_number, parameters,
                           prompt, prompt_cleanup, response_example, is_active
                    FROM api_definition_versions
                    WHERE api_definition_id = :api_id AND is_active = true
                    LIMIT 1
                """)
                
                version_result = session.execute(
                    version_query, {"api_id": row.id}
                ).first()
                
                if version_result:
                    version_data = {
                        "id": str(version_result.id),
                        "api_definition_id": str(version_result.api_definition_id),
                        "version_number": version_result.version_number,
                        "parameters": version_result.parameters or [],
                        "prompt": version_result.prompt,
                        "prompt_cleanup": version_result.prompt_cleanup or "",
                        "response_example": version_result.response_example or {},
                        "is_active": version_result.is_active,
                    }
                    
                    api_data["active_version"] = version_data
                    apis.append(api_data)
                    
            return apis
            
        finally:
            session.close()
    
    async def check_for_changes(self) -> bool:
        """Check if any APIs have changed since last check."""
        await asyncio.sleep(0)  # Make it async
        
        session = self._get_session()
        try:
            # Query for the most recent update time
            query = text("""
                SELECT MAX(updated_at) as last_update
                FROM (
                    SELECT updated_at FROM api_definitions
                    UNION ALL
                    SELECT created_at as updated_at FROM api_definition_versions
                ) as updates
            """)
            
            result = session.execute(query).first()
            if result and result.last_update:
                if self.last_check is None:
                    self.last_check = result.last_update
                    return True  # First check, consider as change
                
                has_changes = result.last_update > self.last_check
                if has_changes:
                    self.last_check = result.last_update
                return has_changes
                
            return False
            
        finally:
            session.close()
    
    async def monitor_changes(self, callback):
        """Monitor for API changes and call callback when detected."""
        logger.info(f"Starting database monitor (sync interval: {self.sync_interval}s)")
        
        while True:
            try:
                if await self.check_for_changes():
                    logger.info("API changes detected, reloading...")
                    apis = await self.get_active_apis()
                    await callback(apis)
                    
            except Exception as e:
                logger.error(f"Error monitoring database: {e}")
                
            await asyncio.sleep(self.sync_interval)