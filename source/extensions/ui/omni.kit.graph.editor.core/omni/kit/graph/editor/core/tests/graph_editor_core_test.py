## Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##
from pathlib import Path

import carb
import omni.kit
import omni.ui as ui
from omni.kit.widget.graph import GraphView
from omni.kit.widget.graph.graph_model import GraphModel
from omni.ui.tests.test_base import OmniUiTest

from ..graph_editor_core_widget import GraphEditorCoreWidget

CURRENT_PATH = Path(carb.tokens.get_tokens_interface().resolve("${omni.kit.graph.editor.core}/data"))


class Node:
    """Node for GraphTestModel"""

    def __init__(self, name: str):
        self.name = name


class GraphTestModel(GraphModel):
    """ "Graph model for editor"""

    def __init__(self):
        super().__init__()

    @property
    def nodes(self, item=None):
        if item is None:
            return [Node("root")]
        if item.name == "root":
            return [Node("child")]
        if item.name == "child":
            return [Node("childChild")]
        return None

    @property
    def name(self, item):
        if item:
            return item.name


class NodeItem(ui.AbstractItem):
    """Node item for NodeCatalogModel"""

    def __init__(self, item_name: str):
        super().__init__()
        self.name_model = ui.SimpleStringModel(item_name)
        self.filtered = True


class NodeCatalogModel(ui.AbstractItemModel):
    """Node catalog model"""

    def __init__(self, *args):
        super().__init__()
        self._children = [NodeItem("data"), NodeItem("symbol")]

    def destroy(self):
        self._children = []

    def get_item_children(self, item):
        """Returns all the children when the widget asks it."""
        if item is None:
            return [c for c in self._children if c.filtered]
        return []

    def get_item_value_model_count(self, item):
        """The number of columns. There is only one column in our case"""
        return 1

    def get_item_value_model(self, item, column_id: int):
        """
        Return value model. It's the object that tracks the specific value.
        In graph core, there are four value models defined for node registry model.
        """
        if column_id == 0:
            return item.name_model


class GraphTestWidget(GraphEditorCoreWidget):
    def __init__(self, graph_model, catalog_model, toolbar_items, **kwargs):
        self.graph_model = graph_model
        self.catalog_model = catalog_model
        self.toolbar_items = toolbar_items
        has_catalog = True if self.catalog_model else False

        super().__init__(
            model=self.graph_model,
            delegate=None,
            view_type=GraphView,
            style=None,
            catalog_model=self.catalog_model,
            catalog_delegate=None,
            toolbar_items=self.toolbar_items,
            has_catalog=has_catalog,
            **kwargs,
        )

    def on_build_breadcrumbs(self):
        # add space padding around the navigation
        with ui.VStack():
            ui.Spacer(height=10)
            with ui.HStack(width=0):
                ui.Spacer(width=15)
                super().on_build_breadcrumbs()

    def on_build_startup(self):
        ui.Label("Startup page")

    def destroy(self):
        if self.catalog_model:
            self.catalog_model.destroy()
        self.catalog_model = None

        if self.graph_model:
            self.graph_model.destroy()
        self.graph_model = None


class TestGraphCoreEditor(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = CURRENT_PATH.absolute().resolve().joinpath("tests")

    # After running each test
    async def tearDown(self):
        self._golden_img_dir = None
        await super().tearDown()

    async def test_general(self):
        """test the general core widget"""
        await self.create_test_area(width=1024, height=512)
        graph_window = ui.Window("GraphCoreGeneralTest", width=1024, height=512)
        graph_widget = None
        with graph_window.frame:
            graph_widget = GraphTestWidget(GraphTestModel(), None, [])
            graph_widget.focus_on_nodes()

        # wait a few frames for the window to be fully loaded
        for _ in range(50):
            await omni.kit.app.get_app().next_update_async()

        await self.finalize_test(golden_img_dir=self._golden_img_dir)

        graph_widget = None
        graph_window = None

    async def test_breadcrumbs(self):
        """test the set_current_compound API and navigation of the graph"""
        await self.create_test_area(width=1024, height=512)
        graph_window = ui.Window("GraphCoreGeneralTest", width=1024, height=512)
        graph_widget = None
        with graph_window.frame:
            graph_widget = GraphTestWidget(GraphTestModel(), None, [])

        # wait a few frames for the mdoel to be set for GraphView
        for _ in range(50):
            await omni.kit.app.get_app().next_update_async()

        widget_model = graph_widget.model
        if widget_model:
            root_item = widget_model[None].nodes
            if root_item and len(root_item) == 1:
                graph_widget.set_current_compound(root_item[0])
                child_item = widget_model[root_item[0]].nodes
                if child_item and len(child_item) == 1:
                    graph_widget.set_current_compound(child_item[0])
                    graph_widget.focus_on_nodes()

        # wait a few frames for the window to be fully loaded
        for _ in range(50):
            await omni.kit.app.get_app().next_update_async()

        await self.finalize_test(golden_img_dir=self._golden_img_dir)

        graph_widget = None
        graph_window = None

    async def test_catalog_widget(self):
        """test the tree view delegate on left side of the graph"""
        await self.create_test_area(width=1024, height=512)
        graph_window = ui.Window("GraphCoreToolbarTest", width=1024, height=512)
        with graph_window.frame:
            graph_widget = GraphTestWidget(None, NodeCatalogModel(), [])

        # wait a few frames for the window to be fully loaded
        for _ in range(70):
            await omni.kit.app.get_app().next_update_async()

        await self.finalize_test(golden_img_dir=self._golden_img_dir)
        graph_widget.destroy()
        graph_widget = None
        graph_window = None

    async def test_toolbar(self):
        """test the creation of toolbar for graph"""
        await self.create_test_area(width=1024, height=512)
        graph_window = ui.Window("GraphCoreToolbarTest", width=1024, height=512)
        graph_widget = None
        with graph_window.frame:
            graph_widget = GraphTestWidget(None, None, [{"name": "open", "label": "Open"}, {"name": "-"}])

        # wait a few frames for the window to be fully loaded
        for _ in range(50):
            await omni.kit.app.get_app().next_update_async()

        await self.finalize_test(golden_img_dir=self._golden_img_dir)
        graph_window.destroy()
        graph_window = None

    async def test_reset_toolbar(self):
        """test reseting toolbar for graph"""
        await self.create_test_area(width=1024, height=512)
        graph_window = ui.Window("GraphCoreToolbarTest", width=1024, height=512)
        with graph_window.frame:
            graph_widget = GraphTestWidget(None, None, [])
            # reset the toolbar items
            graph_widget.set_toolbar_items(
                [{"name": "rebuild", "label": "Rebuild"}, {"name": "-"}, {"name": "save", "label": "Save"}]
            )

        # wait a few frames for the window to be fully loaded
        for _ in range(50):
            await omni.kit.app.get_app().next_update_async()

        await self.finalize_test(golden_img_dir=self._golden_img_dir)
        graph_window.destroy()
        graph_window = None

    async def test_startup_page(self):
        """test the startup page for graph"""
        await self.create_test_area(width=1024, height=512)
        graph_window = ui.Window("GraphCoreToolbarTest", width=1024, height=512)
        with graph_window.frame:
            graph_widget = GraphTestWidget(GraphTestModel(), None, [])
            # unset the model to load the startup page
            graph_widget.model = None

        # wait a few frames for the window to be fully loaded
        for _ in range(50):
            await omni.kit.app.get_app().next_update_async()

        await self.finalize_test(golden_img_dir=self._golden_img_dir)

        graph_widget = None
        graph_window = None
