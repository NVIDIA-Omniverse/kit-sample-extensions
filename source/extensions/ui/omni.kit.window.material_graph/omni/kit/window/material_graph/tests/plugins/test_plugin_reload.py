import asyncio

from ...scripts.plugins.core import Plugin
from ..base import MaterialGraphTestBase


class DummyPlugin(Plugin):
    """Plugin stub for reload tests."""

    def __init__(self, load_catalog: bool = True) -> None:
        """Initialize the dummy plugin."""
        super().__init__("dummy", "Dummy", None, load_catalog=load_catalog)

    def build_catalog_items(self) -> None:
        """Clear catalog items without building."""
        self._catalog_items.clear()

    def is_supported_prim(self, _prim: object) -> bool:
        """Return False for all prims."""
        return False


class TestPluginReload(MaterialGraphTestBase):
    """Plugin reload state coverage."""

    async def test_reload_during_async_build_sets_pending(self) -> None:
        """reload should not run concurrently with an active catalog task."""
        plugin = DummyPlugin(load_catalog=False)
        pending = asyncio.Future()
        plugin._catalog_task = pending
        plugin._catalog_reload_pending = False

        plugin.reload()

        self.assertTrue(plugin._catalog_reload_pending)
        pending.cancel()
