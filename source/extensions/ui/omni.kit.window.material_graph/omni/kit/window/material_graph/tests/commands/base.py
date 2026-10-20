from typing import Callable

import omni.kit.undo

from ..base import MaterialGraphTestBase


class CommandsTestBase(MaterialGraphTestBase):
    """Base for command tests with undo/redo helpers."""

    async def setUp(self) -> None:
        """Reset the undo stack for each command test."""
        await super().setUp()
        omni.kit.undo.clear_stack()

    async def _assert_undo_redo(self, verify_before: Callable[[], None], verify_after: Callable[[], None]) -> None:
        """Assert undo/redo behavior between two verification callbacks."""
        verify_after()
        self.assertTrue(omni.kit.undo.undo())
        await self._app.next_update_async()
        verify_before()
        self.assertTrue(omni.kit.undo.redo())
        await self._app.next_update_async()
        verify_after()
