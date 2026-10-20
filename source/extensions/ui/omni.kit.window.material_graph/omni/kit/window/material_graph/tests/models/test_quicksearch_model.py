"""Fast, headless coverage for the Material Graph Quick Search model."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import omni.kit.test
import omni.ui as ui

from ...scripts import extension as extension_module
from ...scripts.models.catalog.items import CompoundItem, GroupItem, TextureItem
from ...scripts.models.catalog.quicksearch import MaterialGraphQuickSearchModel, QuickSearchSectionItem
from ...scripts.models.catalog.quicksearch import model as quicksearch_module


class _Leaf:
    """Minimal droppable catalog leaf used by model-only tests."""

    def __init__(
        self,
        name: str,
        *,
        info: str = "",
        tags=None,
        visible: bool = True,
        mime_data: str = "mime-data",
    ) -> None:
        self.name_model = ui.SimpleStringModel(name)
        self.info_model = ui.SimpleStringModel(info)
        self.icon_model = ui.SimpleStringModel("icon")
        self.tooltip_model = ui.SimpleStringModel("tooltip")
        self.tags = list(tags or [])
        self._visible = visible
        self._mime_data = mime_data

    def is_visible_in_context(self, _context_name):
        return self._visible

    def get_drag_mime_data(self):
        return self._mime_data


class TestQuickSearchModel(omni.kit.test.AsyncTestCase):
    """Exercise filtering, grouping, values, and execution without rendering UI."""

    async def setUp(self) -> None:
        self.model = MaterialGraphQuickSearchModel()

    async def tearDown(self) -> None:
        self.model.destroy()

    async def test_initialization_values_filter_and_destroy(self) -> None:
        self.assertEqual([section.key for section in self.model._sections], ["nodes", "nodegraphs", "textures"])
        section = self.model._sections[0]
        self.assertEqual(self.model.get_item_value_model_count(section), 1)
        self.assertIs(self.model.get_item_value_model(section, 0), section.name_model)
        self.assertIs(self.model.get_item_value_model(section, 1), section.info_model)
        self.assertIs(self.model.get_item_value_model(section, 2), section.icon_model)
        self.assertIs(self.model.get_item_value_model(section, 3), section.tooltip_model)
        self.assertIsNone(self.model.get_item_value_model(None, 0))
        self.assertIsNone(self.model.get_item_value_model(section, 99))

        self.model.filter_by_text("  MiXeD  ")
        self.assertEqual(self.model._filter_text, "mixed")
        self.model.filter_by_text(None)
        self.assertEqual(self.model._filter_text, "")
        self.model.destroy()
        self.assertEqual(self.model._sections, [])

    async def test_missing_catalog_has_no_children(self) -> None:
        with patch.object(self.model, "_get_catalog_model", return_value=None):
            self.assertEqual(self.model.get_item_children(None), [])
            self.assertFalse(self.model.can_item_have_children(QuickSearchSectionItem("nodes", "Nodes")))
            self.assertFalse(self.model.can_item_have_children(GroupItem("Group")))
        self.assertTrue(self.model.can_item_have_children(None))
        self.assertFalse(self.model.can_item_have_children(object()))
        self.assertEqual(self.model.get_item_children(object()), [])

    async def test_sections_partition_and_return_filtered_children(self) -> None:
        node_leaf = _Leaf("Node")
        node_group = GroupItem("Node Group")
        node_group.add_child(node_leaf)
        compound = CompoundItem("Graph", "", "", "", "asset.usd", "Graph")
        texture = TextureItem("Texture", "texture.png", "icon.png")
        catalog = SimpleNamespace(current_context="mtlx", children=[node_group, compound, texture])

        with patch.object(self.model, "_get_catalog_model", return_value=catalog):
            visible = self.model.get_item_children(None)
            self.assertEqual([section.key for section in visible], ["nodes", "nodegraphs", "textures"])
            self.assertEqual(self.model.get_item_children(self.model._sections[0]), [node_group])
            self.assertEqual(self.model.get_item_children(self.model._sections[1]), [compound])
            self.assertEqual(self.model.get_item_children(self.model._sections[2]), [texture])
            self.assertEqual(self.model.get_item_children(node_group), [node_leaf])
            self.assertTrue(self.model.can_item_have_children(self.model._sections[0]))
            self.assertTrue(self.model.can_item_have_children(node_group))

    async def test_filtering_matches_name_info_tags_and_visibility(self) -> None:
        by_name = _Leaf("Diffuse Color")
        by_info = _Leaf("Other", info="Useful Description")
        by_tag = _Leaf("Third", tags=["Surface", 42])
        hidden = _Leaf("Diffuse Hidden", visible=False)
        non_leaf = SimpleNamespace(name_model=ui.SimpleStringModel("Diffuse Invalid"))
        nested = GroupItem("Nested")
        nested.add_child(by_tag)
        outer = GroupItem("Outer")
        outer.add_child(nested)

        self.assertTrue(self.model._matches(by_name, "COLOR"))
        self.assertTrue(self.model._matches(by_info, "description"))
        self.assertTrue(self.model._matches(by_tag, "42"))
        self.assertFalse(self.model._matches(by_tag, "missing"))
        self.assertEqual(
            self.model._filter_children([by_name, by_info, by_tag, hidden, non_leaf], "mtlx"),
            [by_name, by_info, by_tag],
        )

        self.model._filter_text = "surface"
        self.assertTrue(self.model._group_has_match(outer, "mtlx"))
        self.assertEqual(self.model._filter_children([outer], "mtlx"), [outer])
        self.model._filter_text = "absent"
        self.assertFalse(self.model._group_has_match(outer, "mtlx"))
        self.assertEqual(self.model._filter_children([outer], "mtlx"), [])

    async def test_partition_supports_groups_and_leaf_types(self) -> None:
        node = _Leaf("Node")
        texture_group = GroupItem("Texture Group")
        texture_group.is_texture_group = True
        compound_group = GroupItem("Compound Group")
        compound_group.is_compound_group = True
        texture = TextureItem("Texture", "texture.png", "icon.png")
        compound = CompoundItem("Graph", "", "", "", "asset.usd", "Graph")

        buckets = self.model._partition_root_children([node, texture_group, compound_group, texture, compound])
        self.assertEqual(buckets["nodes"], [node])
        self.assertEqual(buckets["textures"], [texture_group, texture])
        self.assertEqual(buckets["nodegraphs"], [compound_group, compound])

    async def test_execute_adds_only_valid_leaf_mime_data(self) -> None:
        add_node = MagicMock()
        with patch.object(extension_module.GraphExtension, "add_node", add_node):
            self.model.execute(object())
            self.model.execute(_Leaf("Empty", mime_data=""))
            self.model.execute(_Leaf("Ready", mime_data="payload"))
        add_node.assert_called_once_with("payload")

    async def test_execute_failure_reports_error_when_graph_widget_exists(self) -> None:
        graph_widget = SimpleNamespace(show_error=MagicMock())
        graph_window = SimpleNamespace(graph_widget=graph_widget)
        with (
            patch.object(extension_module.GraphExtension, "add_node", side_effect=RuntimeError("injected")),
            patch.object(extension_module, "get_graph_window", return_value=graph_window),
            patch.object(quicksearch_module, "log_exception") as log_exception,
        ):
            self.model.execute(_Leaf("Broken"))
        log_exception.assert_called_once()
        graph_widget.show_error.assert_called_once_with(
            "Quick Search could not create the selected node; see the preceding Material Graph log entry for the "
            "item and exception details",
            log_message=False,
        )

    async def test_execute_failure_is_safe_without_graph_window(self) -> None:
        with (
            patch.object(extension_module.GraphExtension, "add_node", side_effect=RuntimeError("injected")),
            patch.object(extension_module, "get_graph_window", return_value=None),
            patch.object(quicksearch_module, "log_exception") as log_exception,
        ):
            self.model.execute(_Leaf("Broken"))
        log_exception.assert_called_once()

    async def test_catalog_lookup_handles_window_states(self) -> None:
        with patch.object(extension_module, "get_graph_window", return_value=None):
            self.assertIsNone(self.model._get_catalog_model())
        with patch.object(extension_module, "get_graph_window", return_value=SimpleNamespace(graph_widget=None)):
            self.assertIsNone(self.model._get_catalog_model())
        catalog = object()
        graph_widget = SimpleNamespace(catalog_model=catalog)
        with patch.object(
            extension_module,
            "get_graph_window",
            return_value=SimpleNamespace(graph_widget=graph_widget),
        ):
            self.assertIs(self.model._get_catalog_model(), catalog)
