"""Tests for extension startup and window creation.

This module tests the extension lifecycle at startup: extension startup (TestExtensionStartup)
ensures the extension subscribes and initializes correctly when the app starts; window creation
(TestGraphWindowCreation) ensures the graph window can be opened for a material and that the
async open_graph path completes (including the timeout branch when the widget never appears).
We test these because a failure at startup would prevent the window from appearing or would
leave the extension in a broken state; the window creation test also guards against hangs
in the open_graph loop."""

from .test_extension_startup import TestExtensionStartup  # noqa: F401
from .test_window_creation import TestGraphWindowCreation  # noqa: F401

__all__ = [
    "TestExtensionStartup",
    "TestGraphWindowCreation",
]
