# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = []

import asyncio

import carb
import omni.kit.app
import omni.kit.commands
import omni.ui as ui
from omni.kit.property.usd.prim_path_widget import Constant
from omni.kit.window.property.style import get_style
from omni.kit.window.property.templates import LABEL_HEIGHT, ButtonItem
from pxr import Tf, Usd


class AddSchemaAPIPopup:
    def __init__(self):
        self._api_instance_types = {
            "OmniGraphInputDefAPI": ["input1", "input2"],
            "OmniGraphOutputDefAPI": ["value"],
            "CollectionAPI": [
                "leafGeom",
                "allGeom",
                "allGeomProperties",
                "hasRelationships",
                "hasInstanceProxy",
                "coneProperties",
                "includesCollection",
                "excludeInstanceGeom",
                "invalidExpansionRule",
                "invalidExcludesExplicitOnly",
                "invalidExcludesExpandPrims",
                "invalidTopLevelRules",
                "allShapes",
                "lightLink",
            ],
            # these don't have fixed instance names
            "SemanticsAPI": [],
            "CoordSysAPI": [],
        }
        self._hooks = []
        self._window = None

    def __del__(self):  # pragma: no cover
        for h in self._hooks:
            omni.kit.commands.unregister_callback(h)
        self._hooks = []

    def destroy(self):
        if self._window:
            self._window.destroy()
            self._window = None

    def show_window(self, payload, cls_name):
        import omni.kit.commands
        from omni.kit.property.usd import PrimPathWidget, RegisteredSchemaCodes, is_registered_schema

        def cmd_callback(cmd, payload, cls_name):
            async def refresh_window():
                await omni.kit.app.get_app().next_update_async()
                self.show_window(payload, cls_name)

            asyncio.ensure_future(refresh_window())

        # remove and add command callback hooks
        for h in self._hooks:
            omni.kit.commands.unregister_callback(h)
        self._hooks = []
        self._hooks.append(
            omni.kit.commands.register_callback(
                "AppendAPIToPrims",
                omni.kit.commands.POST_DO_CALLBACK,
                lambda c, p=payload, n=cls_name: cmd_callback(c, p, n),
            )
        )
        self._hooks.append(
            omni.kit.commands.register_callback(
                "AppendAPIToPrims",
                omni.kit.commands.POST_UNDO_CALLBACK,
                lambda c, p=payload, n=cls_name: cmd_callback(c, p, n),
            )
        )
        self._hooks.append(
            omni.kit.commands.register_callback(
                "RemoveAPIFromPrims",
                omni.kit.commands.POST_DO_CALLBACK,
                lambda c, p=payload, n=cls_name: cmd_callback(c, p, n),
            )
        )
        self._hooks.append(
            omni.kit.commands.register_callback(
                "RemoveAPIFromPrims",
                omni.kit.commands.POST_UNDO_CALLBACK,
                lambda c, p=payload, n=cls_name: cmd_callback(c, p, n),
            )
        )

        # get schema APIs
        stage = payload.get_stage()
        prims = [stage.GetPrimAtPath(pp) for pp in payload]
        prims = [prim for prim in prims if prim]

        api_types = []
        schema_placeholder_msg = "Select API Schema to apply..."

        schema_reg = Usd.SchemaRegistry()
        for t in Tf.Type.FindByName("UsdAPISchemaBase").GetAllDerivedTypes():
            if not t.isUnknown and schema_reg.IsAppliedAPISchema(t):
                api_schema = schema_reg.GetAPISchemaTypeName(t)

                # ignore private APIs
                _, schema_codes = is_registered_schema([cls_name], api_schema)
                if schema_codes & (RegisteredSchemaCodes.PRIVATE | RegisteredSchemaCodes.NO_CREATE):
                    continue

                if not schema_reg.IsMultipleApplyAPISchema(t):
                    allowed_prims = schema_reg.GetAPISchemaCanOnlyApplyToTypeNames(api_schema)
                    if not allowed_prims or any(
                        prim.IsA(allowed_prim) for allowed_prim in allowed_prims for prim in prims
                    ):
                        api_types.append(api_schema)
                elif api_schema in self._api_instance_types:
                    for instance in self._api_instance_types[api_schema]:
                        allowed_prims = schema_reg.GetAPISchemaCanOnlyApplyToTypeNames(api_schema, instance)
                        if not allowed_prims or any(
                            prim.IsA(allowed_prim) for allowed_prim in allowed_prims for prim in prims
                        ):
                            api_types.append(f"{api_schema}:{instance}")

        if not self._window:
            self._window = ui.Window("Edit API Schema", visible=True, width=400, height=400)
        self._window.frame.clear()
        if not prims:
            return

        self._window.visible = True
        with self._window.frame:
            with ui.ScrollingFrame(
                horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
            ):
                with ui.VStack(height=0, spacing=5, style=get_style()):
                    with ui.HStack(height=0):
                        ui.Spacer(width=8)
                        ui.Label(
                            "Apply API:",
                            name="stage_label",
                            width=Constant.LABEL_WIDTH + PrimPathWidget.get_path_item_padding(),
                            height=LABEL_HEIGHT,
                            style={"font_size": Constant.LABEL_FONT_SIZE},
                        )
                        ui.Spacer(width=8)

                        def combochanged(model):
                            api_schema_full = model.get_value_as_string()
                            if api_schema_full == schema_placeholder_msg:
                                return

                            if api_schema_full:
                                api_schema, api_instance = schema_reg.GetTypeNameAndInstance(api_schema_full)
                                omni.kit.commands.execute(
                                    "AppendAPIToPrims",
                                    paths=payload.get_paths(),
                                    api_schema=api_schema,
                                    api_instance=api_instance,
                                )

                        api_types.sort()
                        # combobox
                        import omni.kit.widget.searchable_combobox
                        from omni.kit.widget.searchable_combobox import (
                            ComboBoxListDelegate,
                            ComboBoxListModel,
                            ComboListBoxWidget,
                            SearchWidget,
                            build_searchable_combo_widget,
                        )

                        def create_searchable_combo_box():
                            # Create the searchable combo box with the specified items and callback
                            class SchemaSearchWidget(SearchWidget):
                                def build_ui_popup(
                                    self,
                                    search_size: float,
                                    default_value: str,
                                    popup_text: str,
                                    index: int,
                                    update_fn: callable,
                                ):
                                    """Builds Combobox like widget when 'open' button is clicked."""

                                    def clear_name(name_field):
                                        name_field.model.set_value(default_value)
                                        if update_fn:
                                            update_fn(name_field.model)

                                    self._update_fn = update_fn
                                    open_button = None
                                    name_field = None

                                    with omni.ui.VStack(height=0, spacing=0, style={"margin_width": 0}):
                                        with ui.HStack(style=self._style, height=search_size):
                                            name_field = ui.StringField(enabled=False)
                                            name_field.model.set_value(popup_text)
                                            open_button = ui.Button("", width=20, image_width=8, name="listbox")

                                    self._search_field = name_field
                                    return name_field, open_button

                                def build_ui(self, width, search_size):
                                    """Build UI for SearchWidget."""

                                    def clear_name(field):
                                        field.model.set_value("")
                                        field.focus_keyboard()

                                    with ui.HStack(width=0, height=search_size, style=self._style):
                                        ui.Rectangle(
                                            width=4,
                                            style={
                                                "background_color": 0xFF2D2D2D,
                                                "border_radius": 4,
                                                "corner_flag": ui.CornerFlag.LEFT,
                                            },
                                        )
                                        ui.Button(
                                            "",
                                            width=14,
                                            enabled=False,
                                            name="search_button",
                                            style={
                                                "margin": 0,
                                                "padding": 0,
                                                "border_radius": 0,
                                                "background_color": 0xFF2D2D2D,
                                            },
                                        )
                                        with ui.ZStack(width=0, height=0):
                                            with ui.HStack(width=0, height=search_size):
                                                field = ui.StringField(
                                                    model=self._search_model,
                                                    width=width - 46,
                                                    name="search_button",
                                                    style={"border_radius": 0, "margin": 0},
                                                )
                                                self._search_clear = ui.Button(
                                                    "",
                                                    width=22,
                                                    fill_policy=ui.FillPolicy.PRESERVE_ASPECT_FIT,
                                                    enabled=False,
                                                    clicked_fn=lambda f=field: clear_name(f),
                                                    name="remove",
                                                    style={"border_radius": 4, "corner_flag": ui.CornerFlag.RIGHT},
                                                )
                                            self._placeholder = ui.Label("  Search....", name="search_placeholder")
                                            self._field = field
                                            self.focus()

                            class SchemaComboListBoxWidget(ComboListBoxWidget):
                                def __init__(
                                    self,
                                    search_widget,
                                    item_list: list,
                                    theme: str,
                                    window_id: str = "SearchableComboBoxWindow",
                                    delegate: ui.AbstractItemDelegate = ComboBoxListDelegate(),
                                ):
                                    super().__init__(search_widget, item_list, theme, window_id, delegate)

                                    icon_path = f"{omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module('omni.kit.widget.searchable_combobox')}/data/icons"
                                    self._search_widget = SchemaSearchWidget(
                                        theme=theme, icon_path=icon_path, modified_fn=self._search_updated
                                    )

                            def build_searchable_combo_widget(
                                combo_list: list[str],
                                combo_index: int,
                                combo_click_fn: callable,
                                widget_height: int,
                                default_value: str,
                                window_id: str = "SearchableComboBoxWindow",
                                delegate: ui.AbstractItemDelegate = ComboBoxListDelegate(),
                            ) -> SearchWidget:
                                theme = (
                                    carb.settings.get_settings().get_as_string("/persistent/app/window/uiStyle")
                                    or "NvidiaDark"
                                )

                                def show_combo_popup(
                                    search_widget: SearchWidget,
                                    name_field: ui.StringField,
                                    combo_index: int,
                                    combo_click_fn: callable,
                                ):
                                    window = ui.Workspace.get_window(window_id)
                                    if window:
                                        window.visible = False
                                        return

                                    listbox_widget = SchemaComboListBoxWidget(
                                        search_widget=search_widget,
                                        item_list=combo_list,
                                        window_id=window_id,
                                        delegate=delegate,
                                        theme=theme,
                                    )
                                    listbox_widget.set_parent(name_field)
                                    listbox_widget.build_ui()

                                search_widget = SchemaSearchWidget(theme=theme, icon_path=None)
                                name_field, listbox_button = search_widget.build_ui_popup(
                                    search_size=widget_height,
                                    default_value=default_value,
                                    popup_text=combo_list[combo_index] if combo_index >= 0 else default_value,
                                    index=combo_index,
                                    update_fn=combo_click_fn,
                                )

                                name_field.set_mouse_pressed_fn(
                                    lambda x, y, b, m, s=search_widget, f=name_field: show_combo_popup(
                                        s, f, combo_index, combo_click_fn
                                    )
                                )
                                listbox_button.set_mouse_pressed_fn(
                                    lambda x, y, b, m, s=search_widget, f=name_field: show_combo_popup(
                                        s, f, combo_index, combo_click_fn
                                    )
                                )

                                return search_widget

                            return build_searchable_combo_widget(
                                combo_list=api_types,
                                combo_index=-1,  # Start with no item selected
                                combo_click_fn=combochanged,
                                widget_height=18,
                                default_value=schema_placeholder_msg,
                                window_id="APISearchWindow",
                                delegate=ComboBoxListDelegate(),  # Use the default delegate for item rendering
                            )

                        create_searchable_combo_box()

                    self._build_schema_group_frames(payload, stage, cls_name, prims)

        if not self._window.visible:
            self._window.visible = True

    def _build_frame_header_with_buttons(self, frame: ui.Frame, text: str, group_id: str, button_list: list):
        frame.collapsed = True

        header_stack = ui.HStack(spacing=8)
        with header_stack:
            with ui.VStack(width=0):
                ui.Spacer()
                ui.Spacer()
            ui.Label(text, style_type_name_override="CollapsableFrame.Header")
            ui.Spacer()
            with ui.HStack(content_clipping=True, width=0):
                for button in button_list:
                    ui.Spacer(width=8)
                    if button.icon:
                        ui.Button(
                            width=button.width,
                            height=button.height,
                            clicked_fn=button.callback_fn,
                            style={"image_url": button.icon},
                            enabled=button.enabled,
                        )
                    else:
                        ui.Button(
                            button.text,
                            width=button.width,
                            height=button.height,
                            clicked_fn=button.callback_fn,
                            identifier=f"{text}.remove_api_schema_button",
                        )

    def _build_schema_group_frames(self, payload, stage, cls_name, prims):
        from omni.kit.property.usd import RegisteredSchemaCodes, is_registered_schema
        from omni.kit.property.usd.widgets import ICON_PATH

        if stage:

            def delete_api(api_schema_full):
                api_schema, api_instance = schema_reg.GetTypeNameAndInstance(api_schema_full)
                omni.kit.commands.execute(
                    "RemoveAPIFromPrims",
                    paths=payload.get_paths(),
                    api_schema=api_schema,
                    api_instance=api_instance,
                )

            schema_reg = Usd.SchemaRegistry()
            icon_path = f"{ICON_PATH}/Locked Value.svg"
            schema_list = []

            ui.Spacer(height=4)
            ui.Separator(height=8)
            ui.Label("Applied APIs", style={"color": 0xFF9E9E9E, "font_size": 16}, alignment=ui.Alignment.CENTER)
            ui.Spacer(height=1)

            applied_schemas = prims[-1].GetAppliedSchemas()
            if applied_schemas:
                for api_schema_full in applied_schemas:
                    api_schema, api_instance = schema_reg.GetTypeNameAndInstance(api_schema_full)
                    schema_group_id = f"Schema:{api_schema_full}"
                    schema_types = [cls_name, prims[-1].GetTypeName()]

                    # ignore private APIs
                    widget_name, schema_codes = is_registered_schema(schema_types, api_schema_full)
                    if schema_codes & RegisteredSchemaCodes.PRIVATE:
                        continue

                    if schema_codes & RegisteredSchemaCodes.NO_REMOVE and widget_name in schema_types:
                        button_item = ButtonItem(icon=icon_path, width=16, height=16, enabled=False)
                    else:
                        button_item = ButtonItem(
                            "Remove", width=16, height=16, callback_fn=lambda s=api_schema_full: delete_api(s)
                        )

                    sframe = ui.CollapsableFrame(
                        title=api_schema_full,
                        name="schemaFrame",
                        collapsed=True,
                    )
                    sframe.set_build_header_fn(
                        lambda collapsed, text, id=schema_group_id, bi=[
                            button_item
                        ], f=sframe: self._build_frame_header_with_buttons(f, text, id, bi)
                    )
