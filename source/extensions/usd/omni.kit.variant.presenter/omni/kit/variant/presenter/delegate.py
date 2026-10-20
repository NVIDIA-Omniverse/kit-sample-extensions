## Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

import typing
from pathlib import Path
from typing import Optional

import carb
import omni.ui as ui
import omni.usd

from . import style
from .items import Group, Prim, Variant
from .model import Model

CURRENT_PATH = Path(__file__).parent.absolute()
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.joinpath("data/icons")


class Delegate(ui.AbstractItemDelegate):
    def __init__(self):
        self._context_menu: Optional[ui.Menu] = None
        self._variant_options: Optional[ui.Menu] = None
        self._create_menuitem: Optional[ui.MenuItem] = None
        self._delete_menuitem: Optional[ui.MenuItem] = None
        self._rename_menuitem: Optional[ui.MenuItem] = None
        self._remove_menuitem: Optional[ui.MenuItem] = None
        self._edit_menuitem: Optional[ui.MenuItem] = None
        self._select_menuitem: Optional[ui.MenuItem] = None
        self._edit_menuitem: Optional[ui.MenuItem] = None
        self._select_menuitem: Optional[ui.MenuItem] = None
        self._locate_menuitem: Optional[ui.MenuItem] = None
        self._rename_window = None
        super().__init__()

    def build_branch(
        self, model: Model, item: typing.Union[Prim, Group], column_id: int, level: int, expanded: bool
    ) -> None:
        """Create a branch widget that opens or closes subtree

        Args:
            model (Model): our Model
            item (typing.Union[Prim, Variant]): the item we are building the branch for
            column_id (int): The column (will always be 0 )
            level (int): The branch level
            expanded (bool): Is branch expanded or not
        """
        if not isinstance(item, Prim) and not isinstance(item, Group):
            return

        if column_id == 0:
            with ui.HStack(width=15 * (level + 1), height=28):
                image_name = "expanded" if expanded else "collapsed"
                with ui.ZStack():
                    with ui.VStack():
                        ui.Spacer(height=2)
                        ui.Rectangle(height=26, style_type_name_override="TreeView.Button")
                    ui.Image(
                        f"{ICON_PATH}/{image_name}.svg",
                        width=18,
                        fill_policy=ui.FillPolicy.PRESERVE_ASPECT_FIT,
                        alignment=ui.Alignment.CENTER,
                    )

    def build_widget(
        self, model: Model, item: typing.Union[Prim, Group, Variant], column_id: int, level: int, expanded: bool
    ) -> None:
        """Create a widget per column per item

        Args:
            model (Model): Our model
            item (typing.Union[Prim, Variant]): Our prim or variant data item
            column_id (int): The column (will always be 0 )
            level (int): The branch level
            expanded (bool): Branch expanded or not
        """
        value_model = model.get_item_value_model(item, 0)
        if not value_model:
            return

        if column_id == 0:
            button = None
            if isinstance(item, Prim):
                stack = ui.ZStack(height=28)
                with stack:
                    with ui.VStack():
                        ui.Spacer(height=2)
                        with ui.HStack():
                            ui.Rectangle(height=26, style_type_name_override="TreeView.Header")
                            ui.Spacer(width=2)
                    with ui.HStack():
                        ui.Spacer(width=5)
                        ui.Label(
                            value_model.get_value_as_string(),
                            name="prim_item_label",
                            tooltip=item.prim_path,
                            tooltip_offset=22,
                            word_wrap=False,
                            elided_text=True,
                            skip_draw_when_clipped=True,
                            style_type_name_override="TreeView.Header",
                        )
                        ui.Label("", width=0, alignment=ui.Alignment.RIGHT_CENTER)
                        with ui.VStack(width=20):
                            ui.Spacer(height=4)
                            prim = model.get_prim(item.prim_path)
                            url_path = None
                            if prim:
                                url_path = omni.usd.get_url_from_prim(prim)
                            if url_path:
                                button = ui.Button(
                                    "",
                                    height=20,
                                    width=20,
                                    name="EditVariantOptions",
                                    tooltip="Locate File: Locate file in content browser to edit the variant at it's source. \nOpen Variant Editor: Open the Variant Editor to edit Variant Set in the current authoring layer",
                                    clicked_fn=lambda m=model, i=item, u=url_path: self.edit_variant_options(m, i, u),
                                )
                            else:
                                button = ui.Button(
                                    "",
                                    height=20,
                                    width=20,
                                    name="EditVariant",
                                    tooltip="Open the Variant Editor to edit Variant Set in the current authoring layer.",
                                    clicked_fn=lambda m=model, i=item: self.edit_variant(m, i),
                                )
                        ui.Spacer(width=4)
                stack.set_mouse_pressed_fn(lambda x, y, b, m, i=item, t=model: self.on_mouse_pressed(b, i, t))

            if isinstance(item, Group):
                self._rename_window = RenameWindow()
                stack = ui.ZStack(height=28)
                with stack:
                    with ui.VStack():
                        ui.Spacer(height=2)
                        with ui.HStack():
                            with ui.ZStack():
                                ui.Rectangle(height=26, style_type_name_override="TreeView.Header")
                                drop = ui.Rectangle(
                                    height=26, style={"background_color": style.HEADER_HOVERED_BACKGROUND_COLOR}
                                )
                                drop.visible = False
                                item._drop = drop
                            ui.Spacer(width=2)
                    with ui.HStack():
                        ui.Spacer(width=5)
                        label = ui.Label(
                            value_model.get_value_as_string(),
                            name="group_item_label",
                            word_wrap=False,
                            elided_text=True,
                            skip_draw_when_clipped=True,
                            tooltip=value_model.get_value_as_string(),
                            style_type_name_override="TreeView.Header",
                        )
                        ui.Spacer(width=5)
                        if not " " in item.group_name:
                            ui.Label("", width=0, alignment=ui.Alignment.RIGHT_CENTER)
                            with ui.VStack(width=20):
                                ui.Spacer(height=4)
                                button = ui.Button(
                                    "",
                                    height=20,
                                    width=20,
                                    name="RemoveGroup",
                                    tooltip="Remove Group",
                                    clicked_fn=lambda m=model, i=item: self.remove_group(m, i),
                                )
                                button.visible = False
                            ui.Spacer(width=4)
                    with ui.HStack(height=28):
                        ui.Spacer(width=5)
                        field = ui.StringField(value_model, visible=False)
                stack.set_mouse_pressed_fn(lambda x, y, b, m, i=item, t=model: self.on_mouse_pressed(b, i, t))
                stack.set_mouse_double_clicked_fn(
                    lambda x, y, b, m, f=field, l=label, i=item, t=model: self.on_double_click(b, f, l, i, t)
                )
                if button:
                    stack.set_mouse_hovered_fn(lambda h, b=button: self.show_button_on_hover(h, b))

            if isinstance(item, Variant):
                stack = ui.HStack(height=30)
                with stack:
                    with ui.ZStack():
                        ui.Rectangle(style={"background_color": style.HEADER_BACKGROUND_COLOR})
                        with ui.HStack():
                            ui.Spacer(width=6)
                            with ui.ZStack(height=28):
                                ui.Rectangle(style_type_name_override="TreeView.Item")
                                with ui.HStack():
                                    if model._is_groups:
                                        self._rename_window = RenameWindow()
                                        ui.Spacer(width=4)
                                        with ui.VStack(width=28):
                                            ui.Spacer(height=2)
                                            with ui.ZStack(width=22):
                                                ui.Rectangle(
                                                    height=24,
                                                    width=16,
                                                    style={
                                                        "border_radius": 4,
                                                        "background_color": style.ITEM_BACKGROUND_COLOR,
                                                    },
                                                )
                                                ui.Image(
                                                    height=24,
                                                    width=16,
                                                    alignment=ui.Alignment.CENTER,
                                                    fill_policy=ui.FillPolicy.STRETCH,
                                                    style=style.HANDLE,
                                                )
                                    else:
                                        ui.Spacer(width=10)
                                    with ui.HStack():
                                        ui.Spacer(width=14)
                                        with ui.HStack():
                                            with ui.VStack(width=ui.Percent(35)):
                                                align = ui.Alignment.LEFT_CENTER
                                                label_height = ui.Percent(100)
                                                if model._is_groups:
                                                    ui.Label(
                                                        item.prim_path,
                                                        name="prim_path_label",
                                                        height=12,
                                                        tooltip=item.prim_path,
                                                        word_wrap=False,
                                                        elided_text=True,
                                                        skip_draw_when_clipped=True,
                                                        style={
                                                            "font_size": 10,
                                                            "color": 0xFF606060,
                                                            "margin_width": 0,
                                                            "margin": 0,
                                                            "padding": 0,
                                                        },
                                                    )
                                                    align = ui.Alignment.LEFT_TOP
                                                    label_height = 14
                                                ui.Label(
                                                    value_model.get_value_as_string(),
                                                    name="variant_item_label",
                                                    alignment=align,
                                                    height=label_height,
                                                    tooltip=item.prim_path,
                                                    tooltip_offset=22,
                                                    style_type_name_override="TreeView.Item",
                                                    word_wrap=False,
                                                    elided_text=True,
                                                    skip_draw_when_clipped=True,
                                                    content_clipping=True,
                                                )
                                            with ui.VStack(width=ui.Percent(65)):
                                                ui.Spacer(height=2)
                                                try:
                                                    from omni.kit.property.variants import variants_model
                                                except:
                                                    from omni.kit.property.usd import variants_model
                                                vset_model = variants_model.VariantSetModel(
                                                    model._stage, [item._prim.GetPath()], item._vset_name, False
                                                )
                                                combo_widget = ui.ComboBox(vset_model)
                                                combo_widget.identifier = (
                                                    f"presenter_combo_variant_{item._vset_name.lower()}"
                                                )
                                                ui.Spacer(height=2)
                                        ui.Spacer(width=2)
                                        if item.group:
                                            with ui.VStack(width=20):
                                                ui.Spacer(height=4)
                                                button = ui.Button(
                                                    height=20,
                                                    width=20,
                                                    name="RemoveVariant",
                                                    tooltip="Remove Variant From Group",
                                                    clicked_fn=lambda m=model, i=item: self.remove_variant(m, i),
                                                )
                                                button.visible = False
                                            ui.Spacer(width=2)
                                        elif model._is_groups:
                                            ui.Spacer(width=22)
                            ui.Spacer(width=6)
                        with ui.HStack():
                            if model._is_groups:
                                ui.Spacer(width=28)
                            else:
                                ui.Spacer(width=8)
                            with ui.VStack():
                                ui.Spacer(height=5)
                                lock_button = ui.Button(height=18, width=18, tooltip="Locks/Unlocks Variant.")
                        locked = ui.Rectangle(style={"background_color": style.LOCKED_OVERLAY_COLOR})
                        lock_button.set_clicked_fn(
                            lambda i=item, m=model, b=lock_button, l=locked, c=combo_widget: self.lock_variant(
                                i, m, b, l, c
                            )
                        )
                        if model.get_variant_lock_metadata(item):
                            locked.visible = True
                            lock_button.name = "LockedVariant"
                            combo_widget.enabled = False
                        else:
                            locked.visible = False
                            lock_button.name = "UnlockedVariant"
                    ui.Spacer(width=2)
                stack.set_mouse_pressed_fn(lambda x, y, b, m, i=item, t=model: self.on_mouse_pressed(b, i, t))
                if button:
                    stack.set_mouse_hovered_fn(lambda h, b=button: self.show_button_on_hover(h, b))

    def on_double_click(self, button, field, label, item, tree_model):
        """Called when the user double-clicked the item in TreeView"""
        if button != 0:
            return

        if " " in item._group_name:
            return
        # Make Field visible when double clicked
        field.visible = True
        field.focus_keyboard()
        # When editing is finished (enter pressed of mouse clicked outside of the viewport)
        self.subscription = field.model.subscribe_end_edit_fn(
            lambda m, f=field, l=label, i=item, t=tree_model: self.on_end_edit(m, f, l, i, t)
        )

    def on_end_edit(self, model, field, label, item, tree_model):
        """Called when the user is editing the item and pressed Enter or clicked outside of the item"""
        field.visible = False
        tree_model.rename_group(item, model.as_string)
        label.text = item.group_name
        self.subscription = None

    def show_button_on_hover(self, hovered, button):
        button.visible = hovered

    def lock_variant(self, item, model, button, locked, combobox):
        """Called when the create group context item is clicked"""
        if button.name == "UnlockedVariant":
            button.name = "LockedVariant"
        else:
            button.name = "UnlockedVariant"
        locked.visible = not locked.visible
        combobox.enabled = not combobox.enabled
        model.set_variant_lock_metadata(item)

    def create_group(self, model):
        """Called when the create group context item is clicked"""
        model.add_group()

    def remove_group(self, model: Model, item: Group):
        """Called when the remove group button or context item is clicked"""
        model.remove_group(item)

    def remove_variant(self, model: Model, item: Group):
        """Called when the remove variant button or context item is clicked"""
        model.remove_variant_from_group(item)

    def rename_group(self, model: Model, item: typing.Union[Group, Variant]):
        """Called when the rename group context item is clicked"""

        def on_named(new_name):
            model.rename_group(group, new_name)

        if isinstance(item, Variant):
            for g in model.groups:
                if item in g.variants:
                    group = g
                    break
        else:
            group = item
        self._rename_window.show("Rename Group", group.name_model.as_string, on_named)

    def select_prim(self, model: Model, item: typing.Union[Prim, Variant]):
        model.select_prim(item)

    def edit_variant_options(self, model: Model, item: typing.Union[Prim, Variant], url_path):
        if self._variant_options is not None:
            self._variant_options.clear()
        self._variant_options = ui.Menu(f"VARIANT OPTIONS MENU##{hash(self)}")
        with self._variant_options:
            self._edit_menuitem = ui.MenuItem("Locate File", triggered_fn=lambda i=item: self.locate_file(url_path))
            self._edit_menuitem = ui.MenuItem(
                "Open Variant Editor", triggered_fn=lambda i=item: self.edit_variant(model, item)
            )
        self._variant_options.show()

    def edit_variant(self, model: Model, item: typing.Union[Prim, Variant]):
        try:
            import omni.kit.variant.editor as ve
        except ModuleNotFoundError:
            carb.log_warn("Variant Editor extension not found.")
            return
        variant_editor_window = ve.get_window()
        if isinstance(item, Variant):
            variant_editor_window._editor_core._select_variant(item._vset, item._variant_selection)
        variant_editor_window.show()
        variant_editor_window._on_prim_picked([item.prim_path])

    def locate_file(self, url_path):
        if url_path:
            try:
                from omni.kit.window.content_browser import get_content_window

                content_browser = get_content_window()
                if content_browser:
                    content_browser.window._window.focus()
                    content_browser.navigate_to(url_path)
            except Exception as exc:
                carb.log_warn(f"find_in_browser error {exc}")

    def on_mouse_pressed(self, button: int, item: typing.Union[Prim, Group, Variant], model: Model):
        if button == 1:
            tab = None
            if isinstance(item, Variant):
                tab = model._is_groups
            if self._context_menu is not None:
                self._context_menu.clear()
            self._context_menu = ui.Menu(f"VARIANT CONTEXT MENU##{hash(self)}")
            with self._context_menu:
                if isinstance(item, Prim) or tab is not None:
                    self._edit_menuitem = ui.MenuItem(
                        "Edit Variant", triggered_fn=lambda i=item: self.edit_variant(model, item)
                    )
                    self._select_menuitem = ui.MenuItem(
                        "Select Prim In Stage", triggered_fn=lambda i=item: self.select_prim(model, item)
                    )
                if tab:
                    self._remove_menuitem = ui.MenuItem(
                        "Remove From Group", triggered_fn=lambda i=item: self.remove_variant(model, item)
                    )
                if isinstance(item, Group) or tab:
                    self._create_menuitem = ui.MenuItem(
                        "Create Group", triggered_fn=lambda i=item: self.create_group(model)
                    )
                    self._delete_menuitem = ui.MenuItem(
                        "Delete Group", triggered_fn=lambda i=item: self.remove_group(model, item)
                    )
                    self._rename_menuitem = ui.MenuItem(
                        "Rename Group", triggered_fn=lambda i=item: self.rename_group(model, item)
                    )
            self._context_menu.show()

    def _placeholder(self):
        pass


class RenameWindow(ui.Window):
    def __init__(self):
        super().__init__(
            title="Rename",
            dockPreference=ui.DockPreference.DISABLED,
            visible=False,
            flags=ui.WINDOW_FLAGS_NO_RESIZE | ui.WINDOW_FLAGS_MODAL,
            width=200,
            height=0,
        )
        self._on_renamed_fn = None

        with self.frame:
            with ui.VStack(height=0):
                self._name_field = ui.StringField(width=ui.Fraction(1))
                with ui.HStack():
                    ui.Button(text="Confirm", clicked_fn=lambda *_: self._on_confirm_rename())
                    ui.Button(text="Cancel", clicked_fn=lambda *_: self._dismiss())

    def show(self, title, old_name, on_renamed):
        self.title = title
        self._on_renamed_fn = on_renamed
        self._name_field.model.set_value(old_name)
        self.visible = True

    def _on_confirm_rename(self):
        if self._on_renamed_fn:
            self._on_renamed_fn(self._name_field.model.get_value_as_string())
        self._dismiss()

    def _dismiss(self):
        self.visible = False
