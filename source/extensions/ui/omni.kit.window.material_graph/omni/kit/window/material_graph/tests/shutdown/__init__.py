"""Tests for extension shutdown and teardown.

This module tests that the extension shuts down cleanly when the app or window is closed
(TestExtensionShutdown): subscriptions are removed, resources are released, and no callbacks
or references remain that could cause errors or leaks after shutdown. We test this because
improper teardown can lead to crashes on exit or when reopening the window, and because
the extension may hold USD or UI references that must be cleared."""

from .test_extension_shutdown import TestExtensionShutdown  # noqa: F401

__all__ = [
    "TestExtensionShutdown",
]
