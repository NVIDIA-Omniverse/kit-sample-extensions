# pylint: disable=relative-beyond-top-level,no-member,protected-access
import json
import tempfile
from pathlib import Path
from typing import Callable, Optional
from unittest.mock import patch

import carb.settings
from pxr import Usd, UsdShade

from ...scripts.models.catalog import tree as model_module
from ...scripts.models.catalog.items import GroupItem
from ...scripts.models.catalog.registries.compound import get_compound_registry
from ...scripts.models.catalog.registries.texture import get_texture_registry
from ...scripts.models.catalog.tree import CatalogTreeModel
from ...scripts.settings import utils
from ...scripts.settings.settings import Settings
from ..base import MaterialGraphTestBase


class _FakePlugin:
    """Plugin stub that supplies catalog items."""

    def __init__(self, items: list[GroupItem]) -> None:
        """Initialize with the catalog items to return."""
        self._items = items
        self.name = "fake"
        self._reload_cb = None

    def set_reload_callback(self, cb: Callable[[], None]) -> None:
        """Store the reload callback."""
        self._reload_cb = cb

    def get_catalog_items(self) -> list[GroupItem]:
        """Return the catalog items."""
        return self._items

    def reload(self) -> None:
        """Invoke the reload callback when present."""
        if self._reload_cb:
            self._reload_cb()


class _FailPlugin(_FakePlugin):
    """Plugin stub that raises when catalog items are requested."""

    def get_catalog_items(self) -> list[GroupItem]:
        """Raise an error to simulate a plugin failure."""
        raise RuntimeError("boom")


class TestCatalogBuild(MaterialGraphTestBase):
    """Catalog build and reload behavior."""

    async def setUp(self) -> None:
        """Create a temporary compound directory."""
        await super().setUp()
        self._compound_dir: Optional[tempfile.TemporaryDirectory[str]] = tempfile.TemporaryDirectory()
        Settings.set_compound_paths([self._compound_dir.name])

    async def tearDown(self) -> None:
        """Clean up the temporary compound directory."""
        try:
            if self._compound_dir:
                self._compound_dir.cleanup()
        finally:
            self._compound_dir = None
            await super().tearDown()

    async def test_clear_on_none_plugin(self) -> None:
        """Setting discovery plugin to None should clear the catalog."""
        model = CatalogTreeModel()
        plugin = _FakePlugin([GroupItem("GroupA")])
        model.set_discovery_plugin(plugin)
        model._on_plugin_reload()
        self.assertTrue(model.children)
        model.set_discovery_plugin(None)
        self.assertEqual(model.children, [])

    async def test_catalog_appends_miscellaneous_items(self) -> None:
        """Catalog should append miscellaneous items after plugin items."""
        model = CatalogTreeModel()
        plugin = _FakePlugin([GroupItem("GroupA")])
        model.set_discovery_plugin(plugin)
        model._on_plugin_reload()
        names = [child.name for child in model.children]
        self.assertIn("GroupA", names)
        self.assertIn("Miscellaneous", names)

    async def test_catalog_handles_plugin_failure(self) -> None:
        """Catalog should handle plugin failures by clearing children."""
        model = CatalogTreeModel()
        plugin = _FailPlugin([])
        model.set_discovery_plugin(plugin)
        model._on_plugin_reload()
        self.assertEqual(model.children, [])

    async def test_catalog_deduplicates_unchanged_discovery_failure_until_recovery(self) -> None:
        """Repeated refresh triggers should log one failure and log again only after a recovery transition."""
        model = CatalogTreeModel()
        failing_plugin = _FailPlugin([])
        model._discovery_plugin = failing_plugin
        with patch.object(model_module.logger, "warning") as warning:
            model._on_plugin_reload()
            model._on_plugin_reload()
            warning.assert_called_once()

            model._discovery_plugin = _FakePlugin([])
            model._on_plugin_reload()
            model._discovery_plugin = failing_plugin
            model._on_plugin_reload()
            self.assertEqual(warning.call_count, 2)

    async def test_catalog_handles_empty_items(self) -> None:
        """Empty catalog results should be handled without error."""
        model = CatalogTreeModel()
        plugin = _FakePlugin([])
        model.set_discovery_plugin(plugin)
        model._on_plugin_reload()
        self.assertEqual(model.children, [])

    async def test_catalog_appends_compounds_group(self) -> None:
        """Catalog should append compound group when compounds exist."""
        # Build a temporary compound registry entry so the catalog model
        # includes the "Compounds" group in the resulting tree.
        compound_path = self._compound_dir.name + "/compound.usda"
        stage = Usd.Stage.CreateNew(compound_path)
        UsdShade.NodeGraph.Define(stage, "/TestCompound")
        stage.GetRootLayer().Save()

        registry = get_compound_registry()
        registry.refresh([self._compound_dir.name])

        model = CatalogTreeModel()
        plugin = _FakePlugin([GroupItem("GroupA")])
        model.set_discovery_plugin(plugin)
        model._on_plugin_reload()
        names = [child.name for child in model.children]
        self.assertIn("TestCompound", names)

    async def test_catalog_no_reload_callback_fallback(self) -> None:
        """When plugin has no reload callback, reload should still populate."""
        model = CatalogTreeModel()

        class NoCallbackPlugin(_FakePlugin):
            """Plugin stub that raises when setting callbacks."""

            def set_reload_callback(self, _cb: Callable[[], None]) -> None:
                """Simulate missing callback support."""
                raise AttributeError("no callbacks")

        plugin = NoCallbackPlugin([GroupItem("GroupA")])
        model.set_discovery_plugin(plugin)
        model._schedule_reload(immediate=True)
        await self.wait_n_updates(1)
        self.assertTrue(model.children)

    async def test_catalog_reload_debounced(self) -> None:
        """Reload should cancel previous task when called repeatedly."""
        model = CatalogTreeModel()
        plugin = _FakePlugin([GroupItem("GroupA")])
        model.set_discovery_plugin(plugin)
        model._schedule_reload()
        first_task = model._reload_task
        model._schedule_reload()
        second_task = model._reload_task
        self.assertIsNot(first_task, second_task)

    async def test_catalog_appends_textures_group(self) -> None:
        """Catalog should append textures group when textures exist."""
        with tempfile.TemporaryDirectory() as texture_dir:
            self._settings.set_string(Settings.CATALOG_TEXTURES_PATH, texture_dir)
            texture_json = Path(texture_dir) / "test.json"
            texture_json.write_text(
                json.dumps(
                    {
                        "id": "test",
                        "name": "Test",
                        "source": texture_dir + "/missing.png",
                        "icon": "",
                        "group": "TextureGroup",
                    }
                ),
                encoding="utf-8",
            )
            registry = get_texture_registry()
            registry.refresh()

            model = CatalogTreeModel()
            plugin = _FakePlugin([GroupItem("GroupA")])
            model.set_discovery_plugin(plugin)
            model._on_plugin_reload()
            names = [child.name for child in model.children]
            self.assertIn("TextureGroup", names)
