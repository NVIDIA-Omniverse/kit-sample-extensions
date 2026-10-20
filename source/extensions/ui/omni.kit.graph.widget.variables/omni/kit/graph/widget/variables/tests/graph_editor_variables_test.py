# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
from pathlib import Path
from typing import Optional

import carb
import omni.kit
import omni.ui as ui
from omni.ui.tests.test_base import OmniUiTest

from ..graph_editor_variables_widget import GraphEditorVariablesWidget

CURRENT_PATH = Path(carb.tokens.get_tokens_interface().resolve("${omni.kit.graph.widget.variables}/data"))


class VariableItem(ui.AbstractItem):
    """Node item for GraphVariablesModel"""

    def __init__(
        self, item_name: str, item_type: str, item_default: bool, item_description: str, item_category: str = ""
    ):
        super().__init__()
        self.name_model = ui.SimpleStringModel(item_name)
        self.type_model = ui.SimpleStringModel(item_type)
        self.default_model = ui.SimpleBoolModel(item_default)
        self.description_model = ui.SimpleStringModel(item_description)
        self.category_model = ui.SimpleStringModel(item_category)

        self.filtered = True
        self.build_value_widget_count = 0


class CategoryItem(ui.AbstractItem):
    def __init__(self, item_name: str, variables: list):
        super().__init__()
        self.name_model = ui.SimpleStringModel(item_name)
        self.variables = variables
        self.filtered = True


class GraphVariablesModel(ui.AbstractItemModel):
    """Variables model"""

    def __init__(self):
        super().__init__()
        self.children = [
            VariableItem("variable1", "string", False, "variable 1 description"),
            VariableItem("variable2", "bool", True, "variable 2 description"),
            CategoryItem(
                "category1", [VariableItem("variable3", "float", True, "variable 3 description", "category1")]
            ),
            CategoryItem("category2", []),
        ]

    def destroy(self):
        self.children = []

    def can_item_have_children(self, parent_item=None):
        return parent_item is not None and isinstance(parent_item, CategoryItem)

    def get_item_children(self, item=None):
        """Returns all the children when the widget asks it."""
        if item is None:
            return [c for c in self.children if c.filtered]

        if isinstance(item, CategoryItem):
            return [c for c in item.variables if c.filtered]

        return []

    def get_item_value_model_count(self, item=None):
        """The number of columns"""
        if item and isinstance(item, VariableItem):
            return 5

        return 1

    def get_item_value_model(self, item=None, column_id: int = 0):
        """
        Return value model. It's the object that tracks the specific value.
        """
        if column_id == 0:
            return item.name_model

        if column_id == 1:
            return item.type_model

        if column_id == 2:
            return item.default_model

        if column_id == 3:
            return item.description_model

        if column_id == 4:
            return item.category_model


class VariablesTestWidget(GraphEditorVariablesWidget):
    def __init__(
        self,
        on_add_variable=None,
        on_add_variable_category=None,
        on_find_variable_reference=None,
        on_build_variable_value_widget=None,
        supported_variable_types=None,
    ):
        self.variables_model = GraphVariablesModel()
        super().__init__(
            self.variables_model,
            on_add_variable=on_add_variable,
            on_add_variable_category=on_add_variable_category,
            on_find_variable_reference=on_find_variable_reference,
            on_build_variable_value_widget=on_build_variable_value_widget,
            supported_variable_types=supported_variable_types,
        )

    def expand_tree_view(self, selection: Optional[list] = None):
        for item in self.variables_model.children:
            self._tree_view.set_expanded(item, True, True)

        if selection:
            self._tree_view.selection = selection
        else:
            self._tree_view.selection = [self.variables_model.children[1]]


class TestVariablesWidget(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = CURRENT_PATH.absolute().resolve().joinpath("tests")

        # '-105.2' suffix on golden images when running on 105.2 or later.
        self._kit_version = float(omni.kit.app.acquire_app_interface().get_kit_version_short())
        self._version_suffix = "-105.2" if self._kit_version >= 105.2 else ""

    def _golden_img_name(self, test_name: str) -> str:
        """Golden image for this Kit: a '-111.0' image where Kit 111 (OVUI) renders differently, else the default."""
        base = f"omni.kit.graph.widget.variables.tests.graph_editor_variables_test.TestVariablesWidget.{test_name}"
        if self._kit_version >= 111.0 and self._golden_img_dir.joinpath(f"{base}-111.0.png").exists():
            return f"{base}-111.0.png"
        return f"{base}{self._version_suffix}.png"

    # After running each test
    async def tearDown(self):
        self._golden_img_dir = None
        await super().tearDown()

    async def test_no_buttons(self):
        """test the widget without optional buttons"""
        await self.create_test_area(width=512, height=1024)
        window = ui.Window("VariablesNoButtonsTest", width=512, height=1024)
        with window.frame:
            variables_widget = VariablesTestWidget()

        # wait a few frames for the window to be fully loaded
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        variables_widget.expand_tree_view()

        # wait a few more frames for the tree view to expand
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        await self.finalize_test(
            golden_img_dir=self._golden_img_dir,
            golden_img_name=f"omni.kit.graph.widget.variables.tests.graph_editor_variables_test.TestVariablesWidget.test_no_buttons{self._version_suffix}.png",
        )

        variables_widget.destroy()
        window.destroy()

    async def test_all_buttons(self):
        """test the widget with all optional buttons"""
        await self.create_test_area(width=512, height=1024)
        window = ui.Window("VariablesAllButtonsTest", width=512, height=1024)
        with window.frame:

            def add_fn():
                pass

            def find_fn(item):
                pass

            variables_widget = VariablesTestWidget(add_fn, add_fn, find_fn)

        # wait a few frames for the window to be fully loaded
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()

        variables_widget.expand_tree_view()

        # wait a few more frames for the tree view to expand
        for _ in range(15):
            await omni.kit.app.get_app().next_update_async()

        await self.finalize_test(
            golden_img_dir=self._golden_img_dir,
            golden_img_name=f"omni.kit.graph.widget.variables.tests.graph_editor_variables_test.TestVariablesWidget.test_all_buttons{self._version_suffix}.png",
        )

        variables_widget.destroy()
        window.destroy()

    async def test_default_widget(self):
        """test the widget with a custom default value widget"""
        await self.create_test_area(width=512, height=1024)
        window = ui.Window("VariablesDefaultWidgetTest", width=512, height=1024)
        with window.frame:

            def build_fn(item):
                ui.CheckBox(item.default_model)
                return True

            variables_widget = VariablesTestWidget(on_build_variable_value_widget=build_fn)

        # wait a few frames for the window to be fully loaded
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        variables_widget.expand_tree_view()

        # wait a few more frames for the tree view to expand
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        await self.finalize_test(
            golden_img_dir=self._golden_img_dir,
            golden_img_name=f"omni.kit.graph.widget.variables.tests.graph_editor_variables_test.TestVariablesWidget.test_default_widget{self._version_suffix}.png",
        )

        variables_widget.destroy()
        window.destroy()

    async def test_build_value_widget_count(self):
        """test to ensure value widget is rebuilt when variable type or name is changed"""
        EXPECTED_COUNT = 4

        await self.create_test_area(width=512, height=1024)
        window = ui.Window("VariablesBuildValueWidgetCountTest", width=512, height=1024)
        with window.frame:

            def build_fn(item):
                item.build_value_widget_count += 1
                return True

            variables_widget = VariablesTestWidget(on_build_variable_value_widget=build_fn)

        # wait a few frames for the window to be fully loaded
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        variables_widget.expand_tree_view()

        changed_var = variables_widget.variables_model.children[1]
        changed_var.name_model._value_changed()
        changed_var.type_model._value_changed()

        # wait a few more frames for the tree view to expand
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.assertTrue(
            (changed_var.build_value_widget_count == EXPECTED_COUNT),
            msg=f"The default value widget was rebuilt {changed_var.build_value_widget_count} times. Expected {EXPECTED_COUNT} times",
        )

        variables_widget.destroy()
        window.destroy()

    async def test_category_combo_box(self):
        """test the widget with the category combo box populated"""
        await self.create_test_area(width=512, height=1024)
        window = ui.Window("VariablesCategoryComboBoxTest", width=512, height=1024)
        with window.frame:
            variables_widget = VariablesTestWidget()

        # wait a few frames for the window to be fully loaded
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        variables_widget.expand_tree_view([variables_widget.variables_model.children[2].variables[0]])

        # wait a few more frames for the tree view to expand
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        await self.finalize_test(
            golden_img_dir=self._golden_img_dir,
            golden_img_name=f"omni.kit.graph.widget.variables.tests.graph_editor_variables_test.TestVariablesWidget.test_category_combo_box{self._version_suffix}.png",
        )

        variables_widget.destroy()
        window.destroy()

    async def test_type_combo_box(self):
        """test the widget with the variable type combo box"""
        await self.create_test_area(width=512, height=1024)
        window = ui.Window("VariablesTypeComboBoxTest", width=512, height=1024)
        with window.frame:
            variables_widget = VariablesTestWidget(supported_variable_types=["float", "bool", "string"])

        # wait a few frames for the window to be fully loaded
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        variables_widget.expand_tree_view()

        # wait a few more frames for the tree view to expand
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        await self.finalize_test(
            golden_img_dir=self._golden_img_dir,
            golden_img_name=self._golden_img_name("test_type_combo_box"),
        )

        variables_widget.destroy()
        window.destroy()
