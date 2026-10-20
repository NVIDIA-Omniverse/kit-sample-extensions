# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import weakref
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

import carb.settings
import omni.kit.app
import omni.ui as ui
from omni.kit.async_engine import run_coroutine
from omni.kit.markup.core import MarkupItem, ViewportMarkup
from omni.kit.markup.core.extension import MarkupChangeCallbacks
from omni.kit.markup.core.extension import get_instance as get_markup_extension_instance
from omni.kit.markup.core.widgets.hover import MarkupItemHoverWidget
from omni.kit.viewport.utility import get_active_viewport_window

from ..common import (
    APPLICATION_MODE,
    CURRENT_TOOL_PATH,
    SETTINGS_MARKUP_ACTIVE,
    SETTINGS_MARKUP_EDITING,
    SETTINGS_MARKUP_ROOT,
)
from ..style import FONT_SIZE, LIST_WINDOW_STYLES
from .playbar import PlayBar

if TYPE_CHECKING:  # pragma: no cover
    from omni.kit.markup.core.extension import MarkupCore


MAX_SHOW_MARKUPS = 3
SETTINGS_LIST_WINDOW_SAVE_POSITION = SETTINGS_MARKUP_ROOT + "list_window/save_position"
SETTINGS_LIST_WINDOW_ALLOW_RESIZE = SETTINGS_MARKUP_ROOT + "list_window/allow_resize"


def build_frame_header(markup: ViewportMarkup, collapsed: bool, text: str, id: str = ""):
    """Custom header for CollapsibleFrame"""
    if not id:
        id = text

    if collapsed:
        alignment = ui.Alignment.RIGHT_CENTER
        width = 5
        height = 7
    else:
        alignment = ui.Alignment.CENTER_BOTTOM
        width = 7
        height = 5

    markup_inst = get_markup_extension_instance()

    def on_rename(x: int, y: int):
        def on_rename_ended(_item):
            if markup_inst and markup_inst.can_edit_markup(markup):
                new_name = model.as_string.replace(" ", "_")
                save = markup_inst.rename_markup(markup, new_name)
                markup_inst.end_edit_markup(markup, save=save, update_thumbnail=False)

            async def cleanup():
                win.destroy()

            run_coroutine(cleanup())

        def on_rename_begin(_item):
            if markup_inst and markup_inst.can_edit_markup(markup):
                markup_inst.begin_edit_markup(markup, set_editing_markup=False)

        flags = (
            ui.WINDOW_FLAGS_POPUP
            | ui.WINDOW_FLAGS_NO_TITLE_BAR
            | ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_NO_DOCKING
            | ui.WINDOW_FLAGS_NO_CLOSE
            | ui.WINDOW_FLAGS_NO_SCROLLBAR
        )
        win = ui.Window(
            "Rename Markup",
            position_x=x,
            position_y=y,
            visible=True,
            padding_x=0,
            padding_y=0,
            style=LIST_WINDOW_STYLES,
            flags=flags,
            width=160,
            height=0,
            identifier="RenameWindow",
        )
        with win.frame:
            model = ui.SimpleStringModel()
            model.add_begin_edit_fn(on_rename_begin)
            model.add_end_edit_fn(on_rename_ended)
            field = ui.StringField(model, multiline=False, identifier="rename_field")
            field.focus_keyboard()

    ctx_menu = None

    def on_mouse_pressed(x, y, btn, flag):

        if not markup_inst.can_edit_markup(markup):
            return

        nonlocal ctx_menu
        if btn == 1:
            if ctx_menu is None:
                ctx_menu = ui.Menu(menu_compatibility=False, tearable=False)
                with ctx_menu:
                    ui.MenuItem(
                        "Rename Markup", triggered_fn=lambda x=x, y=y: on_rename(x, y), identifier="RenameMarkup"
                    )
            ctx_menu.show_at(x, y)

    header_stack = ui.ZStack(spacing=8, mouse_pressed_fn=on_mouse_pressed, identifier="FrameHeader")
    with header_stack:
        with ui.HStack():
            with ui.VStack(width=0):
                ui.Spacer()
                ui.Triangle(
                    style_type_name_override="CollapsableFrame.Header", width=width, height=height, alignment=alignment
                )
                ui.Spacer()
            ui.Spacer()
        with ui.HStack():
            ui.Spacer()
            ui.Label(text, width=0, style_type_name_override="CollapsableFrame.Header")
            ui.Spacer()


@dataclass
class MarkupEntryWidget:
    markup: ViewportMarkup
    outer_stack: ui.ZStack
    hover_widget: MarkupItemHoverWidget
    collapse_frame: ui.CollapsableFrame
    field_stack: ui.ZStack
    notes_field: ui.StringField


class MarkupListWindow(ui.Window):
    WINDOW_WIDTH = 180
    VIEWPORT_MAIN_MENUBAR_HEIGHT = 32
    SPACING = 9

    def __init__(self):
        self._settings = carb.settings.get_settings()
        self._markup_instance = cast("MarkupCore ", get_markup_extension_instance())
        self._markup_count = 0
        self._widgets: "list[MarkupEntryWidget]" = []
        self._widgets_map: "dict[ViewportMarkup, MarkupEntryWidget]" = {}
        self._markup_callback = MarkupChangeCallbacks(
            self._on_markups_changed, self._on_markups_changed, self._on_markup_changed, self._on_markups_changed
        )
        self._markup_instance.register_callback(self._markup_callback)

        flags = (
            ui.WINDOW_FLAGS_NO_TITLE_BAR
            # | ui.WINDOW_FLAGS_POPUP
            | ui.WINDOW_FLAGS_NO_DOCKING
            | ui.WINDOW_FLAGS_NO_CLOSE
            | ui.WINDOW_FLAGS_NO_SCROLLBAR
            | ui.WINDOW_FLAGS_NO_COLLAPSE
        )

        # Data to indicate if any markup comment is being edited; needs to be set when the selection changes too.
        self._editing_comment_data = None
        self._deferred_rebuild = False

        # Give the MarkupCore a command to change selection
        self._markup_instance.set_selection_command(self.select_markup_widget)

        if not self._settings.get(SETTINGS_LIST_WINDOW_ALLOW_RESIZE):  # pragma: no cover
            flags |= ui.WINDOW_FLAGS_NO_RESIZE

        super().__init__(
            "Markups",
            width=MarkupListWindow.WINDOW_WIDTH,
            flags=flags,
            padding_x=2,
            padding_y=2,
            visible=False,
            raster_policy=ui.RasterPolicy.NEVER,
        )
        self.frame.set_style(LIST_WINDOW_STYLES)
        self.set_visibility_changed_fn(self._on_visibility_changed)
        self.set_focused_changed_fn(self._on_focused_changed)
        self._hotkey_context = None
        self._build_ui()

        def on_vp_width_changed(width: float, _self=weakref.ref(self)):
            if self := _self():
                self._list_window_updated = False
                self._on_viewport_size_changed()

        def on_vp_height_changed(height: float, _self=weakref.ref(self)):
            if self := _self():
                self._list_window_updated = False
                self._on_viewport_size_changed()

        self._viewport_handle = get_active_viewport_window()
        if self._viewport_handle:
            self._viewport_handle.set_height_changed_fn(on_vp_height_changed)
            self._viewport_handle.set_width_changed_fn(on_vp_width_changed)
            self._viewport_handle.set_position_x_changed_fn(self._on_viewport_size_changed)
            self._viewport_handle.set_position_y_changed_fn(self._on_viewport_size_changed)

        self._list_window_save_position = self._settings.get(SETTINGS_LIST_WINDOW_SAVE_POSITION)
        self._list_window_updated = False

        self._current_tool_changed_id = self._settings.subscribe_to_node_change_events(
            CURRENT_TOOL_PATH, self._on_current_tool_changed
        )

        def application_mode_changed(*args, _self=weakref.ref(self)):  # pragma: no cover
            self = _self()
            if self:
                self._list_window_updated = False

        self._app_mode_sub = self._settings.subscribe_to_node_change_events(APPLICATION_MODE, application_mode_changed)

        self._markup_active_sub = self._settings.subscribe_to_node_change_events(
            SETTINGS_MARKUP_ACTIVE, self._on_markup_active_changed
        )
        self._markup_editing_sub = self._settings.subscribe_to_node_change_events(
            SETTINGS_MARKUP_EDITING, self._on_markup_editing_changed
        )

        self.__hotkey_context_future = None

    @property
    def selected_index(self) -> "int|None":
        for idx, widget in enumerate(self._widgets):
            if widget.outer_stack.selected:
                return idx

    @selected_index.setter
    def selected_index(self, value: "int|None"):
        for idx, widget in enumerate(self._widgets):
            widget.outer_stack.selected = idx == value
            if widget.outer_stack.selected:
                self._markup_instance.recall_markup(widget.markup)
        if value is None:
            self._markup_instance.recall_markup(None)

    @property
    def widgets(self) -> "list[MarkupEntryWidget]":
        return self._widgets[:]

    def destroy(self):
        if self._hotkey_context:
            from ..extension import MARKUP_WINDOW_FOCUS_CONTEXT

            self._remove_hotkey_context(MARKUP_WINDOW_FOCUS_CONTEXT)
        self._hotkey_context = None
        self.frame.clear()
        self._widgets.clear()
        self._widgets_map.clear()
        self._markup_instance.deregister_callback(self._markup_callback)
        del self._markup_callback
        self._markup_instance = cast("MarkupCore", None)
        self.visible = False
        if self._current_tool_changed_id and self._settings:
            self._settings.unsubscribe_to_change_events(self._current_tool_changed_id)
            self._current_tool_changed_id = None

        if self._app_mode_sub is not None:
            self._settings.unsubscribe_to_change_events(self._app_mode_sub)
            self._app_mode_sub = None

        if self._markup_editing_sub is not None:
            self._settings.unsubscribe_to_change_events(self._markup_editing_sub)
            self._markup_editing_sub = None
        if self._markup_active_sub is not None:
            self._settings.unsubscribe_to_change_events(self._markup_active_sub)
            self._markup_active_sub = None

        self.__play_bar.destroy()
        self.__play_bar = None

        if self.__hotkey_context_future and not self.__hotkey_context_future.done():
            self.__hotkey_context_future.cancel()

    def _on_viewport_size_changed(self, *_):
        if not self.visible or self._viewport_handle is None:  # pragma: no cover
            return

        first_update = not self._list_window_updated
        if first_update:
            self._list_window_updated = True

        vp = ui.Workspace.get_window(self._viewport_handle.title)
        x = MarkupListWindow.SPACING + vp.position_x
        y = vp.position_y + MarkupListWindow.VIEWPORT_MAIN_MENUBAR_HEIGHT + MarkupListWindow.SPACING
        if vp.docked:  # pragma: no cover
            if vp.dock_tab_bar_visible:
                y += 18

        if first_update or not self._list_window_save_position:
            self.setPosition(x, y)

        self._update_window_height(vp.height)

    def _update_window_height(self, vp_height):
        cy = vp_height - MarkupListWindow.VIEWPORT_MAIN_MENUBAR_HEIGHT - MarkupListWindow.SPACING

        show_count = max(self._markup_count, 1)
        if show_count == 0:  # pragma: no cover
            show_count = 1
        elif show_count > MAX_SHOW_MARKUPS:
            show_count = MAX_SHOW_MARKUPS
        # 90 is thumbnail height
        # 30 is label height
        # 2 is spacer between thumbnail and label
        # 4 is scrolling frame padding
        height = min(
            self._container.computed_height + show_count * (90 + 30 + 2) + 4,
            cy - MarkupListWindow.VIEWPORT_MAIN_MENUBAR_HEIGHT,
        )

        if self.height < height:  # pragma: no cover
            self.height = height

    def _on_visibility_changed(self, visible: bool):
        from ..extension import MARKUP_WINDOW_FOCUS_CONTEXT

        if visible:

            async def __delay_re_position(panel):
                await omni.kit.app.get_app().next_update_async()
                await omni.kit.app.get_app().next_update_async()
                panel._on_viewport_size_changed()
                if self._hotkey_context:
                    self._hotkey_context.push(MARKUP_WINDOW_FOCUS_CONTEXT)
                self.focus()
                self.__hotkey_context_future = None

            if self.__hotkey_context_future is not None and not self.__hotkey_context_future.done():
                self.__hotkey_context_future.cancel()
            self.__hotkey_context_future = run_coroutine(__delay_re_position(self))
        else:
            if self._hotkey_context and self._hotkey_context.get() == MARKUP_WINDOW_FOCUS_CONTEXT:
                self._remove_hotkey_context(MARKUP_WINDOW_FOCUS_CONTEXT)

    def _on_focused_changed(self, focused: bool):
        if self._hotkey_context is None:
            try:
                import omni.kit.hotkeys.core

                self._hotkey_context = omni.kit.hotkeys.core.get_hotkey_context()
            except:  # pragma: no cover
                return
        from ..extension import MARKUP_WINDOW_FOCUS_CONTEXT

        if focused and self._hotkey_context.get() != MARKUP_WINDOW_FOCUS_CONTEXT:
            self._hotkey_context.push(MARKUP_WINDOW_FOCUS_CONTEXT)
        else:
            active_markup = self._settings.get_as_string(SETTINGS_MARKUP_ACTIVE)
            # Hotkey context is not cleared when there is an active markup
            # We expect that resetting the active markup brings back focus so the state becomes consistent again
            if active_markup is None or active_markup == "":
                self._remove_hotkey_context(MARKUP_WINDOW_FOCUS_CONTEXT)

    def _remove_hotkey_context(self, context: str):
        if self.__hotkey_context_future is not None and not self.__hotkey_context_future.done():
            self.__hotkey_context_future.cancel()
        if self._hotkey_context is not None:
            all_contexts = []
            while (top_context := self._hotkey_context.get()) is not None:
                all_contexts.append(top_context)
                self._hotkey_context.pop()
            for c in reversed(all_contexts):
                if c != context:  # pragma: no cover
                    self._hotkey_context.push(c)

    def _build_ui(self):
        with self.frame:
            with ui.VStack():
                self._container = ui.VStack(height=0)
                with self._container:
                    self._build_title()
                    ui.Spacer(height=8)
                    with ui.HStack(height=36):
                        ui.Spacer()
                        btn = ui.Button(
                            "Add Markup",
                            name="add_markup",
                            style_type_name_override="Add.Button",
                            clicked_fn=lambda: self._markup_instance.create_markup(),
                            height=36,
                            width=36,
                            identifier="AddMarkupButton",
                        )
                        btn.spacing = 4
                        ui.Spacer(width=4)
                        ui.Button(
                            " ",
                            height=36,
                            width=36,
                            style_type_name_override="Export.Button",
                            clicked_fn=lambda: self._markup_instance.export_markups(),
                            identifier="ExportButton",
                        )
                        ui.Spacer()
                    ui.Spacer(height=2)
                    self.__play_bar = PlayBar()
                    self.__play_bar.bind_widget(self)
                    ui.Separator(height=5, menu_compatibility=False)
                self.__scroll_field = ui.ScrollingFrame(
                    vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED
                )
                self._build_widget()

    def _build_widget(self):
        self._widgets.clear()
        self._widgets_map.clear()

        with self.__scroll_field:
            with ui.VStack(spacing=3, identifier="OuterVStack"):
                for markup in self._markup_instance.get_markups():
                    # If something is wrong with the primtive, skip it and wait for the next refresh.
                    if None in (markup.usd_prim, markup.comment, markup.thumbnail_data):  # pragma: no cover
                        continue

                    outer_stack = ui.ZStack(
                        style={"GridView.Image:selected": {"debug_color": 0x0}},
                        content_clipping=1,
                        height=0,
                    )
                    with outer_stack:
                        with ui.VStack():
                            with ui.HStack(identifier="HStackyStackStack"):
                                ui.Spacer()
                                with ui.ZStack(width=0):
                                    thumbnail_provider = ui.ByteImageProvider()
                                    byte_data, width, height = markup.thumbnail_data or (b"", 0, 0)
                                    thumbnail_provider.set_bytes_data(bytearray(byte_data), [width, height])
                                    image = ui.ImageWithProvider(
                                        thumbnail_provider,
                                        alignment=ui.Alignment.CENTER,
                                        fill_policy=ui.IwpFillPolicy.IWP_PRESERVE_ASPECT_FIT,
                                        height=90,
                                        width=160,
                                        style_type_name_override="GridView.Image",
                                        opaque_for_mouse_events=1,
                                        identifier="ImageThumbnail",
                                    )

                                    hover = MarkupItemHoverWidget(MarkupItem(markup))
                                    hover.visible = False
                                    ui.Rectangle(
                                        style_type_name_override="GridView.Item.Selection",
                                        identifier="_markup_list_window_selection_rectangle",
                                    )
                                ui.Spacer()

                            collapse_frame = ui.CollapsableFrame(
                                markup.name,
                                collapsed=True,
                                build_header_fn=lambda col, txt, mk=markup: build_frame_header(mk, col, txt),
                                identifier="CollapseFrame",
                            )
                            with collapse_frame:
                                field_stack = ui.ZStack()
                                with field_stack:
                                    model = ui.SimpleStringModel(markup.comment)
                                    field = ui.StringField(model, multiline=True, identifier="CommentEditField")
                                    field.read_only = not self._markup_instance.can_edit_markup(
                                        markup, show_messages=False
                                    )
                                    field.enabled = self._markup_instance.can_edit_markup(markup, show_messages=False)

                            def on_collapse(collapsed: bool, mk=markup, stk=field_stack, fld=field):
                                if not collapsed:
                                    fld.model.as_string = mk.comment
                                    stk.height = ui.Pixel((fld.model.as_string.count("\n") + 2.6) * FONT_SIZE)
                                    fld.enabled = self._markup_instance.can_edit_markup(mk, show_messages=False)

                            collapse_frame.set_collapsed_changed_fn(on_collapse)

                            def on_edit_end(mdl: ui.AbstractValueModel, stk=field_stack, mk: ViewportMarkup = markup):
                                self._on_edit_end(mdl, stk, mk)

                            def on_edit_begin(item, mdl=model, stk=field_stack, mk=markup):
                                if self._markup_instance and self._markup_instance.can_edit_markup(mk):
                                    self._editing_comment_data = (mdl, stk, mk)
                                    self._markup_instance.begin_edit_markup(mk, set_editing_markup=False)

                            model.add_begin_edit_fn(on_edit_begin)
                            model.add_end_edit_fn(on_edit_end)

                    def on_click(x, y, btn, flag, mk=markup):
                        if self._widgets_map[mk].hover_widget.button_hovered:  # pragma: no cover
                            return
                        if (
                            self._markup_instance.editing_markup and self._markup_instance.editing_markup != mk
                        ):  # pragma: no cover
                            return

                        if btn == 0:
                            self.select_markup_widget(mk)

                    def on_double_click(x, y, btn, flag, mk=markup):
                        if self._widgets_map[mk].hover_widget.button_hovered:  # pragma: no cover
                            return
                        if (
                            self._markup_instance.editing_markup and self._markup_instance.editing_markup != mk
                        ):  # pragma: no cover
                            return

                        if btn == 0:
                            self.select_markup_widget(mk)

                    def on_hover(hov, mk=markup):
                        self._widgets_map[mk].hover_widget.visible = hov

                    image.set_mouse_pressed_fn(on_click)
                    image.set_mouse_double_clicked_fn(on_double_click)
                    image.set_mouse_hovered_fn(on_hover)
                    entry_widget = MarkupEntryWidget(markup, outer_stack, hover, collapse_frame, field_stack, field)
                    self._widgets.append(entry_widget)
                    self._widgets_map[markup] = entry_widget

        self._markup_count = len(self._widgets)

    def _build_title(self):
        # Same as tear-off menubar
        with ui.ZStack(height=14):
            ui.Rectangle(style_type_name_override="Menu.Title")
            with ui.HStack():
                ui.Spacer(width=14)
                ui.Line(style_type_name_override="Menu.Title.Line")
                with ui.Frame(width=14):
                    ui.Image(
                        style_type_name_override="Menu.Item.CloseMark",
                        mouse_pressed_fn=lambda x, y, b, a: self._on_close_window(),
                        identifier="close_mark",
                    )

    def _on_close_window(self):
        self.visible = False

    def _on_markups_changed(self, *args) -> None:
        self._markup_count = len(self._markup_instance.get_markups())
        vp = ui.Workspace.get_window(self._viewport_handle.title)
        self._update_window_height(vp.height)
        # OMPE-19499: don't rebuild the widget list while the local user is
        # actively typing into a markup's comment field - the rebuild would
        # destroy the active StringField and drop the in-progress edit.
        # Mark the rebuild as deferred and re-run it once the user is done.
        if self._editing_comment_data is not None:
            self._deferred_rebuild = True
            return
        self._build_widget()

    def _on_markup_changed(self, markup: "ViewportMarkup|None"):
        # OMPE-19499: see _on_markups_changed - defer rebuild while a comment
        # edit is in progress.
        if self._editing_comment_data is not None:
            self._deferred_rebuild = True
            return
        self._build_widget()

    def _on_current_tool_changed(self, *args):
        current_tool = self._settings.get(CURRENT_TOOL_PATH)
        if current_tool is None or str(current_tool).lower() == "none":
            self._on_close_window()

    def _on_edit_end(self, mdl: ui.AbstractValueModel, stk, mk: ViewportMarkup):
        self._editing_comment_data = None
        if not self._markup_instance.can_edit_markup(mk):  # pragma: no cover
            self._markup_instance.end_edit_markup(mk, save=False)
            return

        stk.height = ui.Pixel((mdl.as_string.count("\n") + 2.6) * FONT_SIZE)
        mk.comment = mdl.as_string
        if self._markup_instance:
            self._markup_instance.end_edit_markup(mk, save=True, update_thumbnail=False)
            self._markup_instance.current_markup = None

        # OMPE-19499: a remote live-session change may have requested a
        # rebuild while we were typing - apply it now that the edit is done.
        if self._deferred_rebuild:
            self._deferred_rebuild = False
            self._build_widget()

    def _on_markup_active_changed(self, *args):
        active_markup = self._settings.get(SETTINGS_MARKUP_ACTIVE)
        if active_markup is None or active_markup == "" and self.selected_index is not None:
            self.selected_index = None

    def _on_markup_editing_changed(self, *args):
        is_editing = self._settings.get(SETTINGS_MARKUP_EDITING)
        if is_editing and self.visible and self._editing_comment_data is None:
            self.visible = False
        elif not is_editing and not self.visible:
            # NOTE: the intended behavior here is that when a user finishes editing a markup,
            # the list window reappears.
            # However, this has the unintended consequence of popping up the list window when
            # the SETTINGS_MARKUP_EDITING setting is changed to something that evaluates to False;
            # in OMFP-2778 this was observed to happen to a user in a live session who was *not* in
            # markup mode when another user in the live session created a markup.
            # Thus we should take care not to set SETTINGS_MARKUP_EDITING to the empty string
            # redundantly. See comment in editing_markup setter in extension.py.
            self.visible = True

        if not is_editing:
            self._editing_comment_data = None

    def select_markup_widget(self, mk):
        if self._editing_comment_data is not None:
            self._on_edit_end(
                self._editing_comment_data[0], self._editing_comment_data[1], self._editing_comment_data[2]
            )

        self._markup_instance.recall_markup(mk)

        if not mk:
            for mark, widget in self._widgets_map.items():
                widget.outer_stack.selected = False
                widget.collapse_frame.collapsed = True
            return

        if mk in self._widgets_map and self._widgets_map[mk].outer_stack.selected:
            return

        for mark, widget in self._widgets_map.items():
            widget.outer_stack.selected = mk.name == mark.name
            widget.collapse_frame.collapsed = bool(mk.name != mark.name or not widget.notes_field.model.as_string)
            if not widget.collapse_frame.collapsed:
                widget.field_stack.height = ui.Pixel((widget.notes_field.model.as_string.count("\n") + 2.6) * FONT_SIZE)
