"""Lifecycle helper for node-creation drop handlers."""

from ....config.logging import logger


class HandlerRegistry:
    """Track drop handlers for consistent destruction."""

    def __init__(self) -> None:
        """Initialize ordered storage for owned handler instances."""
        self._handlers = []

    def add(self, handler: object) -> object:
        """Register a handler and return it."""
        self._handlers.append(handler)
        return handler

    def destroy(self) -> None:
        """Destroy all registered handlers."""
        for handler in self._handlers:
            try:
                handler.destroy()
            except AttributeError as exc:
                # Handlers that do not implement destroy are tolerated.
                logger.debug("handler destroy skipped: %s", exc)
        self._handlers = []
