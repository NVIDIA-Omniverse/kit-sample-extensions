# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""UI implementation for the In-App Guide step window.

This module provides the main guide window that displays step-by-step instructions
and navigation controls. It handles positioning relative to target UI elements,
animations, and interactions with reveal actions like scrolling and clicking.
"""

import asyncio
import math
import time
import webbrowser
from typing import Callable, List, Optional, Union

import carb.eventdispatcher
import carb.events
import carb.input
import omni.appwindow
import omni.kit.app
import omni.kit.ui_test as ui_test
import omni.ui as ui
from omni.ui_query import OmniUIQuery

from . import style
from .model import ClickAction, ExpandAction, GuideModel, GuideStep, ScrollAction
from .overlay_ui import OverlayWindow


def calculate_guide_position(
    guide_width: int,
    guide_height: int,
    app_width: int,
    app_height: int,
    target_x: int,
    target_y: int,
    target_width: int,
    target_height: int,
) -> tuple[int, int]:
    """Calculate the optimal position for the guide window relative to a target.

    Args:
        guide_width: Width of the guide window
        guide_height: Height of the guide window
        app_width: Width of the application window
        app_height: Height of the application window
        target_x: X position of the target element
        target_y: Y position of the target element
        target_width: Width of the target element
        target_height: Height of the target element

    Returns:
        Tuple of (x, y) coordinates for the guide window position
    """
    # Left of target
    left_x = target_x - guide_width
    if left_x >= 0:
        return left_x, clamp(target_y, 0, app_height - guide_height)

    # Above target
    above_y = target_y - guide_height
    if above_y >= 0:
        return clamp(target_x, 0, app_width - guide_width), above_y

    # Right of target
    right_x = target_x + target_width
    if right_x + guide_width <= app_width:
        return right_x, clamp(target_y, 0, app_height - guide_height)

    # Below target
    below_y = target_y + target_height
    if below_y + guide_height <= app_height:
        return clamp(target_x, 0, app_width - guide_width), below_y

    # Center on target
    center_x = target_x + (target_width - guide_width) // 2
    center_y = target_y + (target_height - guide_height) // 2
    return clamp(center_x, 0, app_width - guide_width), clamp(center_y, 0, app_height - guide_height)


def clamp(value: int, min_val: int, max_val: int) -> int:
    """Clamp a value between minimum and maximum bounds.

    Args:
        value: The value to clamp
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        The clamped value
    """
    return max(min_val, min(value, max_val))


class WidgetRefOverride(ui_test.WidgetRef):
    """Extends widget reference with custom click behavior.

    This class overrides the default WidgetRef to provide custom click emulation
    for guide interactions with UI elements.
    """

    async def click(self, pos=None, right_click=False, double=False, human_delay_speed: int = 2):
        """Emulate a mouse click on the widget.

        Args:
            pos: Position to click at. If None, clicks at center of widget.
            right_click: Whether to perform a right click.
            double: Whether to perform a double click.
            human_delay_speed: Speed factor for simulating human-like delays.
        """
        if not pos:
            pos = self.center
        await ui_test.emulate_mouse_move_and_click(
            pos, right_click=right_click, double=double, human_delay_speed=human_delay_speed
        )


class GuideStepWindow(ui.Window):
    """Window that displays the current guide step and navigation controls."""

    def __init__(self, name: str, model: GuideModel, overlay_window: OverlayWindow):
        """Initialize the guide step window.

        Args:
            name: Name of the window
            model: The guide model instance
            overlay_window: The overlay window instance
        """
        super().__init__(
            name,
            dockPreference=ui.DockPreference.DISABLED,
            flags=(
                ui.WINDOW_FLAGS_NO_COLLAPSE
                | ui.WINDOW_FLAGS_NO_RESIZE
                | ui.WINDOW_FLAGS_NO_SCROLLBAR
                | ui.WINDOW_FLAGS_NO_RESIZE
                | ui.WINDOW_FLAGS_NO_MOVE
                | ui.WINDOW_FLAGS_NO_TITLE_BAR
                | ui.WINDOW_FLAGS_NO_SAVED_SETTINGS
            ),
            auto_resize=False,
            padding_x=0,
            padding_y=0,
            raster_policy=ui.RasterPolicy.NEVER,
            width=350,
        )
        self._model: GuideModel = model
        self._animator: Optional[GuideWindowAnimator] = None
        self._overlay_window: OverlayWindow = overlay_window
        self._tree_view_height = 130
        # Register handler for when the application window is resized
        event_dispatcher = carb.eventdispatcher.get_eventdispatcher()
        self._app_window_resize_sub = event_dispatcher.observe_event(
            observer_name="omni.sample.in_app_guide.OverlayWindow",
            event_name=omni.appwindow.GLOBAL_EVENT_WINDOW_RESIZE,
            on_event=self._on_app_window_resized,
        )

        self.frame.set_style(style.step_ui)
        self.frame.set_build_fn(self._build_ui)
        self._model.add_current_step_changed_function(self._update_ui)

    def _build_ui(self):
        carb.log_info("Building UI")
        with ui.ZStack():
            ui.Rectangle(name="content_background")
            with ui.VStack(spacing=0):
                with ui.ZStack():
                    ui.Rectangle(name="title_bar_background", height=52)
                    with ui.HStack(name="title_stack", height=52):
                        self._header: ui.Label = ui.Label("", name="header", height=32)
                        ui.Button("", name="close", clicked_fn=self._close, height=32, width=32)

                with ui.VStack(name="content_stack", height=0):
                    self._description: ui.Label = ui.Label("", name="description", word_wrap=True, width=300, height=0)

                with ui.ZStack():
                    ui.Rectangle(name="button_bar_background", height=40)
                    with ui.HStack(name="button_bar_stack", spacing=4):
                        self._link_button: ui.Button = ui.Button(
                            "", name="link", clicked_fn=self._open_link, height=32, width=0
                        )
                        ui.Spacer()
                        self._previous_button: ui.Button = ui.Button(
                            " ", clicked_fn=self._model.previous, spacing=0, width=32, height=32
                        )
                        self._steps_button: ui.Button = ui.Button(
                            "Steps",
                            name="steps_toggle",
                            clicked_fn=self._toggle_tree_view,
                            spacing=0,
                            width=64,
                            height=32,
                        )
                        self._next_button: ui.Button = ui.Button(
                            " ", clicked_fn=self._model.next, spacing=0, width=32, height=32
                        )
                self._list_stack: ui.ZStack = ui.ZStack(visible=False, height=self._tree_view_height)
                with self._list_stack:
                    with ui.ScrollingFrame(
                        height=self._tree_view_height,
                        horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                        vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                        style_type_name_override="TreeView",
                    ):
                        self._tree_view: ui.TreeView = ui.TreeView(self._model, height=0)
                        self._tree_view.root_visible = False
                        self._tree_view.set_selection_changed_fn(self._on_list_selection_changed)
        self._update_ui(self._model.current_step)

    def _on_app_window_resized(self, event: carb.events.IEvent):
        """Handle app window resize events."""
        self._update_ui(self._model.current_step)

    def _toggle_tree_view(self):
        """Toggle the visibility of the step list tree view."""
        self._list_stack.visible = not self._list_stack.visible
        guide_step = self._model.current_step
        if guide_step:
            if guide_step.ui_type == "window":
                asyncio.ensure_future(self._position_for_window(guide_step.target_ui_path))
                return
            if guide_step.ui_type == "widget":
                asyncio.ensure_future(
                    self._position_for_widget(
                        guide_step.parent_window_ui_path, guide_step.target_ui_path, guide_step.reveal_actions
                    )
                )
                return
            if guide_step.ui_type == "menu":
                asyncio.ensure_future(self._position_for_menu(guide_step.target_ui_path, guide_step.menu_item_text))
                return

    def _on_list_selection_changed(self, selections: List[GuideStep]):
        """Handle selection changes in the step list.

        Args:
            selections: List of selected guide steps
        """
        if selections:
            selections = selections[-1:]
            self._tree_view.selection = selections
            self._model.current_step = selections[0]
        elif self._model.current_step:
            self._tree_view.selection = [self._model.current_step]

    def _close(self):
        """Close the guide by deactivating the model."""
        self._model.active = False

    def _open_link(self):
        """Open the link associated with the current step."""
        webbrowser.open(self._model.current_step.link.url)

    def _update_ui(self, guide_step: GuideStep):
        """Update the UI based on the current guide step.

        Args:
            guide_step: The current guide step
        """
        self._overlay_window.current_step = None

        if guide_step is None:
            self._header.text = ""
            self._description.text = ""
            self._previous_button.enabled = False
            self._previous_button.name = "disabled"
            self._next_button.enabled = False
            self._next_button.name = "disabled"
            self._link_button.visible = False
            return

        # Update UI elements
        self._header.text = guide_step.title
        self._description.text = guide_step.description
        self._previous_button.enabled = self._model.has_previous
        self._previous_button.name = "enabled_previous" if self._model.has_previous else "disabled_previous"
        self._next_button.enabled = self._model.has_next
        self._next_button.name = "enabled_next" if self._model.has_next else "disabled_next"
        self._link_button.visible = True if guide_step.link else False
        self._link_button.text = guide_step.link.label if guide_step.link else ""
        self._tree_view.selection = [guide_step]

        if guide_step.ui_type == "window":
            asyncio.ensure_future(self._position_for_window(guide_step.target_ui_path))
            return
        if guide_step.ui_type == "widget":
            asyncio.ensure_future(
                self._position_for_widget(
                    guide_step.parent_window_ui_path, guide_step.target_ui_path, guide_step.reveal_actions
                )
            )
            return
        if guide_step.ui_type == "menu":
            asyncio.ensure_future(self._position_for_menu(guide_step.target_ui_path, guide_step.menu_item_text))
            return

    async def _update_window_size(self) -> None:
        """Update the window size based on content."""
        app = omni.kit.app.get_app()
        await app.next_update_async()
        # Update window size
        # 52 for title bar, 20 for content_stack margin, 40 for button bar
        if self._list_stack.visible:
            self.height = self._description.computed_height + 112 + self._tree_view_height
        else:
            self.height = self._description.computed_height + 112
        # Allow UI to adjust
        await app.next_update_async()

    async def _position_for_window(self, window_name: str) -> None:
        """Position the guide window relative to a target window.

        Args:
            window_name: Name of the target window
        """
        # Update this window's size
        await self._update_window_size()
        # Make sure window is visible
        ui.Workspace.show_window(window_name, True)
        # Get the target window
        window = ui.Workspace.get_window(window_name)
        # Make sure window is in focus as it may be behind another one
        window.focus()

        async def position_window():
            # Allow target ui to become visible
            app = omni.kit.app.get_app()
            for _ in range(5):
                await app.next_update_async()

            # Calculate where to place this window
            x, y = calculate_guide_position(
                guide_width=self.width,
                guide_height=self.height,
                app_width=ui.Workspace.get_main_window_width(),
                app_height=ui.Workspace.get_main_window_height(),
                target_x=window.position_x,
                target_y=window.position_y,
                target_width=window.width,
                target_height=window.height,
            )

            self._animator = GuideWindowAnimator(self)
            self._animator.animate_to(x, y, self._on_animation_complete)

        asyncio.ensure_future(position_window())

    async def _position_for_widget(
        self, window_name: str, ui_path: str, reveal_actions: List[Union[ExpandAction, ScrollAction, ClickAction]]
    ) -> None:
        """Position the guide window relative to a target widget.

        Args:
            window_name: Name of the parent window
            ui_path: Path to the target widget
            reveal_actions: List of actions to reveal the widget
        """
        # Update this window's size
        await self._update_window_size()
        # Make sure window is visible
        ui.Workspace.show_window(window_name, True)
        # Get the target window
        window = ui.Workspace.get_window(window_name)
        # Make sure window is in focus as it may be behind another one
        window.focus()
        # Perform reveal actions
        if len(reveal_actions) > 0:
            # Enable mouse interactions with application UI underneath both guide windows.
            self._overlay_window.block_mouse_inputs(block=False)
            self._block_mouse_inputs(block=False)

            app = omni.kit.app.get_app()
            await app.next_update_async()

            for reveal_action in reveal_actions:
                if isinstance(reveal_action, ClickAction):
                    # Get current mouse coordinates
                    carb_input = carb.input.acquire_input_interface()
                    app_window = omni.appwindow.get_default_app_window()
                    mouse = app_window.get_mouse()
                    dpi_scale = ui.Workspace.get_dpi_scale()
                    mouse_pos: ui_test.Vec2 = ui_test.Vec2(carb_input.get_mouse_coords_pixel(mouse))
                    mouse_pos = mouse_pos / dpi_scale
                    # Get widget
                    target_widget = OmniUIQuery.find_widget(reveal_action.ui_path)
                    if not target_widget:
                        self._close()
                        raise Exception(f"UI path not found: {reveal_action.ui_path}")
                    # Get a reference for the widget
                    widget_ref = WidgetRefOverride(target_widget, reveal_action.ui_path, window)
                    # Simulate mouse click on target
                    await widget_ref.click()
                    # Return mouse to original location
                    await ui_test.emulate_mouse_move(mouse_pos)
                    # Let UI update
                    await app.next_update_async()
                    continue
                if isinstance(reveal_action, ExpandAction):
                    target_widget = OmniUIQuery.find_widget(reveal_action.ui_path)
                    if not target_widget:
                        self._close()
                        raise Exception(f"UI path not found: {reveal_action.ui_path}")
                    await self._expand_frame(target_widget)
                    continue
                if isinstance(reveal_action, ScrollAction):
                    await app.next_update_async()
                    # Get the scrollable frame
                    frame = OmniUIQuery.find_widget(reveal_action.ui_path)
                    # Get the widget to scroll to
                    target_widget = OmniUIQuery.find_widget(reveal_action.scroll_target_ui_path)
                    if not target_widget:
                        self._close()
                        raise Exception(f"UI path not found: {reveal_action.scroll_target_ui_path}")
                    await self._scroll_frame(frame, target_widget)
                    await app.next_update_async()
                    continue
                raise NotImplementedError(f"reveal_action {type(reveal_action)} not implemented")

            # Disable mouse interactions with application UI underneath both guide windows.
            self._overlay_window.block_mouse_inputs()
            self._block_mouse_inputs()

        # Get pointer to widget
        widget = OmniUIQuery.find_widget(ui_path)

        async def position_widget():
            nonlocal widget
            # Allow target ui to become visible
            app = omni.kit.app.get_app()
            for _ in range(5):
                await app.next_update_async()

            # Calculate where to place this window
            x, y = calculate_guide_position(
                guide_width=self.width,
                guide_height=self.height,
                app_width=ui.Workspace.get_main_window_width(),
                app_height=ui.Workspace.get_main_window_height(),
                target_x=widget.screen_position_x,
                target_y=widget.screen_position_y,
                target_width=widget.computed_width,
                target_height=widget.computed_height,
            )

            self._animator = GuideWindowAnimator(self)
            self._animator.animate_to(x, y, self._on_animation_complete)

        asyncio.ensure_future(position_widget())

    async def _position_for_menu(self, menu_path: str, menu_item_text: str) -> None:
        """Position the guide window relative to a target menu item.

        Args:
            menu_path: Path to the target menu.
            menu_item_text: Text of the menu item to highlight.
        """
        # Update this window's size
        await self._update_window_size()
        # Get the target menu
        menu_bar = OmniUIQuery.find_menu_item(menu_path)  # Finds the menu bar
        menu_widget = None
        for widget in OmniUIQuery.find_widgets("*", [menu_bar]):
            if isinstance(widget, ui.Menu) or isinstance(widget, ui.MenuItem):
                if widget.text == menu_item_text:
                    menu_widget = widget
                    break
        if not menu_widget:
            self._close()
            raise Exception(f"Menu not found: {menu_path}")

        async def position_menu():
            # Allow target ui to become visible
            app = omni.kit.app.get_app()
            for _ in range(5):
                await app.next_update_async()

            # Calculate where to place this window
            x, y = calculate_guide_position(
                guide_width=self.width,
                guide_height=self.height,
                app_width=ui.Workspace.get_main_window_width(),
                app_height=ui.Workspace.get_main_window_height(),
                target_x=menu_widget.screen_position_x,
                target_y=menu_widget.screen_position_y,
                target_width=menu_widget.computed_width,
                target_height=menu_widget.computed_height,
            )

            self._animator = GuideWindowAnimator(self)
            self._animator.animate_to(x, y, self._on_animation_complete)

        asyncio.ensure_future(position_menu())

    async def _expand_frame(self, frame: ui.ScrollingFrame) -> None:
        """Expand a collapsible frame.

        Args:
            frame: The frame to expand
        """
        if not frame.collapsed:
            return

        frame_expanded = False

        # Handler for when scroll has completed
        def on_expanded(value: float):
            nonlocal frame_expanded
            frame_expanded = True

        # Add handler for when expanded
        frame.set_collapsed_changed_fn(on_expanded)
        # Expand frame
        frame.collapsed = False
        # Loop until expansion has completed
        app = omni.kit.app.get_app()
        while not frame_expanded:
            await app.next_update_async()

    async def _scroll_frame(self, frame: ui.ScrollingFrame, target_widget: ui.Widget) -> None:
        """Scroll a frame to make a widget visible.

        Args:
            frame: The frame to scroll
            target_widget: The widget to scroll to
        """

        def widget_visible_in_frame() -> bool:
            nonlocal frame
            nonlocal target_widget
            if target_widget.screen_position_y < frame.screen_position_y:
                # Widget top edge is above the frame
                return False
            if (
                target_widget.screen_position_y + target_widget.computed_height
                > frame.screen_position_y + frame.computed_height
            ):
                # Widget bottom edge is below the frame
                return False
            return True

        if widget_visible_in_frame():
            # Widget already visible within frame
            return

        scroll_amount: float = 0.0
        scroll_direction: float = 0.0

        def set_scroll_factors() -> None:
            nonlocal frame
            nonlocal target_widget
            nonlocal scroll_amount
            nonlocal scroll_direction

            # Set initial values
            if scroll_direction == 0.0:
                if target_widget.screen_position_y < frame.screen_position_y:
                    scroll_direction = 1.0  # Scroll up
                else:
                    scroll_direction = -1.0  # Scroll down
                scroll_amount = ui.Workspace.get_main_window_height()
                return

            # Evaluate current direction. If previous scroll was too far we toggle the direction and decrease the distance
            if target_widget.screen_position_y < frame.screen_position_y:
                if scroll_direction < 0.0:
                    scroll_direction = 1.0  # Scroll up
                    scroll_amount *= 0.5
            else:
                if scroll_direction > 0.0:
                    scroll_direction = -1.0  # Scroll down
                    scroll_amount *= 0.5

        # Center mouse within frame
        center_x = frame.screen_position_x + frame.computed_width * 0.5
        center_y = frame.screen_position_y + frame.computed_height * 0.5
        mouse_pos: ui_test.Vec2 = ui_test.Vec2(center_x, center_y)
        await ui_test.emulate_mouse_move(mouse_pos)
        app = omni.kit.app.get_app()
        await app.next_update_async()
        # Scroll until widget is visible
        while not widget_visible_in_frame():
            # Set/Update scroll values
            set_scroll_factors()
            await ui_test.emulate_mouse_scroll(ui_test.Vec2(0, scroll_amount * scroll_direction))
            await app.next_update_async()

    def _block_mouse_inputs(self, block: bool = True):
        """Enable or disable mouse input blocking.

        Args:
            block: Whether to block mouse inputs
        """
        if block:
            self.flags &= ~ui.WINDOW_FLAGS_NO_MOUSE_INPUTS  # Remove flag
        else:
            self.flags |= ui.WINDOW_FLAGS_NO_MOUSE_INPUTS  # Add flag

    def _on_animation_complete(self):
        """Handle completion of window animation."""
        self._animator = None
        if self._overlay_window and self._model:
            self._overlay_window.current_step = self._model.current_step

    def destroy(self):
        """Clean up resources."""
        # Unsubscribe from app window resize events by setting to None
        if self._app_window_resize_sub:
            self._app_window_resize_sub = None
        if self._animator:
            self._animator.destroy()
            self._animator = None
        if self._model is not None:
            self._model.remove_current_step_changed_function(self._update_ui)
            self._model = None
        self._header = None
        self._description = None
        self._previous_button = None
        self._next_button = None
        self._link_button = None
        self._steps_button = None
        self._list_stack = None
        self._tree_view = None
        self._overlay_window = None
        super().destroy()


class GuideWindowAnimator:
    """Handles smooth animation of the guide window position."""

    @staticmethod
    def _lerp(start, end, t):
        """Linear interpolation between two values.

        Args:
            start: Start value
            end: End value
            t: Interpolation factor (0-1)

        Returns:
            Interpolated value
        """
        return start + (end - start) * t

    def __init__(self, window, speed_px_per_sec=2000):
        """Initialize the animator.

        Args:
            window: The window to animate
            speed_px_per_sec: Animation speed in pixels per second
        """
        self._window = window
        self._speed = speed_px_per_sec
        self._target_pos = None
        self._on_update_sub = None
        self._on_complete = None

        self._start_pos = None
        self._start_time = None
        self._duration = None

    def animate_to(self, target_x, target_y, on_complete: Callable[[], None]):
        """Start animation to a target position.

        Args:
            target_x: Target x coordinate
            target_y: Target y coordinate
            on_complete: Callback to execute when animation completes
        """
        self._target_pos = (target_x, target_y)
        self._start_pos = (self._window.position_x, self._window.position_y)
        self._on_complete = on_complete

        dx = target_x - self._start_pos[0]
        dy = target_y - self._start_pos[1]
        distance = math.hypot(dx, dy)

        # Time = distance / speed
        self._duration = max(distance / self._speed, 0.001)
        self._start_time = time.time()

        if not self._on_update_sub:
            event_dispatcher = carb.eventdispatcher.get_eventdispatcher()
            self._on_update_sub = event_dispatcher.observe_event(
                observer_name="omni.sample.in_app_guide.GuideWindowAnimator",
                event_name=omni.kit.app.GLOBAL_EVENT_UPDATE,
                on_event=self._on_update,
            )

    def destroy(self):
        """Clean up resources."""
        # Unsubscribe by setting to None
        self._on_update_sub = None
        self._window = None
        self._target_pos = None

    def _on_update(self, event):
        """Handle update events for animation.

        Args:
            event: The update event
        """
        if not self._window or not self._target_pos or not self._start_pos:
            return

        elapsed = time.time() - self._start_time
        t = min(elapsed / self._duration, 1.0)

        # Ease-in-out
        eased_t = t * t * (3 - 2 * t)

        new_x = GuideWindowAnimator._lerp(self._start_pos[0], self._target_pos[0], eased_t)
        new_y = GuideWindowAnimator._lerp(self._start_pos[1], self._target_pos[1], eased_t)

        self._window.position_x = new_x
        self._window.position_y = new_y

        if t >= 1.0:
            # Unsubscribe by setting to None
            self._on_update_sub = None
            self._start_time = None
            self._start_pos = None
            self._target_pos = None
            if self._on_complete:
                self._on_complete()
