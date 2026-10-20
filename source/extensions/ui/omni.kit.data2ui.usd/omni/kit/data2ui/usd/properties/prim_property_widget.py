# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from dataclasses import dataclass
from typing import List, Optional, Type

import carb.settings
import omni.ui as ui
from omni.kit.actions.core import Action
from omni.kit.actions.window import (
    ActionDetailItem,
    ActionsDelegate,
    ActionsModel,
    ActionsView,
    ColumnRegistry,
    StringColumnDelegate,
)
from omni.kit.property.usd import UsdAttributeModel, UsdPropertiesWidget, UsdPropertiesWidgetBuilder, UsdPropertyUiEntry
from omni.kit.widget.highlight_label import HighlightLabel
from pxr import Sdf, Usd

from ..prims import PRIM_NS
from ..prims.valid import valid_ui_prim_types
from .prim_properties import ATTR_NS, DISABLED_PROPERTY, all_prim_style_properties, prim_properties


def _get_plus_glyph():
    return ui.get_custom_glyph_code("${glyphs}/menu_add.svg")


def _get_remove_glyph():
    return ui.get_custom_glyph_code("${glyphs}/menu_delete.svg")


def _get_alignment():
    settings = carb.settings.get_settings()
    return (
        ui.Alignment.RIGHT
        if settings.get("/ext/omni.kit.window.property/labelAlignment") == "right"
        else ui.Alignment.LEFT
    )


def get_model_cls(cls, args, key="model_cls") -> Type[UsdAttributeModel]:
    if args:
        return args.get(key, cls)
    return cls


def get_model_kwargs(args, key="model_kwargs"):
    if args:
        return args.get(key, {})
    return {}


def events_list(stage) -> List[str]:
    # OmniGraph > OmniGraphNode > Inputs > Event Name ('inputs:eventName')
    # Kit 111's usdrt stage has no Fabric query API: read the OmniGraph nodes from the USD stage.
    graphs = [prim for prim in stage.Traverse() if prim.GetTypeName() == "OmniGraphNode"]
    events = list(
        {
            node.GetAttribute("inputs:eventName").Get()
            for node in graphs
            if (
                node.HasAttribute("inputs:eventName")
                and node.GetAttribute("node:type").Get() == "omni.graph.action.OnCustomEvent"
            )
        }
    )
    if "" not in events:
        events.append("")
    return sorted(events)


@dataclass
class Event:
    name: str


class EventItem(ui.AbstractItem):
    def __init__(self, event):
        super().__init__()
        self.model = ui.SimpleStringModel(event)


class EventsComboModel(ui.AbstractItemModel):
    def __init__(self, stage):
        super().__init__()
        self._stage = stage

        self._current_index = ui.SimpleIntModel()
        self._current_index.add_value_changed_fn(lambda a: self._item_changed(None))  # type: ignore

        self._items = [EventItem(event) for event in events_list(self._stage)]

    def get_item_children(self, item):
        return self._items

    def get_item_value_model(self, item: EventItem, column_id):
        if item is None:
            return self._current_index
        return item.model

    def set_value(self, value):
        for i, event in enumerate(self._items):
            if event.model.as_string == value:
                return self._current_index.set_value(i)
        self._current_index.set_value(-1)


class Data2UISchemaPropertiesWidget(UsdPropertiesWidget):
    def __init__(self, title: str, collapsed: bool, multi_edit: bool = True):
        """
        Constructor.

        Args:
            title: title of the widget.
            collapsed: whether the collapsable frame should be collapsed for this widget.
            multi_edit: whether multi-editing is supported.
                If False, properties will only be collected from the last selected prim.
                If True, shared properties among all selected prims will be collected.
        """
        self._title = title
        super().__init__(title=title, collapsed=collapsed, multi_edit=multi_edit)

    def _show_add_ui_style_property_context_menu(self):
        from ..prims.prim_style_properties import prims_add_style_property, prims_allows_style_property

        prims_list: list[Usd.Prim] = [prim for p in self._payload or [] if (prim := self._get_prim(p))]

        self._add_ui_style_property_context_menu = ui.Menu()
        with self._add_ui_style_property_context_menu:
            for prop in all_prim_style_properties:
                if prims_allows_style_property(None, prims_list, prop):

                    def triggered(prims_list=prims_list, prop=prop):
                        prims_add_style_property(None, prims_list, prop)

                    ui.MenuItem(
                        prop,
                        triggered_fn=triggered,
                    )
        self._add_ui_style_property_context_menu.show()

    def _show_remove_ui_style_property_context_menu(self):
        from ..prims.prim_style_properties import prims_remove_style_property

        prims_list: list[Usd.Prim] = [self._get_prim(p) for p in self._payload or []]  # type: ignore
        properties = set()
        for prim in prims_list:
            attr_names = [attr.GetName() for attr in prim.GetAttributes() or []]
            for attr_name in attr_names:
                if attr_name.startswith(f"{ATTR_NS}:Style:"):
                    properties.add(attr_name.split(":")[-1])
        properties = list(properties)

        self._remove_ui_style_property_context_menu = ui.Menu()
        with self._remove_ui_style_property_context_menu:
            for property_name in properties:
                ui.MenuItem(
                    property_name,
                    triggered_fn=lambda prims_list=prims_list, property_name=property_name: prims_remove_style_property(
                        None, prims_list, property_name
                    ),
                )
        self._remove_ui_style_property_context_menu.show()

    def _build_frame_header(self, collapsed, text, id_str: str | None = None):
        if collapsed:
            alignment = ui.Alignment.RIGHT_CENTER
            width = 5
            height = 7
        else:
            alignment = ui.Alignment.CENTER_BOTTOM
            width = 7
            height = 5

        with ui.HStack(spacing=8):
            with ui.VStack(width=0):
                ui.Spacer()
                ui.Triangle(
                    style_type_name_override="CollapsableFrame.Header", width=width, height=height, alignment=alignment
                )
                ui.Spacer()
            ui.Label(text, style_type_name_override="CollapsableFrame.Header")
            if id_str in [f"{self._title}:Style", f"{self._title}:StyleSelector"] or id_str is None:
                with ui.HStack(width=0):
                    ui.Spacer(width=8)
                    with ui.HStack(width=0):
                        ui.Spacer(height=5)
                        with ui.ZStack(content_clipping=True):
                            ui.Button(
                                f"{_get_plus_glyph()} Add",
                                height=16,
                                width=16,
                                opaque_for_mouse_events=True,
                                clicked_fn=self._show_add_ui_style_property_context_menu,
                            )
                        ui.Spacer(width=5)

        return None

    def on_new_payload(self, payload):
        """
        Prevent Data2UI Widget Frame from being created if any selected prim is not a UI prim
        """
        if not super().on_new_payload(payload) or not payload._payload:
            return False

        for prim_path in self._payload or []:
            prim = self._get_prim(prim_path)
            prim_type: str = prim.GetTypeName()  # type: ignore
            if PRIM_NS not in prim_type:
                return False
            prim_type = prim_type.split(PRIM_NS)[1]
            if prim_type not in valid_ui_prim_types:
                return False

        return True

    def _customize_props_layout(self, attrs: List[UsdPropertyUiEntry]):
        from omni.kit.property.usd.custom_layout_helper import (
            CustomLayoutFrame,
            CustomLayoutGroup,
            CustomLayoutProperty,
        )

        class CustomLayoutCallableProperty(CustomLayoutProperty):
            def _on_search_action(self, action: Action, word: str) -> bool:
                return any(
                    word.lower() in string.lower()
                    for string in (
                        action.extension_id,
                        action.id,
                        action.display_name,
                        action.description,
                        action.tag,
                        action.icon_url,
                    )
                )

            def _on_search(self, search_words: Optional[List[str]]) -> None:
                self._scroll_frame.visible = True
                self._actions_model.search(search_words)
                self._actions_view.set_expanded(None, True, True)  # type: ignore

            def _register_column_delegates(self):
                self._column_registry.register_delegate(StringColumnDelegate("Action", width=ui.Pixel(200)))

            def _callable_builder(
                self,
                stage,
                attr_name,
                type_name,
                metadata,
                prim_paths: List[Sdf.Path],
                additional_label_kwargs=None,
                additional_widget_kwargs=None,
            ):
                from omni.kit.actions.window.style import ACTIONS_WINDOW_STYLE
                from omni.kit.window.property.templates import HORIZONTAL_SPACING

                with ui.HStack(spacing=HORIZONTAL_SPACING):
                    display_name = attr_name.split(":")[-1]
                    with ui.HStack(width=160):
                        label = HighlightLabel(
                            display_name,
                            name="label",
                            word_wrap=True,
                            width=ui.Pixel(0),
                            height=ui.Pixel(0),
                            alignment=_get_alignment(),
                        )
                        ui.Spacer()

                    self._model_cls = get_model_cls(UsdAttributeModel, additional_widget_kwargs)
                    self._actual_model = self._model_cls(stage, [path.AppendProperty(attr_name) for path in prim_paths], False, {})  # type: ignore
                    widget_kwargs = {"name": "string"}
                    if additional_widget_kwargs:
                        widget_kwargs.update(additional_widget_kwargs)
                    self._actual_stringfield = ui.StringField(self._actual_model, **widget_kwargs)
                    self._actual_stringfield.visible = False

                    self._column_registry = ColumnRegistry()
                    self._register_column_delegates()

                    self._actions_model = ActionsModel(
                        self._column_registry, on_search_action_fn=self._on_search_action
                    )

                    self._actions_delegate = ActionsDelegate(self._actions_model, self._column_registry)

                    def update_search_label_color():
                        if self._search_widget._search_label and self._search_widget._container:
                            label_text = self._search_widget._search_label.text
                            if label_text.startswith("Action("):
                                label_color = ui.color(0.8, 0.8, 0.8, 1.0)
                            else:
                                label_color = ui.color(0.3, 0.3, 0.3, 1.0)
                            style: dict = self._search_widget._container.style  # type: ignore
                            style["SearchField.Hint"] = {"color": label_color}
                            self._search_widget._container.set_style(style)

                    def execute(item: ActionDetailItem):
                        self._actions_view.set_expanded(None, False, True)  # type: ignore
                        self._scroll_frame.visible = False

                    def on_mouse_double_click(button, item, column_delegate):
                        self._actual_stringfield.model.set_value(f"Action({item.action.extension_id!r}, {item.id!r})")
                        if self._search_widget._search_label:
                            self._search_widget._search_label.text = (
                                f"Action({item.action.extension_id!r}, {item.id!r})"
                            )
                        self._search_widget._set_in_searching(False)
                        self._search_widget._ignore_text_update = True
                        self._search_widget._search_field.model.set_value("")
                        self._search_widget._ignore_text_update = False
                        self._actions_model.execute(item)
                        update_search_label_color()

                    self._actions_model.execute = execute
                    self._actions_delegate.on_mouse_double_click = on_mouse_double_click

                    def event_combobox_changed(combo_model, item):
                        all_options = [
                            combo_model.get_item_value_model(child, 0).as_string
                            for child in combo_model.get_item_children(item)
                        ]
                        default_value_model = combo_model.get_item_value_model(
                            combo_model.get_item_children(item)[0], 0
                        )
                        index_model = combo_model.get_item_value_model(item, 0)
                        # When the index is -1, it means the current serialized data does not match against events in the stage.
                        # Instead of wiping out the data, we're going to use it as the default option in the combobox and
                        # prefix it with Unknown. Only changing the serialized data if the user explicity changes things.
                        current_index = index_model.as_int
                        if index_model.as_int == -1:
                            if not default_value_model.as_string:
                                default_value_model.as_string = f"Unknown{self._actual_stringfield.model.as_string}"
                            index_model.as_int = 0
                            return

                        # We do not want to mess with the serialized value if the event is unknown
                        if default_value_model.as_string.startswith("Unknown"):
                            return

                        if all_options[current_index] != "":
                            # default_value_model.as_string = ""
                            self._actual_stringfield.model.set_value(
                                f"Event('omni.graph.action.{all_options[current_index]}')"
                            )
                        else:
                            self._actual_stringfield.model.set_value("")
                        update_search_label_color()

                    def toggle_searchmode():
                        self._search_toggle.text = "Events" if self._search_widget.enabled else "Actions"
                        self._search_widget.enabled = not self._search_widget.enabled
                        self._search_widget.visible = self._search_widget.enabled
                        self._scroll_frame.visible = False
                        self._scroll_frame.enabled = self._search_widget.enabled
                        self._actions_view.enabled = self._search_widget.enabled

                        if self._events_combobox.enabled and self._search_widget._search_label:
                            if self._search_widget._search_label.text.startswith("Action("):
                                self._actual_stringfield.model.set_value(self._search_widget._search_label.text)

                        self._events_combobox.enabled = not self._events_combobox.enabled
                        self._events_combobox.visible = self._events_combobox.enabled
                        if self._events_combobox.enabled:
                            event_combobox_changed(self._events_combobox.model, None)
                        update_search_label_color()

                    with ui.HStack():
                        ui.Spacer(width=9, height=12)
                        self._search_toggle = ui.Button(
                            "Actions",
                            width=24,
                            height=24,
                            tooltip="Toggle Search between Actions and Events",
                            clicked_fn=lambda: toggle_searchmode(),
                        )
                        ui.Spacer(width=4)
                        with ui.ZStack():
                            from omni.kit.widget.searchfield import SearchField

                            with ui.VStack(spacing=4):
                                self._search_widget = SearchField(
                                    on_search_fn=self._on_search,
                                    subscribe_edit_changed=True,
                                    style=ACTIONS_WINDOW_STYLE,
                                    show_tokens=False,
                                )
                                if self._search_widget._search_label:
                                    if self._actual_stringfield.model.as_string.startswith("Action("):
                                        self._search_widget._search_label.text = (
                                            self._actual_stringfield.model.as_string
                                        )
                                    else:
                                        self._search_widget._search_label.text = "Search Actions"
                                self._scroll_frame = ui.ScrollingFrame(
                                    height=300,
                                    horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                                    vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_ON,
                                    style_type_name_override="ActionsView",
                                )
                                with self._scroll_frame:
                                    self._actions_view = ActionsView(self._actions_model, self._actions_delegate)
                                self._scroll_frame.visible = False

                            with ui.VStack(spacing=4):
                                self._events_combo_model = EventsComboModel(stage)
                                self._events_combobox = ui.ComboBox(
                                    self._events_combo_model,
                                )
                                self._events_combobox.model.add_item_changed_fn(event_combobox_changed)
                                self._events_combobox.enabled = False
                                self._events_combobox.visible = False

                            if self._actual_stringfield.model.as_string.startswith("Event("):
                                selection = self._actual_stringfield.model.as_string
                                try:
                                    evt = eval(selection)
                                except SyntaxError:
                                    eventname = selection.split("omni.graph.action.")[1][:-1]
                                    self._events_combo_model.set_value(eventname)
                                else:
                                    match evt:
                                        case Event(name):
                                            eventname = name.replace("omni.graph.action.", "")
                                            self._events_combo_model.set_value(eventname)

                                toggle_searchmode()

                            update_search_label_color()

                        ui.Spacer(width=16, height=12)

                return self._actual_stringfield.model

            def __init__(self, prop_name, display_name=None, build_fn=None, hide_if_true=None, show_if_true=None):
                super().__init__(prop_name, display_name, build_fn, hide_if_true, show_if_true)
                self._build_fn = self._callable_builder

        def build_fn(
            stage,
            attr_name,
            metadata,
            property_type,
            prim_paths: List[Sdf.Path],
            additional_label_kwargs=None,
            additional_widget_kwargs=None,
        ):
            try:
                disabled = metadata.get("customData", {}).get(DISABLED_PROPERTY, False)
            except AttributeError:
                disabled = False

            if additional_label_kwargs is None:
                additional_label_kwargs = {}
            if additional_widget_kwargs is None:
                additional_widget_kwargs = {}
            additional_label_kwargs["enabled"] = not disabled
            additional_widget_kwargs["enabled"] = not disabled
            additional_widget_kwargs["visible"] = not disabled
            return UsdPropertiesWidgetBuilder.build(
                stage, attr_name, metadata, property_type, prim_paths, additional_label_kwargs, additional_widget_kwargs
            )

        # TODO: Figure out how to sort when prims of multiple types are selected
        sections = sorted(
            {
                attr.attr_name.split(f"{ATTR_NS}:")[1].split(":")[0]
                for attr in attrs
                if attr.attr_name.startswith(f"{ATTR_NS}:")
            }
        )
        style_exists = "Style" in sections
        style_selector_exists = "StyleSelector" in sections
        nonstyle_sections = [section for section in sections if section not in ("Style", "StyleSelector")]

        frame = CustomLayoutFrame(hide_extra=True)

        # Short-circuit if there are not Data2UI attribs
        if not sections:
            return []

        with frame:
            for section in nonstyle_sections:
                with CustomLayoutGroup(section):
                    attr_order = list(prim_properties.get(section, {}).keys())
                    for _attr in attr_order:
                        display_name = _attr
                        if _attr.endswith("_fn"):
                            CustomLayoutCallableProperty(f"{ATTR_NS}:{section}:{_attr}", _attr)
                        else:
                            CustomLayoutProperty(f"{ATTR_NS}:{section}:{_attr}", _attr, build_fn=build_fn)

            if style_selector_exists:
                with CustomLayoutGroup("StyleSelector"):
                    for attr_name in ["type_name", "name", "state"]:
                        for attr in attrs:
                            if attr.attr_name == f"{ATTR_NS}:StyleSelector:{attr_name}":
                                CustomLayoutProperty(attr.attr_name, attr_name, build_fn=build_fn)
            if style_exists:
                with CustomLayoutGroup("Style"):
                    for attr in attrs:
                        if attr.attr_name.startswith(f"{ATTR_NS}:Style"):
                            display_name = attr.attr_name.replace(f"{ATTR_NS}:Style:", "")
                            CustomLayoutProperty(attr.attr_name, display_name, build_fn=build_fn)

        return frame.apply(attrs)
