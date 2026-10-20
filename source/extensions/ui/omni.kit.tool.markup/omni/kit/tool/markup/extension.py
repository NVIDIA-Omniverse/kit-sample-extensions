# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from pathlib import Path
from typing import Optional, cast
from weakref import ref

import carb
import carb.dictionary
import carb.input
import carb.settings
import omni.appwindow
import omni.ext
import omni.kit.app
import omni.kit.commands
from omni import ui
from omni.kit.async_engine import run_coroutine
from omni.kit.markup.core import get_instance as get_markup_core_instance
from omni.kit.viewport.utility import get_active_viewport_window
from omni.kit.window.preferences import register_page, unregister_page
from omni.ui import scene as sc

from .common.settings import MarkupPreferences
from .ui import MarkupScene, get_canvas_size, get_viewport_frame_size
from .ui.constant import (
    CURRENT_TOOL_PATH,
    EXTENSION_NAME,
    MARKUP_BLOCK_GESTURES,
    MARKUP_LETTERBOX_COLOR,
    MARKUP_TOOL_CURRENT,
    MARKUP_TOOL_HIDE,
    SETTINGS_MARKUP_ACTIVE,
    SETTINGS_MARKUP_EDITING,
    SETTINGS_MARKUP_ROOT,
    SETTINGS_VIEWPORT_RECT,
)
from .ui.events import MarkupEvent
from .ui.markup_export import MarkupExportWindow
from .ui.markup_toolbar import MarkupTools
from .ui.renderer import MarkupRenderer

g_singleton = None


# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.
class MarkupToolExtension(omni.ext.IExt):
    def __init__(self, *_args, **_kwargs):
        super().__init__()

    def on_startup(self, _ext_id) -> None:
        self._markup_tool = MarkupTool()
        self._markup_tool.on_startup(_ext_id)

    def on_shutdown(self) -> None:
        self._markup_tool.on_shutdown()


class MarkupTool:
    _markup_stack: ui.ZStack

    def __init__(self, *_args, **_kwargs):
        super().__init__()
        self._settings = None
        self._markup = None
        self._vp_manager = None
        self._viewport_window = None
        # Set in on_startup only once a viewport is found; on_shutdown must handle a startup that stopped earlier.
        self._markup_frame = None
        self._export_window = None
        self._undo_id = None
        self._redo_id = None
        self._page = None
        self._gesture_stack = None
        self._scene_view = None
        self._subscription_ids = []
        self._markup_scene = None
        self._gesture_resize_task = None

    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    def on_startup(self, _ext_id) -> None:
        self._settings = carb.settings.get_settings()
        self._input = carb.input.acquire_input_interface()
        self._keyboard = omni.appwindow.get_default_app_window().get_keyboard()
        self._active_markup_changed = MarkupEvent()
        self._edit_markup_changed = MarkupEvent()
        self._current_tool_changed = MarkupEvent()
        self._markup_visibility_changed = MarkupEvent()
        self._markup_subtool_changed = MarkupEvent()
        self._selected_element_changed = MarkupEvent()
        self._on_undo = MarkupEvent()
        self._on_redo = MarkupEvent()

        get_markup_core_instance().export_fn = self._on_export

        self._subscription_ids[:] = []
        global g_singleton
        g_singleton = self

        def on_active_markup_changed(item, event_type, _self=ref(self)):
            self = _self()
            if self:
                self._active_markup_changed(item, event_type)

        def on_edit_markup_changed(item, event_type, _self=ref(self)):
            self = _self()
            if self:
                self._edit_markup_changed(item, event_type)
                if self._gesture_stack:
                    self._refresh_border_colors()

        def on_current_tool_changed(item, event_type, _self=ref(self)):
            self = _self()
            if self:
                self._current_tool_changed(item, event_type)

        def on_letterbox_color_changed(item, event_type, _self=ref(self)):
            self = _self()
            if self:
                self._refresh_border_colors()

        def on_markup_tool_visibility_changed(item, event_type, _self=ref(self)):
            self = _self()
            if self:
                self._markup_visibility_changed(item, event_type)

        def on_markup_subtool_changed(item, event_type, _self=ref(self)):
            self = _self()
            if self:
                self._markup_subtool_changed(item, event_type)

        self._subscription_ids.extend(
            [
                self._settings.subscribe_to_node_change_events(SETTINGS_MARKUP_ACTIVE, on_active_markup_changed),
                self._settings.subscribe_to_node_change_events(SETTINGS_MARKUP_EDITING, on_edit_markup_changed),
                self._settings.subscribe_to_node_change_events(CURRENT_TOOL_PATH, on_current_tool_changed),
                self._settings.subscribe_to_node_change_events(MARKUP_LETTERBOX_COLOR, on_letterbox_color_changed),
                self._settings.subscribe_to_node_change_events(MARKUP_TOOL_HIDE, on_markup_tool_visibility_changed),
                self._settings.subscribe_to_node_change_events(MARKUP_TOOL_CURRENT, on_markup_subtool_changed),
            ]
        )
        self._active_markup_changed += self._on_markup_active

        if not self._create_viewport():  # pragma: no cover
            # using the warning and return instead of an error to  pass the startup test
            carb.log_warn("Could not register markup for any Viewport backend")
            return

        # Register the export Window so the focus mode toolbar can toggle the display of it.
        self._export_window = MarkupExportWindow()
        self._export_window.visible = False

        with self._markup_stack:
            self._renderer = MarkupRenderer(self)

        self._selected_element_changed += self._renderer.on_selection_changed
        self._on_undo += self._handle_undo
        self._on_redo += self._handle_redo
        self._renderer.element_destroyed += self._on_element_destroyed

        with self._tool_frame:
            self._markup_tools = MarkupTools()

        self._active_markup_changed += self._markup_tools.on_markup_active_changed
        self._edit_markup_changed += self._markup_tools.on_markup_edit_changed
        self._markup_visibility_changed += self._markup_tools.on_visibility_changed
        self._markup_subtool_changed += self._markup_tools.on_subtool_changed
        self._selected_element_changed += self._markup_tools.on_selected_element_changed
        self._current_tool_changed += self._markup_tools.on_app_state_sync_changed

        self._undo_id = omni.kit.commands.register_callback("Undo", omni.kit.commands.POST_DO_CALLBACK, self._on_undo)
        self._redo_id = omni.kit.commands.register_callback("Redo", omni.kit.commands.POST_DO_CALLBACK, self._on_redo)

        self._page = MarkupPreferences()
        register_page(self._page)

    def on_shutdown(self) -> None:
        if self._gesture_resize_task:
            self._gesture_resize_task.cancel()
            self._gesture_resize_task = None

        if isinstance(self._settings, carb.settings.ISettings):
            for sub_id in self._subscription_ids:
                self._settings.unsubscribe_to_change_events(sub_id)

        if self._vp_manager:  # pragma: no cover
            self._vp_manager.destroy()
            self._vp_manager = None
        self._settings = None
        if self._markup is not None:  # pragma: no cover
            self._markup.destroy()
            self._markup = None

        global g_singleton
        g_singleton = None
        if self._gesture_stack:
            self._gesture_stack.clear()
            self._gesture_stack.destroy()
            self._gesture_stack = None

        if self._viewport_window:
            if self._scene_view:
                self._viewport_window.viewport_api.remove_scene_view(self._scene_view)
            self._viewport_window = None

        if self._markup_frame:
            self._markup_frame.destroy()
            self._markup_frame = None

        if self._scene_view:
            self._scene_view.destroy()
            self._scene_view = None

        if isinstance(self._export_window, ui.Window):
            self._export_window.destroy()

        if self._markup_scene:
            self._markup_scene.destroy()
        self._markup_scene = None
        self._renderer = None
        self._markup_tools = None
        if self._undo_id is not None:
            omni.kit.commands.unregister_callback(self._undo_id)
            self._undo_id = None
        if self._redo_id is not None:
            omni.kit.commands.unregister_callback(self._redo_id)
            self._redo_id = None

        if self._page is not None:
            self._page.destroy()
            unregister_page(self._page)
            self._page = None

        get_markup_core_instance().export_fn = None

    def get_element_at_path(self, element_path):
        if self._renderer:
            return self._renderer.get_element_at_path(element_path)

    def get_element_at(self, x, y, *, element_type: str = ""):
        if self._renderer:
            return self._renderer.get_element_at(x, y, element_type=element_type)

    def set_selected_element(self, element):
        self._selected_element_changed(element)

    def get_gesture_manager(self):
        if self._markup_scene:
            return self._markup_scene.markup_gesture_manager
        else:  # pragma: no cover
            return None

    def _on_export(self):
        if self._export_window:
            self._export_window.visible = True

    def _on_visibility_changed(self, value: bool) -> None:
        if value and isinstance(self._settings, carb.settings.ISettings):
            self._settings.set(CURRENT_TOOL_PATH, EXTENSION_NAME)

    def _on_markup_edit(self, *args):  # pragma: no cover
        self._on_markup_active(*args)

    def _on_markup_active(self, item: carb.dictionary.Item, *_):
        if not self._gesture_stack:  # pragma: no cover
            return
        # Because of how `ui.CanvasFrame` operates, we end up capturing all user viewport input here
        # So when a markup is not active we want to hide the canvas, which keeps the viewport playing nice.
        self._canvas.visible = bool(item.get_dict())
        if self._canvas.visible and self._viewport_window:
            self._on_visibility_changed(self._canvas.visible)

    def _create_viewport(self) -> bool:
        self._viewport_window = get_active_viewport_window("Viewport")
        if not self._viewport_window:  # pragma: no cover
            return False

        self._markup_frame = self._viewport_window.get_frame("omni.kit.tool.markup")
        with self._markup_frame:
            with ui.ZStack():

                # Canvas frame is used here because we need a drawing surface that is potentially beyond the boundary
                # of the viewport frame. This allows us to stay aligned to the viewport texture when in "Fill" mode.
                # This is handled by adjusting the offset, and width/height of the gesture-stack whenever the viewport
                # emits a view related change.
                self._canvas = ui.CanvasFrame(
                    zoom_max=1, draggable=False, style={"CanvasFrame": {"background_color": 0x0}}
                )
                with self._canvas:
                    with ui.ZStack():
                        self._offset_top_rect = ui.Placer()
                        self._offset_bottom_rect = ui.Placer(style={"background_color": 0})
                        self._offset = ui.Placer()
                        self._tool_frame = ui.Frame()

                    with self._offset_bottom_rect:
                        with ui.ZStack(height=0):
                            self._bottom_rect = ui.Rectangle()
                    with self._offset_top_rect:
                        with ui.ZStack(height=0):
                            self._top_rect = ui.Rectangle(style={"background_color": 0})
                    with self._offset:
                        with ui.VStack():
                            self._gesture_stack = ui.ZStack(height=0, width=0)
                            ui.Spacer()
                        with self._gesture_stack:
                            # We need the markup elements to live in their own stack, separately from the SceneView
                            # Because otherwise attempting to clean up can destroy the SceneView while it still
                            # tries to be drawn, which really breaks the viewport (hard crash).
                            self._markup_stack = ui.ZStack()
                            self._scene_view = sc.SceneView(name="MarkupScene")
                            with self._scene_view.scene:
                                self._markup_scene = MarkupScene(self)
                            self._viewport_window.viewport_api.add_scene_view(self._scene_view)
                            self._gesture_stack.set_computed_content_size_changed_fn(self._refresh_border_size)

        if self._viewport_window.viewport_api:
            self._sub_id = self._viewport_window.viewport_api.subscribe_to_view_change(self._on_viewport_update)

        async def ensure_viewport_updated():
            if self._viewport_window:
                self._on_viewport_update(self._viewport_window.viewport_api)

        run_coroutine(ensure_viewport_updated())
        return True

    def _refresh_border_colors(self):
        border_color = 0x00000000
        if get_markup_core_instance().editing_markup:
            border_color = self._settings.get(MARKUP_LETTERBOX_COLOR)
            if not isinstance(border_color, int):
                border_color = 0xC0000000
        style = {"background_color": border_color}
        self._top_rect.set_style(style)
        self._bottom_rect.set_style(style)

    def _refresh_border_size(self):
        _, canvas_height = get_canvas_size(self._viewport_window)
        bottom = float(self._offset.offset_y) + float(canvas_height)
        self._offset_bottom_rect.offset_y = ui.Pixel(bottom)
        self._bottom_rect.height = self._offset.offset_y
        self._top_rect.height = self._offset.offset_y

    def _on_viewport_update(self, api):
        if not self._viewport_window or not self._gesture_stack:  # pragma: no cover
            return

        wx, wy = get_viewport_frame_size(self._viewport_window)
        new_width, new_height = get_canvas_size(self._viewport_window)

        self._resize_gesture_stack(new_width, new_height)
        self._offset.offset_x, self._offset.offset_y = ui.Pixel((wx - new_width) / 2), ui.Pixel((wy - new_height) / 2)
        if self._settings:
            self._settings.set_float_array(
                SETTINGS_VIEWPORT_RECT,
                [
                    float(self._offset.offset_x),
                    float(self._offset.offset_y),
                    float(self._offset.offset_x + new_width),
                    float(self._offset.offset_y + new_height),
                ],
            )

        self._refresh_border_colors()
        self._refresh_border_size()

    def _resize_gesture_stack(self, width, height):
        """Apply the new canvas size from a task instead of inline.

        This is reached from ``subscribe_to_view_change``, and the gesture stack also
        has a ``set_computed_content_size_changed_fn`` callback attached. With both in
        play, assigning the size directly inside the view-change callback leaves the
        change unapplied -- the requested size updates but omni.ui never lays it out,
        and the markup renders at the pre-resize scale. Deferring by one update moves
        the assignment out of the callback so the two do not interleave, which is the
        usual way to mutate geometry alongside a computed-content-size callback.
        """
        if self._gesture_resize_task:
            self._gesture_resize_task.cancel()

        async def apply_size():
            await omni.kit.app.get_app().next_update_async()
            if self._gesture_stack:
                self._gesture_stack.width, self._gesture_stack.height = ui.Pixel(width), ui.Pixel(height)

        self._gesture_resize_task = run_coroutine(apply_size())

    def get_markup_stack(self) -> ui.ZStack:
        return self._markup_stack

    def refresh_elements(self, refresh_all_elements=False, selected_element=None):
        if self._renderer:
            self._renderer.refresh_elements(refresh_all_elements, selected_element)

    def _on_element_destroyed(self, element):
        self.set_selected_element(None)
        self.refresh_elements()

    def _handle_undo(self, undo_data):
        self.set_selected_element(None)
        self.refresh_elements(refresh_all_elements=True)

    def _handle_redo(self, data):
        self.set_selected_element(None)
        self.refresh_elements(refresh_all_elements=True)


def get_instance() -> Optional[MarkupTool]:
    return g_singleton


__all__ = ["MarkupToolExtension", "get_instance", "MarkupTool"]
