"""
VNC client implementation for computer tools.
"""

import asyncio
import base64
import io
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional, Tuple

from PIL import Image
from vncdotool import api

logger = logging.getLogger(__name__)


class VNCClient:
    """Wrapper around vncdotool for async operations."""
    
    def __init__(self, host: str, port: int = 5900, password: Optional[str] = None):
        self.host = host
        self.port = port
        self.password = password
        self._client = None
        self._lock = asyncio.Lock()
    
    async def connect(self):
        """Connect to VNC server."""
        async with self._lock:
            if self._client is None:
                loop = asyncio.get_event_loop()
                # vncdotool is synchronous, so we run it in an executor
                self._client = await loop.run_in_executor(
                    None,
                    api.connect,
                    f"{self.host}::{self.port}",
                    self.password
                )
                logger.info(f"Connected to VNC server at {self.host}:{self.port}")
    
    async def disconnect(self):
        """Disconnect from VNC server."""
        async with self._lock:
            if self._client:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._client.disconnect)
                self._client = None
                logger.info(f"Disconnected from VNC server at {self.host}:{self.port}")
    
    async def ensure_connected(self):
        """Ensure we're connected to the VNC server."""
        if self._client is None:
            await self.connect()
    
    async def screenshot(self) -> str:
        """Take a screenshot and return as base64 encoded PNG."""
        await self.ensure_connected()
        loop = asyncio.get_event_loop()
        
        # Capture screenshot to a temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # vncdotool saves screenshot to file
            await loop.run_in_executor(None, self._client.captureScreen, tmp_path)
            
            # Read and encode the image
            with open(tmp_path, 'rb') as f:
                image_data = f.read()
            
            # Convert to base64
            base64_image = base64.b64encode(image_data).decode('utf-8')
            return base64_image
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    async def move_mouse(self, x: int, y: int):
        """Move mouse to absolute coordinates."""
        await self.ensure_connected()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._client.mouseMove, x, y)
    
    async def click(self, button: int = 1):
        """Click mouse button (1=left, 2=middle, 3=right)."""
        await self.ensure_connected()
        loop = asyncio.get_event_loop()
        # A click is a press followed by a release
        await loop.run_in_executor(None, self._client.mouseDown, button)
        await asyncio.sleep(0.05)  # Small delay between press and release
        await loop.run_in_executor(None, self._client.mouseUp, button)
    
    async def mouse_down(self, button: int = 1):
        """Press mouse button down."""
        await self.ensure_connected()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._client.mouseDown, button)
    
    async def mouse_up(self, button: int = 1):
        """Release mouse button."""
        await self.ensure_connected()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._client.mouseUp, button)
    
    async def drag(self, x: int, y: int, button: int = 1):
        """Drag mouse to coordinates."""
        await self.ensure_connected()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._client.mouseDrag, x, y, button)
    
    async def type_text(self, text: str):
        """Type text."""
        await self.ensure_connected()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._client.type, text)
    
    async def key_press(self, key: str):
        """Press a special key."""
        await self.ensure_connected()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._client.keyPress, key)
    
    async def scroll(self, direction: str, amount: int = 5):
        """Scroll in a direction."""
        await self.ensure_connected()
        loop = asyncio.get_event_loop()
        
        # Map direction to scroll button
        scroll_map = {
            'up': 4,
            'down': 5,
            'left': 6,
            'right': 7
        }
        button = scroll_map.get(direction, 5)
        
        # Send multiple scroll events
        for _ in range(amount):
            await loop.run_in_executor(None, self._client.mousePress, button)
            await asyncio.sleep(0.01)  # Small delay between scrolls
    
    async def get_cursor_position(self) -> Tuple[int, int]:
        """Get current cursor position."""
        # vncdotool doesn't provide cursor position directly
        # We'll need to track it ourselves or use a workaround
        # For now, return a default position
        logger.warning("Cursor position tracking not implemented, returning (0, 0)")
        return (0, 0)


# Connection pool for VNC clients
class VNCConnectionPool:
    """Manage VNC connections to different containers."""
    
    def __init__(self):
        self._connections = {}
        self._lock = asyncio.Lock()
    
    @asynccontextmanager
    async def get_connection(self, host: str, port: int = 5900, password: Optional[str] = None):
        """Get or create a VNC connection."""
        key = f"{host}:{port}"
        
        async with self._lock:
            if key not in self._connections:
                client = VNCClient(host, port, password)
                await client.connect()
                self._connections[key] = client
            
            client = self._connections[key]
        
        try:
            yield client
        except Exception as e:
            logger.error(f"Error using VNC connection to {key}: {e}")
            # Remove failed connection from pool
            async with self._lock:
                if key in self._connections:
                    await self._connections[key].disconnect()
                    del self._connections[key]
            raise
    
    async def close_all(self):
        """Close all connections."""
        async with self._lock:
            for client in self._connections.values():
                await client.disconnect()
            self._connections.clear()


# Global connection pool
vnc_pool = VNCConnectionPool()