# pylint: disable=relative-beyond-top-level,protected-access
import tempfile
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from ...scripts.config.paths import Paths
from ...scripts.models.catalog.items import CompoundItem, GroupItem
from ...scripts.models.catalog.items.texture import TextureItem
from ...scripts.models.catalog.registries.texture import TextureRegistry
from ...scripts.models.catalog.tree import CatalogTreeModel
from ...scripts.settings.settings import Settings
from ..base import MaterialGraphTestBase


class _FakePlugin:
    """Plugin stub that supplies catalog items."""

    def __init__(self, items: list[GroupItem]) -> None:
        self._items = items
        self.name = "fake"
        self._reload_cb = None

    def set_reload_callback(self, cb) -> None:
        self._reload_cb = cb

    def get_catalog_items(self) -> list[GroupItem]:
        return self._items

    def reload(self) -> None:
        """No-op reload to satisfy catalog model calls."""
        if self._reload_cb:
            self._reload_cb()


@contextmanager
def _isolated_catalog_model():
    """Construct a tree model without mutating process-global registry callbacks."""
    compound_registry = SimpleNamespace(
        set_reload_callback=MagicMock(),
        get_group_items=MagicMock(return_value=[]),
        get_items=MagicMock(return_value=[]),
        refresh=MagicMock(),
        assign_group=MagicMock(return_value=True),
    )
    texture_registry = SimpleNamespace(
        set_reload_callback=MagicMock(),
        get_group_items=MagicMock(return_value=[]),
        get_items=MagicMock(return_value=[]),
        assign_group=MagicMock(return_value=True),
    )
    with (
        patch(
            f"{Paths.MODULE_ID}.scripts.models.catalog.tree.get_compound_registry",
            return_value=compound_registry,
        ),
        patch(
            f"{Paths.MODULE_ID}.scripts.models.catalog.tree.get_texture_registry",
            return_value=texture_registry,
        ),
    ):
        model = CatalogTreeModel()
    try:
        yield model, compound_registry, texture_registry
    finally:
        model.destroy()


class TestCatalogTreeTextures(MaterialGraphTestBase):
    """Catalog tree texture grouping behavior."""

    async def setUp(self) -> None:
        await super().setUp()
        self._tmp_dir = tempfile.TemporaryDirectory()
        self._settings.set_string(Settings.CATALOG_TEXTURES_PATH, self._tmp_dir.name)

    async def tearDown(self) -> None:
        try:
            self._tmp_dir.cleanup()
        finally:
            await super().tearDown()

    async def test_textures_grouping_and_filtering(self) -> None:
        """Texture groups and filters should behave correctly."""
        texture_a = Path(self._tmp_dir.name) / "a.png"
        texture_b = Path(self._tmp_dir.name) / "b.png"
        texture_a.write_text("dummy", encoding="utf-8")
        texture_b.write_text("dummy", encoding="utf-8")

        with patch.object(TextureRegistry, "_schedule_validation", autospec=True):
            registry = TextureRegistry()
            registry.create_group("GroupA")
            item_a = registry.add_texture(str(texture_a), name="A")
            registry.add_texture(str(texture_b), name="B")
            registry.assign_group(item_a, "GroupA")

            with patch(
                f"{Paths.MODULE_ID}.scripts.models.catalog.tree.get_texture_registry",
                autospec=True,
                return_value=registry,
            ):
                model = CatalogTreeModel()
                plugin = _FakePlugin([GroupItem("GroupA")])
                model.set_discovery_plugin(plugin)
                model._on_plugin_reload()

                root_items = model.get_item_children(None)
                group_names = [item.name for item in root_items if isinstance(item, GroupItem)]
                texture_names = [item.name for item in root_items if isinstance(item, TextureItem)]
                self.assertIn("GroupA", group_names)
                self.assertIn("B", texture_names)

                model.set_filter_group("textures")
                textures_only = model.get_item_children(None)
                self.assertTrue(textures_only)
                self.assertTrue(all(isinstance(item, (GroupItem, TextureItem)) for item in textures_only))

                model.set_filter_group("nodes")
                nodes_only = model.get_item_children(None)
                self.assertTrue(all(not isinstance(item, TextureItem) for item in nodes_only))

            registry.destroy()

    async def test_tree_value_models_drag_data_and_group_filters(self) -> None:
        """Tree model columns, drag payloads, and group filters should remain deterministic."""
        with _isolated_catalog_model() as (model, _, _):
            texture = TextureItem("Texture", "texture.png", "")
            texture_group = GroupItem("Textures")
            texture_group.is_texture_group = True
            texture_group.add_child(texture)
            node_group = GroupItem("Nodes")
            model._children = [texture_group, node_group]

            self.assertEqual(model.get_item_value_model_count(texture), 1)
            self.assertIs(
                model.get_item_value_model(texture, CatalogTreeModel.Column.NAME.value),
                texture.name_model,
            )
            self.assertIs(
                model.get_item_value_model(texture, CatalogTreeModel.Column.INFO.value),
                texture.info_model,
            )
            self.assertIs(
                model.get_item_value_model(texture, CatalogTreeModel.Column.ICON.value),
                texture.icon_model,
            )
            self.assertIs(
                model.get_item_value_model(texture, CatalogTreeModel.Column.TOOLTIP.value),
                texture.tooltip_model,
            )
            self.assertIsNone(model.get_item_value_model(None, 0))
            self.assertIsNone(model.get_item_value_model(texture, 99))
            self.assertIn('"type": "Texture"', model.get_drag_mime_data(texture))
            self.assertEqual(model.get_drag_mime_data(node_group), "")

            model.set_filter_group("textures")
            self.assertEqual(model.get_item_children(None), [texture_group])
            self.assertEqual(model.get_item_children(texture_group), [texture])
            self.assertEqual(model.get_item_children(node_group), [])
            self.assertEqual(model.get_item_children(texture), [])

    async def test_tree_drop_routes_texture_and_compound_group_assignments(self) -> None:
        """Internal drops should accept only matching groups and route persistent assignments."""
        with _isolated_catalog_model() as (model, compound_registry, texture_registry):
            texture = TextureItem("Texture", "texture.png", "", group="Old")
            compound = CompoundItem("Graph", "", "", "", "graph.usda", "/Graph", group="Old")
            texture_group = GroupItem("NewTexture")
            texture_group.is_texture_group = True
            compound_group = GroupItem("NewCompound")
            compound_group.is_compound_group = True
            self.assertTrue(model.drop_accepted(texture_group, texture))
            self.assertTrue(model.drop_accepted(None, texture))
            self.assertFalse(model.drop_accepted(compound_group, texture))
            self.assertTrue(model.drop_accepted(compound_group, compound))
            self.assertFalse(model.drop_accepted(texture_group, compound))
            self.assertFalse(model.drop_accepted(None, object()))

            model.drop(texture_group, texture)
            texture_registry.assign_group.assert_called_once_with(texture, "NewTexture")
            model.drop(None, texture)
            self.assertEqual(texture_registry.assign_group.call_args_list[-1].args, (texture, ""))
            model.drop(compound_group, compound)
            compound_registry.assign_group.assert_called_once_with(compound, "NewCompound")

            texture_registry.assign_group.side_effect = RuntimeError("write failed")
            model.drop(texture_group, texture)
            compound_registry.assign_group.return_value = False
            model.drop(compound_group, compound)

    async def test_context_filtering_signatures_and_clear_notifications(self) -> None:
        """Visibility changes should notify only when projected catalog state changes."""
        with _isolated_catalog_model() as (model, _, _):
            visible = CompoundItem("Visible", "", "", "", "graph.usda", "/Visible", ["mdl"])
            hidden = CompoundItem("Hidden", "", "", "", "graph.usda", "/Hidden", ["mtlx"])
            group = GroupItem("Compounds")
            group.is_compound_group = True
            group.add_child(visible)
            group.add_child(hidden)
            model._children = [group]
            with patch.object(model, "_item_changed") as changed:
                model.set_current_context("mdl")
                model.filter_by_text("")
                self.assertEqual([item.name for item in model.get_item_children(group)], ["Visible"])
                model.filter_by_text("visible")
                self.assertTrue(changed.called)
                changed.reset_mock()
                model.set_filter_group("nodegraphs")
                changed.assert_called_once_with(None)

            signature = model._compute_signature([group])
            self.assertEqual(signature, model._compute_signature([group]))
            model.clear()
            self.assertEqual(model.children, [])
            model.clear()

    async def test_registry_reload_callbacks_and_destroy_release_every_subscription(self) -> None:
        """Registry callbacks should rebuild only active catalogs and destroy should detach all owners."""
        with _isolated_catalog_model() as (model, compound_registry, texture_registry):
            plugin = _FakePlugin([GroupItem("Shaders")])
            model.set_discovery_plugin(plugin)
            model._on_compounds_reload()
            model._on_textures_reload()
            model.refresh_compounds()
            self.assertTrue(model.children)
            compound_registry.refresh.assert_called_once_with()

        compound_registry.set_reload_callback.assert_called_with(None)
        texture_registry.set_reload_callback.assert_called_with(None)
        self.assertEqual(model.children, [])
