"""Client wrapper classes for API compatibility"""
from typing import Any
import httpx


class ContentBlockWrapper:
    """Wrapper for individual content blocks to provide Pydantic model interface"""

    def __init__(self, block_dict: dict):
        self._dict = block_dict

    def model_dump(self):
        """Provide model_dump method expected by _response_to_params"""
        return self._dict

    @property
    def text(self):
        """Provide .text attribute for text blocks"""
        return self._dict.get('text')

    @property
    def type(self):
        """Provide .type attribute"""
        return self._dict.get('type')

    def __getattr__(self, name):
        """Fallback for any other attributes"""
        return self._dict.get(name)


class ResponseWrapper:
    """Wrapper to make dictionary response compatible with BetaMessage interface"""

    def __init__(self, response_dict: dict):
        self._dict = response_dict

    @property
    def content(self):
        """Provide .content attribute access for _response_to_params"""
        content_list = self._dict.get('content', [])
        # Wrap each content block to provide Pydantic model interface
        return [ContentBlockWrapper(block) for block in content_list]

    @property
    def stop_reason(self):
        """Provide .stop_reason attribute access"""
        return self._dict.get('stop_reason')

    def __getattr__(self, name):
        """Fallback for any other attributes"""
        return self._dict.get(name)


class RawResponse:
    """Raw response wrapper for HTTP responses"""

    def __init__(self, parsed_data: Any, http_response: httpx.Response):
        self.parsed_data = parsed_data
        self.http_response = http_response

    def parse(self):
        """Return wrapped response data that provides BetaMessage interface"""
        return ResponseWrapper(self.parsed_data)
