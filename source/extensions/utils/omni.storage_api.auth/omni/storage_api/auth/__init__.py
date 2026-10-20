"""
USD Storage API Authentication Extension

This extension acts as an intermediate layer between the Client Library and Web Portal,
communicating authentication events and messages through the streaming data channel.
"""

from .auth_handler import AuthPortalError, StorageAuthHandler
from .extension import StorageAuthExtension, get_instance

__all__ = [
    "AuthPortalError",
    "StorageAuthHandler",
    "StorageAuthExtension",
    "get_instance",
]
