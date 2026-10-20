"""Reusable context-manager stubs for controller tests."""

from unittest.mock import MagicMock


class DummyContextManager:
    """Context manager stub that returns a fixed node from get_node."""

    def __init__(self, node: object | None = None) -> None:
        self._node = node

    def get_node(self, _context: str, _identifier: str) -> object | None:
        return self._node


class DropHandlerContextManager:
    """Context manager stub for path/texture drop handlers (get_context, get_node)."""

    def __init__(self, plugin=None) -> None:
        self._plugin = plugin

    def get_context(self, _name: str):
        return MagicMock(plugin=self._plugin)

    def get_node(self, _context: str, _identifier: str):
        return None
