# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""
A menu system for the minimap generator that handles UI interactions and settings.

This module provides a comprehensive UI menu system for controlling the minimap generation settings
and navigation capabilities. It enables users to generate top-down views of USD stages with
configurable parameters for visualization and navigation.

Key Features:
- Floor/ceiling height controls for selective geometry visibility
- Tile size and count management for optimizing render resolution
- Real-time navigation and orientation tracking
- Stage boundary initialization from selection
- Context menus for advanced operations
- Job limit controls for performance optimization

The menu system integrates with the USD stage to handle:
- Selection-based boundary initialization
- Tile-based rendering with configurable resolution
- Metadata management for storing minimap data
- Real-time navigation and orientation tracking

Usage:
1. Initialize stage boundaries by selecting enclosing primitives and clicking 'Init'
2. Adjust floor/ceiling heights to control visible geometry
3. Configure tile size and count for desired resolution
4. Generate minimap using Build button (RMB for additional options)
5. Save minimap data to stage metadata
"""

__all__ = ["Menu"]

import asyncio
import logging
import math
from functools import partial

import carb
import carb.eventdispatcher
import carb.events
import omni.ui as ui
import omni.usd
from omni.kit.widget.settings import SettingType, create_setting_widget, create_setting_widget_combo
from omni.ui import color as cl
from pxr import Gf, UsdGeom

from . import settings
from .generator import BOUND_PRIMS_KEY, CDATA_KEY, MinimapGenerator
from .settings import S_PATH
from .style import base_style, btn_style, btn_style_dim, menu_style
from .window import WindowEventTypes

logger = logging.getLogger(__name__)


class Menu:
    """
    A class that manages the minimap generator's UI menu system.

    This class provides a comprehensive interface for controlling minimap generation settings
    and navigation capabilities. It handles the creation and management of UI elements for:
    - Floor/ceiling height controls
    - Tile size and count management
    - Build and save operations
    - Job limit controls
    - Context menus for advanced operations

    The menu system supports:
    - Automatic minimap generation from stage geometry
    - Custom floor/ceiling bounds definition
    - Tile-based rendering with configurable resolution
    - Real-time navigation and orientation tracking

    Usage Tips:
    - Clear irrelevant primitives to optimize bounding box size
    - Tile count of 999 indicates boundary problems
    - Initialize scene to ensure tile count <= 128
    - Increase tile size to reduce tile count
    - Use RMB menus on buttons and sliders for additional options
    - Save stage after saving minimap to preserve settings

    Args:
        generator (MinimapGenerator): The minimap generator instance
        window (ui.Window): The window instance to attach the menu to

    Attributes:
        _usd_context: The USD context for stage operations
        _settings: Global settings manager
        _stage: Current USD stage
        _provider: Reference to the minimap generator
        _window: Reference to the UI window
        _frame: UI frame for the menu
        _bound_prims: Currently bound primitives
        _bounds: Current bounds
    """

    def __init__(self, generator: MinimapGenerator, window: ui.Window):
        """Initialize the menu system with the given generator and window."""
        self._usd_context = omni.usd.get_context()
        self._settings = carb.settings.get_settings()
        self._stage = None
        self._provider = generator
        self._window = window
        self._frame = window.get_frame("ui_frame")
        self._bound_prims = self._bounds = None
        self._async_tasks = []

        # Ensure DEV_MODE has a default value in carb settings (the _DevModeAccessor
        # in settings.py reads from carb settings on every access, so we never assign
        # to settings.DEV_MODE directly — that would overwrite the accessor object).
        if self._settings.get(S_PATH.DEV_MODE) is None:
            self._settings.set(S_PATH.DEV_MODE, False)

        self._init_frame()

        # Subscribe to window events for settings visibility
        self._window_evt_sub_id = window.get_event_stream().create_subscription_to_pop(
            self._on_window_event, name="Menu window event"
        )

        # Subscribe to stage events to update menu when stages change
        self._stage_sub = [
            carb.eventdispatcher.get_eventdispatcher().observe_event(
                observer_name="omni.sample.minimap.Menu",
                event_name=self._usd_context.stage_event_name(event),
                on_event=func,
            )
            for event, func in [
                (omni.usd.StageEventType.OPENED, lambda _: self._on_stage_opened()),
                (omni.usd.StageEventType.CLOSING, lambda _: self._on_stage_closing()),
                (omni.usd.StageEventType.CLOSED, lambda _: self._on_stage_closed()),
            ]
        ]

        # Subscribe to generator events to update resolution when metadata loads
        from .generator import MinimapGeneratorEventTypes

        if self._provider and self._provider._event_stream:
            self._generator_event_sub = self._provider._event_stream.create_subscription_to_pop_by_type(
                int(MinimapGeneratorEventTypes.UPDATE), self._on_generator_update, name="Menu generator update"
            )
        else:
            self._generator_event_sub = None

        if self._usd_context.get_stage_state() == omni.usd.StageState.OPENED:
            self._on_stage_opened()

    def destroy(self):
        """Clean up menu resources."""
        # Prevent multiple destroy calls
        if hasattr(self, "_destroyed") and self._destroyed:
            return
        self._destroyed = True

        # 1. Cancel all async tasks
        if hasattr(self, "_async_tasks"):
            for task in self._async_tasks:
                if not task.done():
                    task.cancel()
            self._async_tasks.clear()

        # 2. Clean up subscriptions
        self._stage_sub = None
        self._window_evt_sub_id = None
        self._generator_event_sub = None

        # 3. Clear references
        self._provider = None
        self._window = None
        self._frame = None

    def _on_window_event(self, event: carb.events.IEvent):
        """
        Handle window events for showing/hiding settings.

        Responds to window events to control menu visibility:
        - SHOW_SETTINGS: Display the settings frame
        - HIDE_SETTINGS: Hide the settings frame

        This allows users to toggle the settings panel while keeping
        the navigation interface always visible.

        Args:
            event (carb.events.IEvent): The window event to handle
        """
        if event.type == int(WindowEventTypes.SHOW_SETTINGS):
            self._frame.visible = True
        elif event.type == int(WindowEventTypes.HIDE_SETTINGS):
            self._frame.visible = False

    def _on_generator_update(self, event: carb.events.IEvent):
        """
        Handle generator UPDATE events after tiles are loaded.
        This ensures resolution field is updated AFTER metadata is loaded,
        making metadata resolution take precedence over settings.

        Args:
            event (carb.events.IEvent): The generator update event
        """
        if hasattr(self, "_resolution_drag") and self._resolution_drag and self._provider:
            resolution_value = self._provider.resolution
            self._resolution_drag.model.set_value(resolution_value)

    def _on_stage_opened(self):
        """
        Handle stage opened event by updating the UI with current stage data.

        This method:
        1. Gets the current USD context
        2. Retrieves the opened stage
        3. Updates UI elements with stage data
        4. Initializes menu with current settings

        This ensures the menu reflects the current stage state
        when a new stage is opened.
        """
        try:
            self._usd_context = omni.usd.get_context()
            self._stage = self._usd_context.get_stage()

            # Always update internal state, but only refresh UI for non-anonymous stages
            if self._stage:
                is_anonymous = self._stage.GetRootLayer().anonymous
                if not is_anonymous:
                    self._update_ui()
        except Exception as e:
            logger.warning("Failed to initialize stage on open: %s", e, exc_info=True)

    def _on_stage_closing(self): ...

    def _on_stage_closed(self): ...

    def _update_ui(self):
        """
        Asynchronously update UI elements with current generator values.
        Updates floor/ceiling fields and tile calculations.
        This is called when the stage is loaded.
        Tile size auto-fits to bounds when tile count is 1.
        """

        async def __update_ui():
            try:
                await omni.kit.app.get_app().next_update_async()

                # Wait for generator's stage to be set (with timeout)
                max_wait = 50  # 50 frames max (~0.8 seconds at 60fps)
                wait_count = 0
                while not self._provider._stage and wait_count < max_wait:
                    await omni.kit.app.get_app().next_update_async()
                    wait_count += 1

                if not self._provider._stage:
                    carb.log_warn("Menu initialization: Generator stage not ready after timeout")
                    return

                # Give the provider a bit more time to load metadata after stage is set
                # This ensures resolution is loaded from metadata before we update UI
                await omni.kit.app.get_app().next_update_async()
                await omni.kit.app.get_app().next_update_async()

                # Check if menu hasn't been destroyed during the wait
                if not self._provider or not self._window:
                    return

                self._floor_fld.model.set_value(self._provider.floor)
                self._ceil_fld.model.set_value(self._provider.ceiling)
                # Ensure tile_size is set from settings if not already set
                if not self._provider.tile_size or self._provider.tile_size == 0:
                    # Set internal value directly to avoid triggering setter during load
                    default_tile_size = self._settings.get(S_PATH.DEFAULT_TILE_SIZE) or 256
                    self._provider._tile_size = default_tile_size
                # Update tile size field to match provider
                self._tsize_fld.model.set_value(self._provider.tile_size)

                # NOTE: Resolution is updated by _on_generator_update() event handler
                # which fires AFTER metadata is loaded, ensuring metadata takes precedence

                # Calculate tile count based on whether tiles are loaded
                if self._provider._map_tile_groups:
                    # Tiles loaded: use actual count
                    tile_count = min(self._provider.calculate_tile_count(), 999)
                    self._tiles_fld.model.set_value(tile_count)
                else:
                    # No tiles: start with 1 and check if tile size is reasonable
                    optimal_size = self._provider.calculate_tile_size(1)
                    max_tile_size = self._settings.get(S_PATH.MAX_TILE_SIZE) or 256
                    if optimal_size > max_tile_size:
                        # Tile size too large for 1 tile, calculate needed count
                        tile_count = min(self._provider.calculate_tile_count(), 999)
                    else:
                        # 1 tile is reasonable
                        tile_count = 1
                        self._tsize_fld.model.set_value(optimal_size)
                        self._provider._tile_size = optimal_size
                    self._tiles_fld.model.set_value(tile_count)

                # Set slider limits to match bounds and ensure floor/ceiling are valid
                # This validates loaded values and adjusts if they're outside bounds
                self._validate_settings(init_from_bounds=False)

                # Update camera indicator size slider with current window value
                if hasattr(self, "_cam_size_slider") and self._cam_size_slider:
                    self._cam_size_slider.model.set_value(self._window.cam_size)
            except Exception as e:
                carb.log_error(f"Menu initialization error: {e}")

        task = asyncio.ensure_future(__update_ui())
        self._async_tasks.append(task)
        self._async_tasks = [t for t in self._async_tasks if not t.done()]

    def _menu(self, button, widget=None):
        """
        Handle menu button interactions.

        Args:
            button (int): Button identifier (1 for right click)
            widget (ui.Widget, optional): The widget that triggered the menu
        """
        if button == 1:  # Right click
            self._show_menu(widget)

    def _init_bounds(self):
        """
        Initialize bounds from currently selected primitives.

        This method:
        1. Clears all cached metadata and bounds
        2. Gets the currently selected primitives from the USD stage
        3. Calculates their combined bounding box
        4. Updates the generator's range based on these bounds
        5. Updates UI fields (floor, ceiling, tiles, tile size) from new bounds
        6. Validates the settings to ensure they are within bounds

        Note:
            - Selection must enclose the desired area to capture
            - This is the recommended way to fix boundary calculation issues
            - Use this when tile count shows 999 (indicating boundary problems)
            - Helps optimize the stage for minimaps <= 128 tiles
        """
        selection = self._usd_context.get_selection()
        selected_paths = selection.get_selected_prim_paths()
        if not self._stage:
            logger.warning("Init: No valid stage. Please open or create a stage first.")
            return

        # Check if stage is anonymous (unsaved)
        root_layer = self._stage.GetRootLayer()
        if root_layer.anonymous:
            logger.warning(
                "Init: Stage is unsaved. Please save the stage first (File -> Save As) before initializing minimap bounds."
            )
            return

        if not selected_paths:
            carb.log_warn("Init: No primitives selected. Please select primitives to define minimap bounds.")
            return

        # Clear all cached metadata/bounds AND settings before initializing new bounds
        self._provider._floor = None
        self._provider._ceiling = None
        self._provider._tile_size = None
        self._provider._resolution = None
        self._provider._range = None
        self._provider._bounds_top = None
        self._provider._bounds_bottom = None

        # Clear settings to ensure no stale data
        self._settings.set(S_PATH.BOUNDS, "")
        self._settings.set(S_PATH.FLOOR, None)
        self._settings.set(S_PATH.CEILING, None)

        # CRITICAL: Clear stage metadata to ensure it doesn't interfere
        if root_layer.customLayerData:
            custom_data = dict(root_layer.customLayerData)
            if "omni_minimap:bounds" in custom_data:
                del custom_data["omni_minimap:bounds"]
                root_layer.customLayerData = custom_data

        # Calculate bounds from selection
        bounds = self._provider.prim_bounds(selected_paths)
        if not bounds or bounds.IsEmpty():
            carb.log_warn("Init: Could not calculate valid bounds from selection")
            return

        # Set the new bounds (this caches the range AND writes to settings)
        self._provider.range = bounds

        # Use _validate_settings to calculate floor/ceiling with 0.1% buffer,
        # ensure they're within bounds, and set slider limits properly
        self._validate_settings(init_from_bounds=True)

        # Update tile count and size
        self._tiles_fld.model.set_value(min(self._provider.calculate_tile_count(), 999))
        self._tsize_fld.model.set_value(self._provider.tile_size)

        # CRITICAL: Call auto_fit_zoom to initialize _minimap_view_center
        # This ensures pan dragging works immediately after Init
        if self._window:
            self._window.auto_fit_zoom()

    def _show_menu(self, widget=None):
        """
        Display a context menu for the given widget.

        Shows a menu with options relevant to the widget type:
        - For tiles: Initialize from bounds
        - For write: Clear cache, delete map data, delete all metadata
        - For build: Generate draft, build tiles
        - For height fields: Use top/bottom of selection

        The menu provides actions for:
        - Manipulating bounds
        - Generating minimaps
        - Managing cached data
        - Clearing stage metadata

        Args:
            widget (ui.Widget, optional): The widget that triggered the menu.
                Different widgets will show different context menu options.
        """

        def get_bb(action: str, widget: ui.FloatField = None):
            """
            Get bounding box information based on the requested action.

            Args:
                action (str): The action to perform ('tiles', 'top', 'bottom', 'init')
                widget (ui.FloatField, optional): The widget to update with the result
            """
            selection = self._usd_context.get_selection()
            selected_paths = selection.get_selected_prim_paths()

            # Determine the up axis and meters per unit for the stage
            up_axis = UsdGeom.GetStageUpAxis(self._stage)
            mpu = UsdGeom.GetStageMetersPerUnit(self._stage)
            axis_comp = 2 if UsdGeom.Tokens.z == up_axis else 1  # Use Z or Y axis based on stage settings

            if not self._stage:
                return

            if action == "tiles":
                # Update tile count based on generator calculation
                self._tiles_fld.model.set_value(self._provider.calculate_tile_count())
                return
            else:
                if not selected_paths:
                    return

            # Get bounds of selected prims and update UI accordingly
            bound = self._provider.prim_bounds(selected_paths)
            if bound:
                if action == "top":
                    widget.model.set_value(bound.GetMax()[axis_comp] * mpu)
                elif action == "bottom":
                    widget.model.set_value(bound.GetMin()[axis_comp] * mpu)
                elif action == "init":
                    # Store selected prims and update UI with bound values
                    if self._provider._stage:
                        self._provider._stage.SetMetadataByDictKey(CDATA_KEY, BOUND_PRIMS_KEY, ",".join(selected_paths))
                    self._bounds = bound
                    self._floor_fld.model.set_value(bound.GetMin()[axis_comp] * mpu)
                    self._ceil_fld.model.set_value(bound.GetMax()[axis_comp] * mpu)
                elif action not in ["top", "bottom", "bound", "init"]:
                    logger.warning(f"Invalid action: {action}")
                    return
            else:
                logger.warning(f"Could not compute bounds for {selected_paths[0]}")

        async def __menu_show():
            """Asynchronously show the context menu with appropriate options."""
            # Check if menu hasn't been destroyed
            if not self._window:
                return
            self._output_menu = ui.Menu(style=menu_style)
            with self._output_menu:
                # Create menu items based on widget type
                if widget and widget.name == "tiles":
                    ui.MenuItem("Initialize from bounds", triggered_fn=partial(get_bb, "tiles"))
                elif widget and widget.name == "write":
                    ui.MenuItem(
                        "Clear Minimap Cache",
                        triggered_fn=lambda: asyncio.ensure_future(self._provider.clear_minimap()),
                    )
                    ui.MenuItem("Delete Map Data Only", triggered_fn=partial(self._provider.clear_data))
                    ui.MenuItem("Delete All Metadata", triggered_fn=partial(self._provider.clear_data, True))
                elif widget and widget.name == "build":
                    ui.MenuItem("Generate Draft", triggered_fn=partial(self._on_click_build, preview=True))
                    # ui.MenuItem("Build Tiles (keep)", triggered_fn=partial(self._on_click_build, rebuild=False))
                else:
                    if widget is not None:
                        ui.MenuItem("Use top of selection", triggered_fn=partial(get_bb, "top", widget))
                        ui.MenuItem("Use bottom of selection", triggered_fn=partial(get_bb, "bottom", widget))
            if widget is not None:
                widget.tooltip = ""
            self._output_menu.show()

        asyncio.ensure_future(__menu_show())

    def _on_cam_size_changed(self, model):
        """
        Handle camera FOV indicator size slider changes.

        Args:
            model: The slider's value model
        """
        if self._window:
            new_size = model.as_float
            self._window.cam_size = new_size

    def _on_resolution_changed(self, model):
        """
        Handle resolution changes.
        Updates the provider's resolution (which will be saved to metadata)
        and saves the new value to persistent settings.

        Args:
            model: The drag field's value model
        """
        new_resolution = model.as_int
        # Update provider's resolution (will be saved to metadata on next save)
        if self._provider:
            self._provider.resolution = new_resolution
        # Also save to carb settings as fallback
        carb.settings.get_settings().set(S_PATH.RESOLUTION, new_resolution)

    def _on_dev_mode_toggle(self):
        """Toggle developer mode and update button appearance."""
        # Read current value from carb settings and toggle it (never assign to
        # settings.DEV_MODE directly — that would overwrite the _DevModeAccessor).
        current_value = carb.settings.get_settings().get(S_PATH.DEV_MODE) or False
        new_value = not current_value
        carb.settings.get_settings().set(S_PATH.DEV_MODE, new_value)
        self._update_dev_mode_button()
        # Immediate feedback using persisted value
        persisted = settings.DEV_MODE
        status = "ENABLED" if persisted else "DISABLED"
        hint = " (Filter console by 'DEV:')" if persisted else ""
        logger.warning(f"DEV: Developer Mode {status}{hint}")
        if persisted:
            # Reset window's refresh monitoring counters to trigger immediate logging
            if hasattr(self._window, "_refresh_count"):
                delattr(self._window, "_refresh_count")

    def _update_dev_mode_button(self):
        """Update the dev mode button style to reflect current state."""
        if hasattr(self, "_dev_mode_btn") and self._dev_mode_btn:
            # Switch between normal and dimmed button styles
            if settings.DEV_MODE:
                self._dev_mode_btn.set_style(btn_style)  # Normal button style when enabled
            else:
                self._dev_mode_btn.set_style(btn_style_dim)  # Dimmed when disabled

    def tile_edit(self, action: str, *args):
        """
        Handle tile size and count editing.

        Maintains synchronization between tile size and count:
        - When size changes: Recalculates tile count
        - When count changes: Recalculates tile size

        The relationship ensures:
        - Total area coverage remains constant
        - Tile count stays within limits (1-128)
        - Tile size stays within bounds (64m-256m)

        Args:
            action (str): The edit action ('tsize' or 'tiles')
            *args: Additional arguments (unused)

        Note:
            - Tile count of 999 indicates boundary problems
            - Increasing tile size reduces total tile count
            - Default size (256m) balances resolution and file size
        """
        if not self._provider:
            return

        # Check if stage and range are valid
        if not self._provider._stage or not self._provider.range:
            return

        if action == "tsize":
            # Update tile count when user changes size
            self._provider.tile_size = self._tsize_fld.model.as_int
            tiles = min(self._provider.calculate_tile_count(), 999)
            self._tiles_fld.model.set_value(tiles)
        elif action == "tiles":
            # Update tile size when user changes count
            tile_size = self._provider.calculate_tile_size(self._tiles_fld.model.as_int)
            if self._tsize_fld.model.as_int != tile_size:
                self._tsize_fld.model.set_value(tile_size)

    def _validate_settings(self, init_from_bounds=False):
        """
        Calculate and validate floor/ceiling values, and set slider limits.

        This is the main mechanism for determining floor/ceiling values to avoid code duplication.

        Args:
            init_from_bounds: If True, calculate floor/ceiling from bounds with 0.1% buffer

        This method ensures:
        1. Floor/ceiling values are calculated from bounds (if init_from_bounds=True)
        2. Slider min/max limits are set to keep floor/ceiling within bounds
        3. Floor and ceiling don't intersect
        """
        if not self._stage:
            return

        from pxr import UsdGeom

        up_axis = UsdGeom.GetStageUpAxis(self._stage)
        mpu = UsdGeom.GetStageMetersPerUnit(self._stage)
        axis_comp = 2 if UsdGeom.Tokens.z == up_axis else 1

        # Get bounds - force recalculation to ensure they're fresh
        if init_from_bounds:
            # Force recalculation from range
            self._provider._bounds_top = None
            self._provider._bounds_bottom = None

        bounds_bottom = self._provider.bounds_bottom
        bounds_top = self._provider.bounds_top

        if bounds_bottom is None or bounds_top is None:
            return

        # If initializing from bounds, calculate floor/ceiling with 0.1% buffer
        if init_from_bounds:
            vertical_range = bounds_top - bounds_bottom
            floor_meters = bounds_bottom + (vertical_range * 0.001)
            ceiling_meters = bounds_top - (vertical_range * 0.001)

            # CRITICAL: Remove slider constraints BEFORE setting values
            # Otherwise old constraints will clamp the new values
            self._floor_fld.model.set_min(-1000000)
            self._floor_fld.model.set_max(1000000)
            self._ceil_fld.model.set_min(-1000000)
            self._ceil_fld.model.set_max(1000000)

            # Update provider cache and settings
            self._provider._floor = floor_meters
            self._provider._ceiling = ceiling_meters
            self._settings.set(S_PATH.FLOOR, floor_meters)
            self._settings.set(S_PATH.CEILING, ceiling_meters)

            # Update UI fields (now unconstrained)
            self._floor_fld.model.set_value(floor_meters)
            self._ceil_fld.model.set_value(ceiling_meters)

        # Get current values after potential initialization
        floor_val = self._floor_fld.model.as_float
        ceil_val = self._ceil_fld.model.as_float

        # Ensure floor/ceiling are within bounds before setting slider limits
        # If they're outside, adjust them to be just inside bounds
        # Use strict inequality because in_bounds() uses strict comparison
        if floor_val <= bounds_bottom:
            floor_val = bounds_bottom + (bounds_top - bounds_bottom) * 0.001
            self._floor_fld.model.set_value(floor_val)
            self._provider._floor = floor_val
        if ceil_val >= bounds_top:
            ceil_val = bounds_top - (bounds_top - bounds_bottom) * 0.001
            self._ceil_fld.model.set_value(ceil_val)
            self._provider._ceiling = ceil_val

        # Set slider min/max limits to be INSIDE bounds (strict inequality)
        # in_bounds() check uses: bounds_bottom < value < bounds_top
        # So slider limits must exclude the exact boundary values
        vertical_range = bounds_top - bounds_bottom
        slider_min = bounds_bottom + (vertical_range * 0.0001)  # 0.01% inside
        slider_max = bounds_top - (vertical_range * 0.0001)  # 0.01% inside

        # Floor slider: can't go above ceiling
        # Use additive epsilon (not multiplicative) so it works for zero/negative values
        eps = max((slider_max - slider_min) * 1e-4, 1e-7)
        self._floor_fld.model.set_min(slider_min)
        self._floor_fld.model.set_max(min(slider_max, ceil_val - eps))

        # Ceiling slider: can't go below floor
        self._ceil_fld.model.set_min(max(slider_min, floor_val + eps))
        self._ceil_fld.model.set_max(slider_max)

    def _on_click_build(self, preview=False, rebuild=False, *args):
        """
        Handle click events for minimap generation.

        Validates settings and triggers the minimap generation process with current parameters.
        The generation can be done in different modes:
        - Preview: Quick single-tile generation for entire stage
        - Rebuild: Clear existing tiles and regenerate
        - Normal: Generate additional tiles for current settings

        Args:
            preview (bool): Whether to generate a preview (single tile for entire stage)
            rebuild (bool): Whether to clear existing tiles before generation
            *args: Additional arguments (unused - for compatibility with other functions)

        Note:
            - Preview is useful for quick visualization
            - Rebuild is needed when changing fundamental parameters
            - Normal build appends tiles for current floor/ceiling settings
        """
        self._provider.generate_minimap(
            height_min=self._floor_fld.model.as_float,
            height_max=self._ceil_fld.model.as_float,
            tile_size=self._tsize_fld.model.as_int,
            job_limit=self._jobs_fld.model.as_int,
            preview=preview,
            rebuild=rebuild,
        )

    def _build_menu_stack(self):
        """
        Creates a comprehensive UI layout with controls for:
        1. Ceiling height:
           - Slider for setting upper cutoff
           - RMB menu for selection-based values
           - Init button for auto bounds calculation
        2. Floor height:
           - Slider for setting lower cutoff
           - RMB menu for selection-based values
           - Build button for tile generation (with RMB options)
        3. Tile controls:
           - Number of tiles slider - auto configured
           - Tile size control (64-256m, default: 256m)
        4. Job limit controls:
           - Slider for concurrent job count (1-8)
           - Write button for saving to stage metadata (with RMB options)
        5. Camera size and dev mode:
           - Cam Size slider for FOV indicator (0-1 range)
           - DEV button for performance monitoring toggle
        6. Resolution:
           - Resolution drag for tile quality (256-4096 pixels)
        Note:
            - All spatial fields are based on meters
            - Most controls have RMB context menus
            - Default values are in .toml settings
        """
        l_w = 70
        c_w = 58  # Control and button width (same size) - increased by 5% to fit all digits
        with ui.ZStack(width=0, height=0, style=base_style, mouse_transparent=False, content_clipping=True):

            def block_gestures(h):
                self._window._block_gestures = h

            ui.Rectangle(mouse_hovered_fn=lambda h: block_gestures(h))

            with ui.VStack(spacing=2):
                with ui.HStack(height=10, spacing=2):
                    ui.Spacer(width=2)
                    _lbl = ui.Label("Ceiling (m)", width=l_w)
                    _lbl.tooltip = "Set to the lowest ceiling prim you want to hide."
                    self._ceil_fld = ui.FloatDrag(width=c_w, tooltip="Ceiling height (RMB for more options).")
                    self._ceil_fld.model.set_value(self._settings.get(S_PATH.DEFAULT_CEILING) or 12.0)
                    self._ceil_fld.set_mouse_pressed_fn(lambda x, y, b, m, w=self._ceil_fld: self._menu(b, w))
                    _btn = ui.Button(
                        "Init", name="init", style=btn_style, width=c_w, clicked_fn=partial(self._init_bounds)
                    )
                    _btn.tooltip = "Calculate bounds from selection (auto config)."

                with ui.HStack(height=10, spacing=2):
                    ui.Spacer(width=2)
                    _lbl = ui.Label("Floor (m)", width=l_w)
                    _lbl.tooltip = "Set to the lowest floor prim you want to show."
                    self._floor_fld = ui.FloatDrag(width=c_w, tooltip="Floor height (RMB for more options).")
                    self._floor_fld.model.set_value(self._settings.get(S_PATH.DEFAULT_FLOOR) or 0.0)
                    self._floor_fld.set_mouse_pressed_fn(lambda x, y, b, m, w=self._floor_fld: self._menu(b, w))
                    _btn = ui.Button("Build", name="build", style=btn_style, width=c_w)
                    _btn.set_clicked_fn(partial(self._on_click_build, rebuild=True))
                    _btn.set_mouse_pressed_fn(lambda x, y, b, m, w=_btn: self._menu(b, w))
                    _btn.tooltip = "Generate tiles (RMB for more options)."

                with ui.HStack(height=10, spacing=2):
                    ui.Spacer(width=2)
                    ui.Label(
                        "Tiles | Size", width=l_w, tooltip="Max tiles and tile size\nwork together via bounding box."
                    )
                    _max = self._settings.get(S_PATH.MAX_TILES)
                    self._tiles_fld = ui.IntSlider(width=c_w, min=1, max=_max, tooltip="Number of tiles")
                    _val = self._settings.get(S_PATH.NUM_TILES)
                    self._tiles_fld.model.set_value(_val if _val is not None else 1)
                    max_tile_size = self._settings.get(S_PATH.MAX_TILE_SIZE) or 256
                    self._tsize_fld = ui.IntDrag(width=c_w, min=64, max=max_tile_size, tooltip="Tile size")
                    # Initialize from provider's current tile_size (reads from metadata or settings default)
                    default_tile_size = self._settings.get(S_PATH.DEFAULT_TILE_SIZE) or 256
                    self._tsize_fld.model.set_value(self._provider.tile_size if self._provider else default_tile_size)
                    self._tiles_fld.model.add_end_edit_fn(partial(self.tile_edit, "tiles"))
                    self._tsize_fld.model.add_end_edit_fn(partial(self.tile_edit, "tsize"))

                with ui.HStack(height=10, spacing=2):
                    ui.Spacer(width=2)
                    ui.Label("Max Jobs", width=l_w, tooltip="Maximum jobs, tweak to balance performance and quality.")
                    self._jobs_fld, _ = create_setting_widget(
                        S_PATH.JOB_LIMIT, SettingType.INT, width=c_w, range_from=1, range_to=8
                    )
                    self._jobs_fld.tooltip = "Maximum concurrent jobs."
                    _btn = ui.Button("Write", name="write", style=btn_style, width=c_w)
                    _btn.set_clicked_fn(partial(self._provider.save_tiles))
                    _btn.set_mouse_pressed_fn(lambda x, y, b, m, w=_btn: self._menu(b, w))
                    _btn.tooltip = (
                        "Write tiles to stage metadata (in-memory).\nYou must save the stage manually to persist."
                    )

                with ui.HStack(height=10, spacing=2):
                    ui.Spacer(width=2)
                    ui.Label(
                        "Cam Size", width=l_w, tooltip="Camera FOV indicator size:\n0=10% viewport, 1=33% viewport"
                    )
                    # Load current camera FOV indicator multiplier from window (0-1 range)
                    # Default is 0.5 (21.5% of viewport), per-session only
                    current_indicator = self._window.cam_size if self._window else 0.5
                    self._cam_size_slider = ui.FloatSlider(width=c_w, min=0, max=1)
                    self._cam_size_slider.model.set_value(current_indicator)
                    self._cam_size_slider.tooltip = (
                        "Adjust camera indicator size:\n0 (10% viewport) to 1 (33% viewport).\nResets each session."
                    )
                    # Update window cam_size during drag - no longer rebuilds entire UI
                    self._cam_size_slider.model.add_value_changed_fn(self._on_cam_size_changed)
                    # Developer mode toggle button
                    self._dev_mode_btn = ui.Button("DEV", name="devmode", style=btn_style, width=c_w)
                    self._dev_mode_btn.set_clicked_fn(self._on_dev_mode_toggle)
                    self._dev_mode_btn.set_tooltip(
                        "Toggle developer mode for performance monitoring.\nResets each session."
                    )
                    self._update_dev_mode_button()

                with ui.HStack(height=10, spacing=2):
                    ui.Spacer(width=2)
                    ui.Label(
                        "Resolution",
                        width=l_w,
                        tooltip="Minimap resolution quality (pixels per stage unit).\nHigher = sharper but more VRAM.",
                    )
                    # Resolution drag - any value from 256-4096
                    self._resolution_drag = ui.IntDrag(width=c_w, min=256, max=4096)
                    # Initialize from provider first (includes metadata), fallback to settings
                    _res = self._provider.resolution if self._provider else self._settings.get(S_PATH.RESOLUTION)
                    self._resolution_drag.model.set_value(_res if _res is not None else 1024)
                    self._resolution_drag.model.add_end_edit_fn(self._on_resolution_changed)
                    self._resolution_drag.tooltip = (
                        "Pixels per stage unit.\nMultiples of 256 recommended:\n256, 512, 768, 1024, 1536, 2048, etc."
                    )

    def _init_frame(self):
        """
        Initialize the main UI frame.

        Creates the base frame and adds the menu stack to it.
        Visibility is controlled by window events after stage loading completes.
        """
        with self._frame:
            with ui.VStack(spacing=0, mouse_transparent=False):
                ui.Spacer()
                with ui.HStack(height=0):
                    ui.Spacer(width=5)
                    self._build_menu_stack()
                ui.Spacer(height=5)
        # Set initial visibility to match default show_settings value
        self._frame.visible = self._window.show_settings
