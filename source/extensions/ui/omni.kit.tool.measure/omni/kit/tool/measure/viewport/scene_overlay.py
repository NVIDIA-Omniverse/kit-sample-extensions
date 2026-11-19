# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from typing import Callable, Optional

import omni.ui as ui
from carb.input import KeyboardInput
from carb.settings import ISettings, get_settings
from carb.windowing import CursorStandardShape
from omni.kit.window.cursor import get_main_window_cursor

from ..common import MeasureCreationState, MeasureMode
from ..interface.style import STYLE_VP_BUTTON
from ..manager import StateMachine


class MeasureSceneOverlay:
    FINALIZE_MODES = [MeasureMode.MULTI_POINT, MeasureMode.AREA]
    NAVBAR_VISIBILITY_PATH: str = "/exts/omni.kit.viewport.navigation.core/isVisible"
    TIMELINE_MINIBAR_PATH: str = "/exts/omni.kit.timeline.minibar/visible"

    def __init__(self, on_enter_pressed_fn: Optional[Callable] = None):
        super().__init__()
        self.__frame = ui.Frame()

        self._settings: ISettings = get_settings()

        self._enter_pressed_fn: Optional[Callable] = on_enter_pressed_fn

        # NOTE: Need to register to the Tool Creation State changed
        StateMachine().add_tool_creation_state_changed_fn(self.__on_creation_state_changed)
        self._key_sub = StateMachine().subscribe_to_key_pressed_event(self._on_key_pressed)

        # NOTE: Register to the visibility settings paths for required viewport content
        self._nav_visibility_sub = self._settings.subscribe_to_node_change_events(
            self.NAVBAR_VISIBILITY_PATH, lambda item, name="navigation": self.__on_visibility_changed(item, name)
        )

        self._timeline_visibility_sub = self._settings.subscribe_to_node_change_events(
            self.TIMELINE_MINIBAR_PATH, lambda item, name="timeline_minibar": self.__on_visibility_changed(item, name)
        )
        self._visibility = False
        self.__frame.set_build_fn(self.__build_ui())

    def __del__(self):
        self.destroy()

    def destroy(self):
        if self._nav_visibility_sub:
            self._settings.unsubscribe_to_change_events(self._nav_visibility_sub)
            self._nav_visibility_sub = None

        if self._timeline_visibility_sub:
            self._settings.unsubscribe_to_change_events(self._timeline_visibility_sub)
            self._timeline_visibility_sub = None

    def __enter__(self):
        return self.__root

    def __exit__(self):
        return True

    def __build_ui(self):
        self.__root = ui.ZStack()
        with self.__root:
            self._button_stack = ui.VStack(visible=self._visibility)
            with self._button_stack:
                self._top_offset = ui.Spacer()
                with ui.HStack(height=16):
                    ui.Spacer()
                    ui.Button(
                        "Press To Complete (Enter)",
                        style=STYLE_VP_BUTTON,
                        width=0,
                        clicked_fn=self._on_complete_clicked,
                        mouse_hovered_fn=self.__on_hovered,
                        opaque_for_mouse_events=True,
                    )
                    ui.Spacer()
                self._bottom_offset = ui.Spacer()

        self.__update_button_position()

    def __block_snapping(self, block: bool) -> None:
        from .snap.manager import MeasureSnapProviderManager

        MeasureSnapProviderManager().enabled = not block

    def _on_complete_clicked(self) -> None:
        if self._button_stack:
            self._visibility = False
            self._button_stack.visible = self._visibility

            tool = StateMachine().tool_mode

            from ..manager import ReferenceManager

            if current_tool := ReferenceManager().measure_scene._create_manipulator._get_tool(tool):
                if current_tool.creation_state == MeasureCreationState.END_SELECTION:
                    current_tool._try_auto_complete_and_save()
            self.__block_snapping(False)

    def __on_hovered(self, hovered: bool) -> None:
        shape = CursorStandardShape.HAND if hovered else CursorStandardShape.ARROW
        get_main_window_cursor().override_cursor_shape(shape)
        self.__block_snapping(hovered)

    def __on_creation_state_changed(self, state: MeasureCreationState) -> None:
        if self._button_stack:
            self._visibility = (
                state == MeasureCreationState.END_SELECTION and StateMachine().tool_mode in self.FINALIZE_MODES
            )
            self._button_stack.visible = self._visibility

    def __on_visibility_changed(self, *_) -> None:
        self.__update_button_position()

    def __update_button_position(self):
        if not self._top_offset and not self._bottom_offset:
            return

        offset = 20  # Default Padding

        # NOTE: Hardcode for testing
        if nav_visible := self._settings.get_as_bool(self.NAVBAR_VISIBILITY_PATH):
            offset += 72
        if timeline_visible := self._settings.get_as_bool(self.TIMELINE_MINIBAR_PATH):
            offset += 30
        offset += 30 if nav_visible and timeline_visible else 20

        self._bottom_offset.height = ui.Pixel(offset)
        self.__frame.rebuild()

    def _on_key_pressed(self, key: KeyboardInput) -> None:
        if key != KeyboardInput.ENTER:
            return

        if (
            tool := StateMachine().tool_mode
        ) in self.FINALIZE_MODES and StateMachine().tool_creation_state == MeasureCreationState.END_SELECTION:
            # TODO: Needs to wait for Hotkey Implementation and callbacks to do thing to current enabled measure tool

            if self._button_stack:
                self._visibility = False
                self._button_stack.visible = self._visibility

                # If hotkey is handled elsewhere we can nuke this
                from ..manager import ReferenceManager

                if current_tool := ReferenceManager().measure_scene._create_manipulator._get_tool(tool):
                    current_tool.force_save()
