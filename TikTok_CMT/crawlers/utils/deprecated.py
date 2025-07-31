import warnings
import functools
from crawlers.base_crawler import BaseCrawler
from crawlers.utils.api_exceptions import APIResponseError, APIConnectionError
from crawlers.utils.logger import logger
from typing import Optional, Union, Any
from httpx import Response, HTTPStatusError


def deprecated(message):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            warnings.warn(
                f"{func.__name__} is deprecated: {message}",
                DeprecationWarning,
                stacklevel=2
            )
            return await func(*args, **kwargs)
        return wrapper
    return decorator