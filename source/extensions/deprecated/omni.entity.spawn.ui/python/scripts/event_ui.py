## Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##
from typing import Callable

import omni.graph.core as og
import omni.kit.commands
import omni.ui as ui
from omni.kit.property.usd import TfTokenAttributeModel
from pxr import Sdf

from .style import LABEL_WIDTH, PROPERTY_WIDGET_ALIGN_WIDTH, spawn_property_style
from .utils import get_upstream_node, get_usd_attribute_model


class EventTypeComboBoxModel(ui.AbstractItemModel):
    class Item(ui.AbstractItem):
        def __init__(self, text) -> None:
            super().__init__()

            self.model = ui.SimpleStringModel(text)

    def __init__(self, select_node: og.Node, item_names: list, offset=0):
        super().__init__()
        self._select_node = select_node
        self._offset = offset
        index = self._select_node.get_attribute("inputs:index").get()
        self.current_index = ui.SimpleIntModel(index + offset)
        self.current_index.add_value_changed_fn(lambda a: self._item_changed(None))
        self._items = [__class__.Item(text) for text in item_names]

    def _item_changed(self, arg0: ui.AbstractItem):
        transform_type_index = self.current_index.as_int - self._offset
        omni.kit.commands.execute(
            "ChangeProperty",
            prop_path=self._select_node.get_prim_path() + ".inputs:index",
            value=transform_type_index,
            prev=None,
        )
        super()._item_changed(arg0)

    def get_item_children(self, parentItem):
        return self._items

    def get_item_value_model(self, item=None, column_id: int = 0):
        if item is None:
            return self.current_index
        else:
            return item.model

    def clean(self):
        pass


def build_spawn_event_ui(widget, stage, spawn_node):
    select_node = get_upstream_node(spawn_node.get_attribute("inputs:execIn"), ["inputs:execIn"])
    if select_node:
        key_input_node = get_upstream_node(select_node.get_attribute("inputs:input0"), [])

    spawn_event_frame = ui.CollapsableFrame("Spawn Event", name="subFrame", build_header_fn=widget._build_frame_header)
    spawn_event_frame.style = spawn_property_style

    def _on_event_type_changed(model, item):
        index = model.get_item_value_model().as_int
        keyboard_args.visible = index == 0

    with spawn_event_frame:
        with ui.VStack(spacing=6):
            if not (select_node and key_input_node):
                ui.Label("Graph Modified")
                ui.Label("Use Grahph Editor or restore original connections")
                return
            with ui.HStack(height=0):
                ui.Label("Type", width=LABEL_WIDTH)
                ui.Spacer(width=PROPERTY_WIDGET_ALIGN_WIDTH)
                # Disable the Collision UI
                # select_items = ["Key Pressed", "Simulation Start", "Collision"]
                select_items = ["Key Pressed", "Simulation Start"]
                event_type_combo = ui.ComboBox(EventTypeComboBoxModel(select_node, select_items))

            keyboard_args = build_keyboard_args(stage, widget, key_input_node)
            keyboard_args.visible = event_type_combo.model.get_item_value_model().as_int == 0
            event_type_combo.model.add_item_changed_fn(_on_event_type_changed)

            with ui.HStack():
                loop_node = get_upstream_node(spawn_node.get_attribute("inputs:execIn"), [])
                attr_path = Sdf.Path(loop_node.get_prim_path() + "." + "inputs:stop")
                attr = stage.GetAttributeAtPath(attr_path)
                widget._build_usd_prop_widget(attr, "Spawn Count on Event", 1, {"min": 0})


def build_destroy_event_ui(widget, stage, spawn_node):
    all_names_attr = spawn_node.get_attribute("outputs:allSpawnedEntityNames")
    down_attrs = all_names_attr.get_downstream_connections()
    destory_node = down_attrs[0].get_node()
    exec_in_attr = destory_node.get_attribute("inputs:execIn")
    upstreams = exec_in_attr.get_upstream_connections()
    select_node = None
    branch_node = None
    for attr in upstreams:
        node_type = attr.get_node().get_type_name()
        if node_type == "omni.graph.action.Branch":
            branch_node = attr.get_node()
        elif node_type == "omni.entity.spawn.core.SelectiveGate":
            select_node = attr.get_node()
    if select_node:
        key_input_node = get_upstream_node(select_node.get_attribute("inputs:input0"), [])

    def _on_event_type_changed(model, item):
        index = model.get_item_value_model().as_int
        keyboard_args.visible = index == 1

    spawn_event_frame = ui.CollapsableFrame(
        "Destroy Event", name="subFrame", build_header_fn=widget._build_frame_header
    )
    spawn_event_frame.style = spawn_property_style

    with spawn_event_frame:
        with ui.VStack(spacing=6):
            if not (select_node and branch_node and key_input_node):
                ui.Label("Graph Modified")
                ui.Label("Use Grahph Editor or restore original connections")
                return
            with ui.HStack(height=0):
                ui.Label("Type", width=LABEL_WIDTH)
                ui.Spacer(width=PROPERTY_WIDGET_ALIGN_WIDTH)
                # Disable the Collision UI
                # select_items =  ["None", "Key Pressed", "Collision"]
                select_items = ["None", "Key Pressed"]
                event_type_combo = ui.ComboBox(EventTypeComboBoxModel(select_node, select_items, 1))

            keyboard_args = build_keyboard_args(stage, widget, key_input_node)
            keyboard_args.visible = event_type_combo.model.get_item_value_model().as_int == 1
            event_type_combo.model.add_item_changed_fn(_on_event_type_changed)

            condition_attr = branch_node.get_attribute("inputs:condition")
            attr = stage.GetAttributeAtPath(Sdf.Path(condition_attr.get_path()))
            widget._build_usd_prop_widget(attr, "Destroy All Entities When Simulation Ends")


def build_keyboard_args(stage, widget, key_input_node):
    keyboard_args = ui.HStack(spacing=0)
    with keyboard_args:

        def build_modify_key(attr_name, disaply_name):
            path, model = get_usd_attribute_model(stage, key_input_node, attr_name)
            ui.CheckBox(model, width=0)
            ui.Label(disaply_name)
            widget._models[path].append(model)
            return model

        ui.Label("Key Binding", width=LABEL_WIDTH)
        ui.Spacer(width=PROPERTY_WIDGET_ALIGN_WIDTH)

        ctrl_model = build_modify_key("inputs:ctrlIn", " Ctrl")
        alt_model = build_modify_key("inputs:altIn", " Alt")
        shift_model = build_modify_key("inputs:shiftIn", " Shift")

        key_path, key_model = get_usd_attribute_model(stage, key_input_node, "inputs:keyIn", TfTokenAttributeModel)
        ui.ComboBox(key_model)
        widget._models[key_path].append(key_model)

        ui.Spacer()

        def is_value_default():
            return not (
                ctrl_model.as_bool
                or alt_model.as_bool
                or shift_model.as_bool
                or key_model.get_value_as_token() != key_model._get_value_from_index(0)
            )

        def set_value_default():
            if ctrl_model.as_bool:
                ctrl_model.set_value(False)
            if alt_model.as_bool:
                alt_model.set_value(False)
            if shift_model.as_bool:
                shift_model.set_value(False)
            key_token = key_model._get_value_from_index(0)
            if key_model.get_value_as_token() != key_token:
                key_model.set_value(key_token)

        def on_value_changed(model, item=None):
            default_button.rebuild()

        default_button = build_default_button(is_value_default, set_value_default)
        default_button.rebuild()

        ctrl_model.add_value_changed_fn(on_value_changed)
        alt_model.add_value_changed_fn(on_value_changed)
        shift_model.add_value_changed_fn(on_value_changed)
        key_model.add_item_changed_fn(on_value_changed)

    return keyboard_args


def build_default_button(is_value_default_fn: Callable, set_value_default_fn: Callable):
    def on_clicked(x, y, b, m):
        if is_value_default_fn():
            return
        set_value_default_fn()

    def build_fn():
        if is_value_default_fn():
            height = 5
            icon_name = "default_value"
        else:
            height = 12
            icon_name = "changed_value"

        with ui.VStack():
            ui.Spacer()
            ui.Image(
                name=icon_name,
                mouse_pressed_fn=on_clicked,
                width=12,
                height=height,
            )
            ui.Spacer()

    frame = ui.Frame(width=0)
    frame.set_build_fn(build_fn)
    return frame
