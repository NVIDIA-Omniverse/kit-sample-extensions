# pylint: disable=relative-beyond-top-level
from ...scripts import api as api_module
from ..base import MaterialGraphTestBase


class TestApiInit(MaterialGraphTestBase):
    """API package exports the supported context-menu registration surface."""

    async def test_all_exports_exist(self) -> None:
        """All declared exports exist on the api module."""
        for name in api_module.__all__:
            self.assertTrue(hasattr(api_module, name), f"api export missing: {name}")

    async def test_exports_match_supported_surface(self) -> None:
        """Only the supported public API functions are exported."""
        self.assertEqual(
            set(api_module.__all__),
            {
                "add_background_menu_item",
                "add_node_menu_item",
                "remove_background_menu_item",
                "remove_node_menu_item",
            },
        )
