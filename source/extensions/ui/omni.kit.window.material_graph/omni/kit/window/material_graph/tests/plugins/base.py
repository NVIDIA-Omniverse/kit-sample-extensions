import tempfile

from ..base import MaterialGraphTestBase


class PluginTestBase(MaterialGraphTestBase):
    """Base for plugin tests using temporary scratch data."""

    async def setUp(self) -> None:
        """Create a temporary scratch directory."""
        await super().setUp()
        self._temp_dir: tempfile.TemporaryDirectory[str] | None = tempfile.TemporaryDirectory()

    async def tearDown(self) -> None:
        """Clean up the temporary plugin search path."""
        if self._temp_dir:
            self._temp_dir.cleanup()
        self._temp_dir = None
        await super().tearDown()
