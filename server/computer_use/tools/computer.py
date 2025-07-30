import asyncio
import logging
from typing import Literal, cast

from anthropic.types.beta import BetaToolComputerUse20241022Param, BetaToolUnionParam

from server.database import db

from .base import BaseAnthropicTool, ToolError, ToolResult
from .vnc_client import vnc_pool

Action_20241022 = Literal[
    'key',
    'type',
    'mouse_move',
    'left_click',
    'left_click_drag',
    'right_click',
    'middle_click',
    'double_click',
    'screenshot',
    'cursor_position',
]

Action_20250124 = (
    Action_20241022
    | Literal[
        'left_mouse_down',
        'left_mouse_up',
        'scroll',
        'hold_key',
        'wait',
        'triple_click',
    ]
)

ScrollDirection = Literal['up', 'down', 'left', 'right']


class BaseComputerTool(BaseAnthropicTool):
    """
    A tool that allows the agent to interact with the screen, keyboard, and mouse of a remote computer.
    All actions are performed via VNC connection to the target container.
    """

    name: Literal['computer'] = 'computer'
    width: int = 1024  # Default width
    height: int = 768  # Default height
    display_num: int = 1  # Default display number

    @property
    def options(self):
        return {
            'display_width_px': self.width,
            'display_height_px': self.height,
            'display_number': self.display_num,
        }

    def to_params(self) -> BetaToolComputerUse20241022Param:
        return {'name': self.name, 'type': self.api_type, **self.options}

    async def __call__(
        self,
        *,
        session_id: str,
        action: Action_20241022,
        text: str | None = None,
        coordinate: tuple[int, int] | None = None,
        **kwargs,
    ):
        return await self._perform_vnc_action(
            session_id, action, text, coordinate, **kwargs
        )

    async def _perform_vnc_action(
        self,
        session_id: str,
        action: Action_20241022 | Action_20250124,
        text: str | None = None,
        coordinate: tuple[int, int] | None = None,
        scroll_direction: ScrollDirection | None = None,
        scroll_amount: int | None = None,
        duration: int | float | None = None,
        key: str | None = None,
        **kwargs,
    ):
        """Perform the action via VNC connection."""
        logger = logging.getLogger(__name__)

        # Check for cancellation
        await asyncio.sleep(0)

        # Get the session information
        session = db.get_session(session_id)
        if not session:
            raise ToolError(f'Session {session_id} not found')

        # Get the container IP and VNC port
        container_ip = session.get('container_ip')
        if not container_ip:
            raise ToolError(f'Container IP not found for session {session_id}')
        
        vnc_port = int(session.get('vnc_port', 5900))
        
        # TODO: Get VNC password from session if needed
        vnc_password = session.get('vnc_password')

        try:
            # Get VNC connection from pool
            async with vnc_pool.get_connection(container_ip, vnc_port, vnc_password) as vnc:
                # Perform the requested action
                if action == 'screenshot':
                    base64_image = await vnc.screenshot()
                    return ToolResult(
                        output="Screenshot taken successfully",
                        base64_image=base64_image
                    )
                
                elif action == 'mouse_move':
                    if not coordinate:
                        raise ToolError("Coordinate required for mouse_move")
                    await vnc.move_mouse(coordinate[0], coordinate[1])
                    return ToolResult(output=f"Mouse moved to {coordinate}")
                
                elif action == 'left_click':
                    if coordinate:
                        await vnc.move_mouse(coordinate[0], coordinate[1])
                    await vnc.click(1)
                    return ToolResult(output="Left click performed")
                
                elif action == 'right_click':
                    if coordinate:
                        await vnc.move_mouse(coordinate[0], coordinate[1])
                    await vnc.click(3)
                    return ToolResult(output="Right click performed")
                
                elif action == 'middle_click':
                    if coordinate:
                        await vnc.move_mouse(coordinate[0], coordinate[1])
                    await vnc.click(2)
                    return ToolResult(output="Middle click performed")
                
                elif action == 'double_click':
                    if coordinate:
                        await vnc.move_mouse(coordinate[0], coordinate[1])
                    await vnc.click(1)
                    await asyncio.sleep(0.1)
                    await vnc.click(1)
                    return ToolResult(output="Double click performed")
                
                elif action == 'triple_click':
                    if coordinate:
                        await vnc.move_mouse(coordinate[0], coordinate[1])
                    for _ in range(3):
                        await vnc.click(1)
                        await asyncio.sleep(0.1)
                    return ToolResult(output="Triple click performed")
                
                elif action == 'left_click_drag':
                    if not coordinate:
                        raise ToolError("Coordinate required for left_click_drag")
                    await vnc.drag(coordinate[0], coordinate[1], 1)
                    return ToolResult(output=f"Dragged to {coordinate}")
                
                elif action == 'left_mouse_down':
                    if coordinate:
                        await vnc.move_mouse(coordinate[0], coordinate[1])
                    await vnc.mouse_down(1)
                    return ToolResult(output="Left mouse button pressed down")
                
                elif action == 'left_mouse_up':
                    if coordinate:
                        await vnc.move_mouse(coordinate[0], coordinate[1])
                    await vnc.mouse_up(1)
                    return ToolResult(output="Left mouse button released")
                
                elif action == 'type':
                    if not text:
                        raise ToolError("Text required for type action")
                    await vnc.type_text(text)
                    return ToolResult(output=f"Typed: {text}")
                
                elif action == 'key':
                    if key:
                        # Use the key parameter if provided
                        await vnc.key_press(key)
                        return ToolResult(output=f"Key pressed: {key}")
                    elif text:
                        # Fall back to text parameter for backward compatibility
                        await vnc.key_press(text)
                        return ToolResult(output=f"Key pressed: {text}")
                    else:
                        raise ToolError("Key or text required for key action")
                
                elif action == 'hold_key':
                    if key:
                        # For hold_key, we'll press and release after duration
                        await vnc.key_press(key)
                        if duration:
                            await asyncio.sleep(duration)
                        return ToolResult(output=f"Key held: {key}")
                    else:
                        raise ToolError("Key required for hold_key action")
                
                elif action == 'scroll':
                    if not scroll_direction:
                        raise ToolError("Scroll direction required for scroll action")
                    amount = scroll_amount or 5
                    await vnc.scroll(scroll_direction, amount)
                    return ToolResult(output=f"Scrolled {scroll_direction} by {amount}")
                
                elif action == 'cursor_position':
                    position = await vnc.get_cursor_position()
                    return ToolResult(output=f"Cursor position: {position}")
                
                elif action == 'wait':
                    wait_time = duration or 1.0
                    await asyncio.sleep(wait_time)
                    return ToolResult(output=f"Waited for {wait_time} seconds")
                
                else:
                    raise ToolError(f"Unknown action: {action}")

        except asyncio.CancelledError:
            raise
        except ToolError:
            raise
        except Exception as e:
            logger.error(f'VNC action {action} failed: {str(e)}')
            raise ToolError(f'VNC action failed: {str(e)}') from e


class ComputerTool20241022(BaseComputerTool, BaseAnthropicTool):
    api_type: Literal['computer_20241022'] = 'computer_20241022'

    def to_params(self) -> BetaToolComputerUse20241022Param:
        return {'name': self.name, 'type': self.api_type, **self.options}


class ComputerTool20250124(BaseComputerTool, BaseAnthropicTool):
    api_type: Literal['computer_20250124'] = 'computer_20250124'

    def to_params(self):
        return cast(
            BetaToolUnionParam,
            {'name': self.name, 'type': self.api_type, **self.options},
        )

    async def __call__(
        self,
        *,
        session_id: str,
        action: Action_20250124,
        text: str | None = None,
        coordinate: tuple[int, int] | None = None,
        scroll_direction: ScrollDirection | None = None,
        scroll_amount: int | None = None,
        duration: int | float | None = None,
        key: str | None = None,
        **kwargs,
    ):
        return await self._perform_vnc_action(
            session_id=session_id,
            action=action,
            text=text,
            coordinate=coordinate,
            scroll_direction=scroll_direction,
            scroll_amount=scroll_amount,
            duration=duration,
            key=key,
            **kwargs,
        )