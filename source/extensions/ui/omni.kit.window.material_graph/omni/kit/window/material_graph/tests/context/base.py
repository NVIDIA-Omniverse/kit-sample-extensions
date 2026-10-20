from ...scripts.context_manager.context_manager import ContextManager
from ..base import MaterialGraphTestBase


class ContextManagerTestBase(MaterialGraphTestBase):
    """Base for ContextManager tests with a shared manager."""

    async def setUp(self) -> None:
        """Create a ContextManager for tests."""
        await super().setUp()
        self._manager = ContextManager(self._usd_context)

    async def tearDown(self) -> None:
        """Destroy the ContextManager after tests."""
        if self._manager:
            self._manager.destroy()
        self._manager = None
        await super().tearDown()
