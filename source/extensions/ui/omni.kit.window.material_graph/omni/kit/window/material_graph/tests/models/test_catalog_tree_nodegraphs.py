from unittest.mock import patch

from ...scripts.config.paths import Paths
from ...scripts.models.catalog.items import GroupItem
from ...scripts.models.catalog.items.compound import CompoundItem
from ...scripts.models.catalog.tree import CatalogTreeModel
from ..base import MaterialGraphTestBase

# pylint: disable=relative-beyond-top-level,protected-access


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


class _FakeCompoundRegistry:
    """Compound registry stub with grouped items."""

    def __init__(self, items: list[CompoundItem]) -> None:
        self._items = items
        self._reload_cb = None

    def set_reload_callback(self, cb) -> None:
        self._reload_cb = cb

    def get_items(self) -> list[CompoundItem]:
        return list(self._items)

    def get_group_items(self) -> list[GroupItem]:
        group = GroupItem("GroupA")
        setattr(group, "is_compound_group", True)
        for item in self._items:
            if item.group == "GroupA":
                group.add_child(item)
        return [group]


class _EmptyTextureRegistry:
    def set_reload_callback(self, cb) -> None:
        pass

    def get_group_items(self) -> list[GroupItem]:
        return []

    def get_items(self) -> list:
        return []


class TestCatalogTreeNodeGraphs(MaterialGraphTestBase):
    """Catalog tree nodegraph grouping behavior."""

    async def test_nodegraphs_grouping_and_filtering(self) -> None:
        """Compound items are grouped by group and filtered by current context visibility."""
        item_a = CompoundItem(
            name="CompoundA",
            info="info",
            icon="",
            tooltip="tooltip",
            source_asset="asset.usda",
            identifier="/GraphA",
            context_visibility=["mdl"],
            group="GroupA",
        )
        item_b = CompoundItem(
            name="CompoundB",
            info="info",
            icon="",
            tooltip="tooltip",
            source_asset="asset.usda",
            identifier="/GraphB",
            context_visibility=["mdl"],
            group="",
        )
        fake_registry = _FakeCompoundRegistry([item_a, item_b])

        with (
            patch(
                f"{Paths.MODULE_ID}.scripts.models.catalog.tree.get_compound_registry",
                autospec=True,
                return_value=fake_registry,
            ),
            patch(
                f"{Paths.MODULE_ID}.scripts.models.catalog.tree.get_texture_registry",
                autospec=True,
                return_value=_EmptyTextureRegistry(),
            ),
        ):
            model = CatalogTreeModel()
            plugin = _FakePlugin([])
            model.set_discovery_plugin(plugin)
            model._on_plugin_reload()

            model.set_filter_group("nodegraphs")
            nodegraphs_only = model.get_item_children(None)
            self.assertGreaterEqual(len(nodegraphs_only), 1)
            self.assertTrue(all(isinstance(item, (GroupItem, CompoundItem)) for item in nodegraphs_only))

            model.set_filter_group("nodes")
            nodes_only = model.get_item_children(None)
            self.assertTrue(all(not isinstance(item, CompoundItem) for item in nodes_only))
