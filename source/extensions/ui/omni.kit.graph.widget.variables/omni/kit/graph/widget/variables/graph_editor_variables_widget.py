# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["GraphEditorVariablesWidget"]

import weakref
from functools import partial
from pathlib import Path
from typing import Callable, Optional

import omni.kit.ui
import omni.ui as ui
from omni.kit.widget.searchable_combobox import build_searchable_combo_widget
from omni.kit.widget.searchfield import SearchField

from .graph_editor_variables_tree_delegate import GraphEditorVariablesTreeDelegate

EMPTY_STRING_MODEL = ui.SimpleStringModel("")
ICON_PATH = Path(omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)).joinpath(
    "icons"
)


class VariablePropertyComboBoxModel(ui.AbstractItemModel):
    def __init__(self):
        super().__init__()

        self._current_index_model = ui.SimpleIntModel()

        def on_index_changed(index_model):
            if self._target_model:
                index = index_model.as_int
                combo_items = self.get_item_children()
                if index < len(combo_items):
                    self._target_model.set_value(self.get_item_value_model(combo_items[index]).as_string)

            self._item_changed(None)

        self._index_callback_id = self._current_index_model.add_value_changed_fn(on_index_changed)
        self._target_model = None
        self._target_callback_id = None

    def destroy(self):
        self._current_index_model.remove_value_changed_fn(self._index_callback_id)
        self._current_index_model = None
        self._index_callback_id = None
        self.target_model = None

    def can_item_have_children(self, parent_item=None):
        return not parent_item

    def get_item_value_model_count(self, item=None):
        return 1

    @property
    def target_model(self) -> Optional[ui.AbstractValueModel]:
        return self._target_model

    @target_model.setter
    def target_model(self, value_model: Optional[ui.AbstractValueModel]):
        if self._target_model:
            self._target_model.remove_value_changed_fn(self._target_callback_id)
            self._target_callback_id = None

        self._target_model = value_model

        if not self._target_model:
            return

        def on_value_changed(model: ui.AbstractValueModel):
            model_value = model.as_string
            items = self.get_item_children()
            for i in range(len(items)):
                if self.get_item_value_model(items[i]).as_string == model_value:
                    self.get_item_value_model().set_value(i)
                    break

        self._target_callback_id = self._target_model.add_value_changed_fn(on_value_changed)
        on_value_changed(self._target_model)


class CategoryComboBoxModel(VariablePropertyComboBoxModel):
    class NoCategoryItem(ui.AbstractItem):
        def __init__(self):
            super().__init__()
            self.value_model = ui.SimpleStringModel("No Category")

    def __init__(self, variable_item_model):
        super().__init__()

        self._no_category_item = CategoryComboBoxModel.NoCategoryItem()
        self._variable_item_model = variable_item_model

        def on_variables_changed(model, item):
            if item:
                return

            if len(self.get_item_children()) < self._current_index_model.as_int:
                self._current_index_model.set_value(0)

            self._item_changed(None)

        self._callback_id = self._variable_item_model.add_item_changed_fn(on_variables_changed)

    def destroy(self):
        super().destroy()
        self._no_category_item = None

        self._variable_item_model.remove_item_changed_fn(self._callback_id)
        self._variable_item_model = None
        self._callback_id = None

    def get_item_children(self, parent_item=None):
        if not parent_item:
            result = [self._no_category_item]
            for item in self._variable_item_model.get_item_children():
                if self._variable_item_model.can_item_have_children(item):
                    result.append(item)

            return result

        return []

    def get_item_value_model(self, item=None, column_id=0):
        if not item:
            return self._current_index_model

        if item == self._no_category_item:
            return self._no_category_item.value_model

        return self._variable_item_model.get_item_value_model(item, 0)


class TypeComboBoxModel(VariablePropertyComboBoxModel):
    class TypeItem(ui.AbstractItem):
        def __init__(self, var_type):
            super().__init__()
            self.value_model = ui.SimpleStringModel(str(var_type))

    def __init__(self, supported_variable_types: list):
        super().__init__()

        self._children = [TypeComboBoxModel.TypeItem(var_type) for var_type in supported_variable_types]

    def destroy(self):
        super().destroy()
        self._children = None

    def get_item_children(self, parent_item=None):
        if not parent_item:
            return self._children

        return []

    def get_item_value_model(self, item=None, column_id=0):
        if not item:
            return self._current_index_model

        return item.value_model


class GraphEditorVariablesWidget:
    def __init__(
        self,
        model: ui.AbstractItemModel,
        delegate: ui.AbstractItemDelegate = None,
        on_add_variable: Optional[Callable[[], None]] = None,
        on_add_variable_category: Optional[Callable[[], None]] = None,
        on_find_variable_reference: Optional[Callable[[ui.AbstractItem], None]] = None,
        on_build_variable_value_widget: Optional[Callable[[ui.AbstractItem], bool]] = None,
        supported_variable_types: Optional[list] = None,
        **kwargs,
    ):
        self._model = model

        # auto type conversion added in Kit 105.2
        self._app_gt_105_2 = float(omni.kit.app.acquire_app_interface().get_kit_version_short()) >= 105.2

        def on_variables_changed(model, item):
            if not self._selected_item:
                return

            for variable_item in model.get_item_children():
                if variable_item == self._selected_item:
                    return

            self._on_variable_selection_changed([])

        self._variables_changed_callback_id = self._model.add_item_changed_fn(on_variables_changed)

        if delegate:
            self._delegate = delegate
            self._delegate_created = False
        else:
            self._delegate = GraphEditorVariablesTreeDelegate()
            self._delegate_created = True

        self._tree_view = None
        self._search_field = None

        self._filter_subscription = None

        self._on_add_variable_fn = on_add_variable
        self._on_add_variable_category_fn = on_add_variable_category
        self._on_find_variable_reference_fn = on_find_variable_reference
        self._on_build_variable_value_widget_fn = on_build_variable_value_widget

        self._selected_item = None
        self._add_menu = None
        self._add_button = None
        self._add_variable_button = None
        self._add_category_button = None
        self._variable_properties_stack = None
        self._variable_name_field = None
        self._variable_details_stack = None
        self._variable_type_field = None

        if supported_variable_types and len(supported_variable_types) > 0:
            self._type_combo_model = TypeComboBoxModel(supported_variable_types)
            self._supported_variable_types = supported_variable_types
        else:
            self._type_combo_model = None
            self._supported_variable_types = []

        self._variable_type_combo = None

        self._last_type_model = None
        self._type_changed_callback_id = None

        self._last_name_model = None
        self._name_changed_callback_id = None

        self._variable_default_stack = None
        self._variable_default_widget_container = None
        self._variable_default_widget = None
        self._variable_description_stack = None
        self._variable_description_field = None
        self._variable_category_stack = None
        self._category_combo_model = CategoryComboBoxModel(model)
        self._variable_category_combo = None
        self._find_variable_button = None
        self._delete_item_button = None

        self._frame = ui.Frame(**kwargs)
        self._frame.set_build_fn(self._on_build)

    def destroy(self):
        self._filter_subscription = None

        def destroy_widget(widget):
            if widget:
                widget.destroy()

        destroy_widget(self._search_field)
        self._search_field = None

        destroy_widget(self._tree_view)
        self._tree_view = None

        if self._delegate_created:
            self._delegate.destroy()

        self._delegate = None

        self._model.remove_item_changed_fn(self._variables_changed_callback_id)
        self._model = None
        self._variables_changed_callback_id = None

        self._on_add_variable_fn = None
        self._on_add_variable_category_fn = None
        self._on_find_variable_reference_fn = None
        self._on_build_variable_value_widget_fn = None
        self._selected_item = None

        destroy_widget(self._add_button)
        self._add_button = None
        destroy_widget(self._add_variable_button)
        self._add_variable_button = None
        destroy_widget(self._add_category_button)
        self._add_category_button = None
        destroy_widget(self._add_menu)
        self._add_menu = None
        destroy_widget(self._variable_name_field)
        self._variable_name_field = None
        destroy_widget(self._variable_type_field)
        self._variable_type_field = None

        if self._type_combo_model:
            self._type_combo_model.destroy()
            self._type_combo_model = None

        destroy_widget(self._variable_type_combo)
        self._variable_type_combo = None
        self._supported_variable_types = None

        if self._last_type_model and self._type_changed_callback_id:
            self._last_type_model.remove_value_changed_fn(self._type_changed_callback_id)
            self._last_type_model = None
            self._type_changed_callback_id = None

        if self._last_name_model and self._name_changed_callback_id:
            self._last_name_model.remove_value_changed_fn(self._name_changed_callback_id)
            self._last_name_model = None
            self._name_changed_callback_id = None

        destroy_widget(self._variable_default_widget_container)
        self._variable_default_widget_container = None
        destroy_widget(self._variable_default_widget)
        self._variable_default_widget = None
        destroy_widget(self._variable_default_stack)
        self._variable_default_stack = None
        destroy_widget(self._variable_description_field)
        self._variable_description_field = None
        destroy_widget(self._variable_description_stack)
        self._variable_description_stack = None

        self._category_combo_model.destroy()
        self._category_combo_model = None

        destroy_widget(self._variable_category_combo)
        self._variable_category_combo = None
        destroy_widget(self._variable_category_stack)
        self._variable_category_stack = None
        destroy_widget(self._variable_details_stack)
        self._variable_details_stack = None

        destroy_widget(self._find_variable_button)
        self._find_variable_button = None
        destroy_widget(self._delete_item_button)
        self._delete_item_button = None

        destroy_widget(self._variable_properties_stack)
        self._variable_properties_stack = None

        destroy_widget(self._frame)
        self._frame = None

    @property
    def visible(self):
        return self._frame.visible

    @visible.setter
    def visible(self, value: bool):
        self._frame.visible = value

    def set_on_add_variable_fn(self, fn: Optional[Callable[[ui.AbstractItem], None]]):
        self._on_add_variable_fn = fn
        if self._add_variable_button:
            self._add_variable_button.visible = fn is not None
            self._add_button.visible = fn is not None and self._on_add_variable_category_fn is not None

    def set_on_add_variable_category_fn(self, fn: Optional[Callable[[], None]]):
        self._on_add_variable_category_fn = fn
        if self._add_category_button:
            self._add_category_button.visible = fn is not None
            self._add_button.visible = fn is not None and self._on_add_variable_fn is not None
            self._on_variable_selection_changed(self._tree_view.selection)

    def set_on_find_variable_reference_fn(self, fn: Optional[Callable[[ui.AbstractItem], None]]):
        self._on_find_variable_reference_fn = fn
        if self._find_variable_button:
            self._find_variable_button.visible = fn is not None

    def set_on_build_variable_value_widget_fn(self, fn: Optional[Callable[[ui.AbstractItem], bool]]):
        self._on_build_variable_value_widget_fn = fn
        if self._variable_default_widget_container:
            self._on_variable_selection_changed(self._tree_view.selection)

    def _filter_by_text(self, filter_name_text: str):
        """Called when the user changes the search field"""
        self._tree_view.keep_expanded = not not filter_name_text
        self._delegate.filter_by_text(filter_name_text)
        self._model.filter_by_text(filter_name_text)

    def _on_variable_selection_changed(self, items):
        has_selection = items is not None and len(items) > 0
        self._variable_properties_stack.visible = has_selection

        if self._last_type_model and self._type_changed_callback_id:
            self._last_type_model.remove_value_changed_fn(self._type_changed_callback_id)
            self._last_type_model = None
            self._type_changed_callback_id = None

        if self._last_name_model and self._name_changed_callback_id:
            self._last_name_model.remove_value_changed_fn(self._name_changed_callback_id)
            self._last_name_model = None
            self._name_changed_callback_id = None

        if has_selection:
            selected_item = items[0]
            self._selected_item = selected_item
            model_count = self._model.get_item_value_model_count(selected_item)
            name_model = self._model.get_item_value_model(selected_item, 0)
            self._variable_name_field.model = name_model
            is_category = self._model.can_item_have_children(selected_item)
            self._variable_details_stack.visible = not is_category
            if not is_category:
                type_model = self._model.get_item_value_model(selected_item, 1)
                if self._type_combo_model:
                    self._type_combo_model.target_model = type_model
                else:
                    self._variable_type_field.model = type_model

                def build_default_value_widget(value_model):
                    self._variable_default_widget_container.clear()

                    built_default_widget = False
                    if self._on_build_variable_value_widget_fn:
                        with self._variable_default_widget_container:
                            built_default_widget = self._on_build_variable_value_widget_fn(selected_item)
                            self._variable_default_stack.visible = built_default_widget

                    self._variable_default_widget.visible = not built_default_widget

                    if not built_default_widget:
                        default_value_model = (
                            self._model.get_item_value_model(selected_item, 2) if model_count > 2 else None
                        )
                        self._variable_default_stack.visible = default_value_model is not None
                        if self._variable_default_stack.visible:
                            self._variable_default_widget.model = default_value_model

                def on_type_value_change(type_model):
                    self._last_type_model = type_model
                    if self._app_gt_105_2 and self._variable_type_combo:
                        self._variable_type_combo.set_text(type_model.as_string)
                    build_default_value_widget(type_model)

                self._type_changed_callback_id = type_model.add_value_changed_fn(on_type_value_change)
                on_type_value_change(type_model)

                def on_name_value_change(name_model):
                    self._last_name_model = name_model
                    build_default_value_widget(name_model)

                self._name_changed_callback_id = name_model.add_value_changed_fn(on_name_value_change)
                on_name_value_change(name_model)

                description_model = self._model.get_item_value_model(selected_item, 3) if model_count > 3 else None
                self._variable_description_stack.visible = description_model is not None
                if self._variable_description_stack.visible:
                    self._variable_description_field.model = description_model

                category_model = self._model.get_item_value_model(self._selected_item, 4) if model_count > 4 else None
                self._variable_category_stack.visible = category_model is not None
                if self._variable_category_stack.visible:
                    self._category_combo_model.target_model = category_model

                self._delete_item_button.text = "Variable"
            else:
                self._delete_item_button.text = "Category"
        else:
            self._selected_item = None
            self._variable_name_field.model = EMPTY_STRING_MODEL
            if self._variable_type_field:
                self._variable_type_field.model = EMPTY_STRING_MODEL
            if not self._on_build_variable_value_widget_fn:
                self._variable_default_widget.model = EMPTY_STRING_MODEL
            self._variable_description_field.model = EMPTY_STRING_MODEL

    def _on_build(self):
        self._add_menu = ui.Menu("Variable Add Menu")
        with self._add_menu:

            def add_variable(weak_self):
                weak_self = weak_self()
                if not weak_self:
                    return

                if weak_self._on_add_variable_fn:
                    weak_self._on_add_variable_fn()

            self._add_variable_button = ui.MenuItem(
                "Variable",
                triggered_fn=partial(add_variable, weak_self=weakref.ref(self)),
                visible=self._on_add_variable_fn is not None,
            )

            def add_category(weak_self):
                weak_self = weak_self()
                if not weak_self:
                    return

                if weak_self._on_add_variable_category_fn:
                    weak_self._on_add_variable_category_fn()

            self._add_category_button = ui.MenuItem(
                "Category",
                triggered_fn=partial(add_category, weak_self=weakref.ref(self)),
                visible=self._on_add_variable_category_fn is not None,
            )

        with ui.HStack():
            with ui.VStack(spacing=4):
                with ui.HStack(height=0, spacing=4):

                    def on_add(weak_self):
                        weak_self = weak_self()
                        if not weak_self:
                            return

                        has_add_variable = weak_self._on_add_variable_fn is not None
                        has_add_category = weak_self._on_add_variable_category_fn is not None
                        if has_add_variable and has_add_category:
                            weak_self._add_menu.show()
                        elif has_add_variable:
                            weak_self._add_variable_button.call_triggered_fn()
                        else:
                            weak_self._add_category_button.call_triggered_fn()

                    self._add_button = ui.Button(
                        f" {omni.kit.ui.get_custom_glyph_code('${glyphs}/menu_add.svg')}  Add ",
                        width=0,
                        clicked_fn=partial(on_add, weak_self=weakref.ref(self)),
                        visible=self._on_add_variable_fn is not None or self._on_add_variable_category_fn is not None,
                    )

                    self._search_field = SearchField(show_tokens=False)

                # List Widget (on the bottom)
                with ui.ScrollingFrame(
                    horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                    vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                    style_type_name_override="TreeView",
                ):
                    self._tree_view = ui.TreeView(
                        self._model,
                        delegate=self._delegate,
                        root_visible=False,
                        header_visible=False,
                        selection_changed_fn=self._on_variable_selection_changed,
                    )

                self._variable_properties_stack = ui.VStack(height=0, spacing=4, visible=False)
                with self._variable_properties_stack:
                    ui.Label("Variable Properties", height=0)

                    with ui.VStack(spacing=4):
                        LABEL_WIDTH_PERCENT = 30
                        with ui.HStack(spacing=4):
                            ui.Label("Name", width=ui.Percent(LABEL_WIDTH_PERCENT))
                            self._variable_name_field = ui.StringField()
                        self._variable_details_stack = ui.VStack(spacing=4)
                        with self._variable_details_stack:
                            with ui.HStack(spacing=4):
                                ui.Label("Type", width=ui.Percent(LABEL_WIDTH_PERCENT))
                                if self._type_combo_model:
                                    if self._app_gt_105_2:
                                        self._variable_type_combo = build_searchable_combo_widget(
                                            self._supported_variable_types,
                                            self._type_combo_model.get_item_value_model().as_int,
                                            self._on_type_combo_clicked,
                                            18,
                                            "",
                                        )
                                    else:
                                        self._variable_type_combo = ui.ComboBox(self._type_combo_model)
                                else:
                                    self._variable_type_field = ui.StringField(
                                        enabled=False, style={"Field": {"color": 0xFF5C5C5C}}
                                    )

                            self._variable_default_stack = ui.HStack(spacing=4)
                            with self._variable_default_stack:
                                ui.Label("Default Value", width=ui.Percent(LABEL_WIDTH_PERCENT))
                                with ui.ZStack():
                                    self._variable_default_widget_container = ui.VStack(spacing=4)
                                    self._variable_default_widget = ui.StringField(
                                        enabled=False, style={"Field": {"color": 0xFF5C5C5C}}, visible=False
                                    )

                            self._variable_description_stack = ui.HStack(spacing=4)
                            with self._variable_description_stack:
                                ui.Label("Description", width=ui.Percent(LABEL_WIDTH_PERCENT))
                                self._variable_description_field = ui.StringField()

                            self._variable_category_stack = ui.HStack(spacing=4)
                            with self._variable_category_stack:
                                ui.Label("Category", width=ui.Percent(LABEL_WIDTH_PERCENT))
                                self._variable_category_combo = ui.ComboBox(self._category_combo_model)

                    with ui.HStack():
                        ui.Spacer()

                        def find_variable(weak_self):
                            weak_self = weak_self()
                            if not weak_self:
                                return

                            if weak_self._on_find_variable_reference_fn:
                                weak_self._on_find_variable_reference_fn(weak_self._selected_item)

                        self._find_variable_button = ui.Button(
                            "Find Next",
                            image_url=str(ICON_PATH.joinpath("goTo_dark.svg")),
                            style={"Button": {"stack_direction": ui.Direction.LEFT_TO_RIGHT}},
                            width=0,
                            height=0,
                            clicked_fn=partial(find_variable, weak_self=weakref.ref(self)),
                            visible=self._on_find_variable_reference_fn is not None,
                        )

                        def delete_item(weak_self):
                            weak_self = weak_self()
                            if not weak_self:
                                return

                            weak_self._model.remove_item(weak_self._selected_item)

                        self._delete_item_button = ui.Button(
                            "Variable",
                            image_url=str(ICON_PATH.joinpath("error_dark.svg")),
                            style={"Button": {"stack_direction": ui.Direction.LEFT_TO_RIGHT}},
                            width=0,
                            height=0,
                            clicked_fn=partial(delete_item, weak_self=weakref.ref(self)),
                        )

            ui.Spacer(width=10)

        # The filtering logic
        # SearchField doesn't have a way to callback in the middle of the
        # editing on_search_fn is executed when the user pressed enter. So we
        # use the model directly.
        field_model = self._search_field._search_field.model
        self._filter_subscription = field_model.subscribe_value_changed_fn(lambda m: self._filter_by_text(m.as_string))

    def _on_type_combo_clicked(self, model):
        try:
            i = self._supported_variable_types.index(model.as_string)
        except ValueError:
            return
        self._type_combo_model.get_item_value_model().set_value(i)
