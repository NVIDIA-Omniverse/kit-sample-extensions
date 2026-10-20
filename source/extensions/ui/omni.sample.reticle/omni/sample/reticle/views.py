# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from functools import partial

import omni.ui as ui
from omni.ui import color as cl
from omni.ui import scene

from . import styles
from .constants import CompositionGuidelines
from .models import ReticleModel


class ReticleScene:
    """Viewport layer wrapper for RegisterViewportLayer registry.

    This class is instantiated automatically by RegisterViewportLayer for each viewport.
    When the constructor is called, a ui.Frame is already in scope, allowing direct
    creation of both omni.ui and omni.ui.scene elements.

    """

    def __init__(self, vp_args: dict):
        """Initialize the reticle layer for a viewport.

        Args:
            vp_args: Dictionary containing viewport info from the registry.
                     Contains 'viewport_api' key with the viewport API instance.
        """
        self._vp_api = vp_args["viewport_api"]
        self._model = ReticleModel()
        self._root = None
        self.scene_view = None
        self.reticle_menu = None

        # Get initial aspect ratio from render resolution
        resolution = self._vp_api.resolution
        self._aspect_ratio = resolution[0] / resolution[1]

        # Subscribe to render resolution changes
        self._view_change_sub = self._vp_api.subscribe_to_render_settings_change(self._on_viewport_changed)

        # Rebuild the overlay whenever the model changes
        self._model.add_reticle_changed_fn(self._rebuild)

        # Build the UI - ui.Frame is already in scope from RegisterViewportLayer
        self._build_ui()

    def _build_ui(self):
        """Build the reticle UI. Called from constructor where ui.Frame is in scope."""
        # Get render resolution for aspect ratio calculation
        width, height = self._vp_api.resolution

        # Create root container - ui.Frame is already in scope from RegisterViewportLayer
        self._root = ui.ZStack()
        with self._root:
            # Set the aspect ratio policy depending if the viewport is wider than it is taller or vice versa.
            if width / height > self._get_aspect_ratio_flip_threshold():
                self.scene_view = scene.SceneView(aspect_ratio_policy=scene.AspectRatioPolicy.PRESERVE_ASPECT_VERTICAL)
            else:
                self.scene_view = scene.SceneView(
                    aspect_ratio_policy=scene.AspectRatioPolicy.PRESERVE_ASPECT_HORIZONTAL
                )

            # Build all the scene view guidelines
            with self.scene_view.scene:
                self._build_scene_content()

            # Build ReticleMenu button
            with ui.VStack():
                ui.Spacer()
                with ui.HStack(height=0):
                    ui.Spacer()
                    self.reticle_menu = ReticleMenu(self._model)

    def _rebuild(self, *args):
        """Rebuild the overlay when model or viewport changes."""
        if self._vp_api is None or self._root is None:
            return

        # Update aspect ratio
        width, height = self._vp_api.resolution
        self._aspect_ratio = width / height

        # Clear and rebuild scene content
        if self.scene_view is not None:
            self.scene_view.scene.clear()
            with self.scene_view.scene:
                self._build_scene_content()

    def _build_scene_content(self):
        """Build the scene content (guidelines, safe areas, letterbox)."""
        if self._model.composition_mode.as_int == CompositionGuidelines.THIRDS:
            self._build_thirds()
        elif self._model.composition_mode.as_int == CompositionGuidelines.QUAD:
            self._build_quad()
        elif self._model.composition_mode.as_int == CompositionGuidelines.CROSSHAIR:
            self._build_crosshair()

        if self._model.action_safe_enabled.as_bool:
            self._build_safe_rect(self._model.action_safe_percentage.as_float / 100.0, color=cl.action_safe_default)
        if self._model.title_safe_enabled.as_bool:
            self._build_safe_rect(self._model.title_safe_percentage.as_float / 100.0, color=cl.title_safe_default)
        if self._model.custom_safe_enabled.as_bool:
            self._build_safe_rect(self._model.custom_safe_percentage.as_float / 100.0, color=cl.custom_safe_default)
        if self._model.letterbox_enabled.as_bool:
            self._build_letterbox()

    def _on_viewport_changed(self, *args):
        """Update aspect ratio and rebuild overlay when viewport resolution changes."""
        width, height = self._vp_api.resolution
        new_ratio = width / height
        if abs(new_ratio - self._aspect_ratio) < 1e-3:
            return
        self._rebuild()

    def _get_aspect_ratio_flip_threshold(self):
        """Get threshold value for determining aspect ratio policy."""
        return self._aspect_ratio - self._aspect_ratio * 0.05

    def destroy(self):
        """Clean up resources when viewport is destroyed."""
        self._view_change_sub = None
        if hasattr(self, "scene_view") and self.scene_view is not None:
            self.scene_view.scene.clear()
            self.scene_view = None
        if hasattr(self, "reticle_menu") and self.reticle_menu is not None:
            self.reticle_menu.destroy()
            self.reticle_menu = None
        if hasattr(self, "_root") and self._root is not None:
            self._root.clear()
            self._root = None
        self._vp_api = None
        self._model = None

    def __del__(self):
        self.destroy()

    @property
    def visible(self):
        """Get visibility state of the reticle layer."""
        if self._root is not None:
            return self._root.visible
        return False

    @visible.setter
    def visible(self, value: bool):
        """Set visibility state of the reticle layer."""
        if self._root is not None:
            self._root.visible = value

    def _get_aspect_ratio(self):
        """Get the aspect ratio of the viewport."""
        return self._aspect_ratio

    def _build_thirds(self):
        """Build the scene ui graphics for the Thirds composition mode."""
        aspect_ratio = self._get_aspect_ratio()
        line_color = cl.comp_lines_default
        inverse_ratio = 1 / aspect_ratio
        if self.scene_view.aspect_ratio_policy == scene.AspectRatioPolicy.PRESERVE_ASPECT_VERTICAL:
            scene.Line([-0.333 * aspect_ratio, -1, 0], [-0.333 * aspect_ratio, 1, 0], color=line_color)
            scene.Line([0.333 * aspect_ratio, -1, 0], [0.333 * aspect_ratio, 1, 0], color=line_color)
            scene.Line([-aspect_ratio, -0.333, 0], [aspect_ratio, -0.333, 0], color=line_color)
            scene.Line([-aspect_ratio, 0.333, 0], [aspect_ratio, 0.333, 0], color=line_color)
        else:
            scene.Line([-1, -0.333 * inverse_ratio, 0], [1, -0.333 * inverse_ratio, 0], color=line_color)
            scene.Line([-1, 0.333 * inverse_ratio, 0], [1, 0.333 * inverse_ratio, 0], color=line_color)
            scene.Line([-0.333, -inverse_ratio, 0], [-0.333, inverse_ratio, 0], color=line_color)
            scene.Line([0.333, -inverse_ratio, 0], [0.333, inverse_ratio, 0], color=line_color)

    def _build_quad(self):
        """Build the scene ui graphics for the Quad composition mode."""
        aspect_ratio = self._get_aspect_ratio()
        line_color = cl.comp_lines_default
        inverse_ratio = 1 / aspect_ratio
        if self.scene_view.aspect_ratio_policy == scene.AspectRatioPolicy.PRESERVE_ASPECT_VERTICAL:
            scene.Line([0, -1, 0], [0, 1, 0], color=line_color)
            scene.Line([-aspect_ratio, 0, 0], [aspect_ratio, 0, 0], color=line_color)
        else:
            scene.Line([0, -inverse_ratio, 0], [0, inverse_ratio, 0], color=line_color)
            scene.Line([-1, 0, 0], [1, 0, 0], color=line_color)

    def _build_crosshair(self):
        """Build the scene ui graphics for the Crosshair composition mode."""
        aspect_ratio = self._get_aspect_ratio()
        line_color = cl.comp_lines_default
        if self.scene_view.aspect_ratio_policy == scene.AspectRatioPolicy.PRESERVE_ASPECT_VERTICAL:
            scene.Line([0, 0.05 * aspect_ratio, 0], [0, 0.1 * aspect_ratio, 0], color=line_color)
            scene.Line([0, -0.05 * aspect_ratio, 0], [0, -0.1 * aspect_ratio, 0], color=line_color)
            scene.Line([0.05 * aspect_ratio, 0, 0], [0.1 * aspect_ratio, 0, 0], color=line_color)
            scene.Line([-0.05 * aspect_ratio, 0, 0], [-0.1 * aspect_ratio, 0, 0], color=line_color)
        else:
            scene.Line([0, 0.05, 0], [0, 0.1, 0], color=line_color)
            scene.Line([0, -0.05, 0], [0, -0.1, 0], color=line_color)
            scene.Line([0.05, 0, 0], [0.1, 0, 0], color=line_color)
            scene.Line([-0.05, 0, 0], [-0.1, 0, 0], color=line_color)

        scene.Points([[0.00005, 0, 0]], sizes=[2], colors=[line_color])

    def _build_safe_rect(self, percentage, color):
        """Build the scene ui graphics for the safe area rectangle

        Args:
            percentage (float): The 0-1 percentage the render target that the rectangle should fill.
            color: The color to draw the rectangle wireframe with.
        """
        aspect_ratio = self._get_aspect_ratio()
        inverse_ratio = 1 / aspect_ratio
        if self.scene_view.aspect_ratio_policy == scene.AspectRatioPolicy.PRESERVE_ASPECT_VERTICAL:
            scene.Rectangle(aspect_ratio * 2 * percentage, 1 * 2 * percentage, thickness=1, wireframe=True, color=color)
        else:
            scene.Rectangle(
                1 * 2 * percentage, inverse_ratio * 2 * percentage, thickness=1, wireframe=True, color=color
            )

    def _build_letterbox(self):
        """Build the scene ui graphics for the letterbox.

        The letterbox effect creates black bars at the top and bottom (or sides) of the viewport
        to achieve a specific aspect ratio. The calculations differ based on whether we're in
        vertical or horizontal aspect ratio preservation mode.

        For vertical mode (when viewport is wider than taller):
        - If letterbox_ratio >= aspect_ratio: Add black bars at top and bottom
        - If letterbox_ratio < aspect_ratio: Add black bars at sides

        For horizontal mode (when viewport is taller than wider):
        - If letterbox_ratio >= aspect_ratio: Add black bars at sides
        - If letterbox_ratio < aspect_ratio: Add black bars at top and bottom
        """
        aspect_ratio = self._get_aspect_ratio()
        letterbox_color = cl.letterbox_default
        letterbox_ratio = self._model.letterbox_ratio.as_float

        def build_letterbox_helper(width, height, x_offset, y_offset):
            """Helper function to create letterbox rectangles.

            Args:
                width (float): Width of the letterbox rectangle
                height (float): Height of the letterbox rectangle
                x_offset (float): X offset from center
                y_offset (float): Y offset from center
            """
            move = scene.Matrix44.get_translation_matrix(x_offset, y_offset, 0)
            with scene.Transform(transform=move):
                scene.Rectangle(width * 2, height * 2, thickness=0, wireframe=False, color=letterbox_color)
            move = scene.Matrix44.get_translation_matrix(-x_offset, -y_offset, 0)
            with scene.Transform(transform=move):
                scene.Rectangle(width * 2, height * 2, thickness=0, wireframe=False, color=letterbox_color)

        if self.scene_view.aspect_ratio_policy == scene.AspectRatioPolicy.PRESERVE_ASPECT_VERTICAL:
            # Vertical mode: viewport is wider than taller
            if letterbox_ratio >= aspect_ratio:
                # Add black bars at top and bottom
                # Calculate height of black bars: total height - (width / letterbox_ratio)
                height = 1 - aspect_ratio / letterbox_ratio
                rect_height = height / 2  # Split height between top and bottom
                rect_offset = 1 - rect_height  # Offset from center
                build_letterbox_helper(aspect_ratio, rect_height, 0, rect_offset)
            else:
                # Add black bars at sides
                # Calculate width of black bars: current width - (height * letterbox_ratio)
                width = aspect_ratio - letterbox_ratio
                rect_width = width / 2  # Split width between left and right
                rect_offset = aspect_ratio - rect_width  # Offset from center
                build_letterbox_helper(rect_width, 1, rect_offset, 0)
        else:
            # Horizontal mode: viewport is taller than wider
            inverse_ratio = 1 / aspect_ratio
            if letterbox_ratio >= aspect_ratio:
                # Add black bars at sides
                # Calculate height of black bars: inverse_ratio - (1 / letterbox_ratio)
                height = inverse_ratio - 1 / letterbox_ratio
                rect_height = height / 2  # Split height between left and right
                rect_offset = inverse_ratio - rect_height  # Offset from center
                build_letterbox_helper(1, rect_height, 0, rect_offset)
            else:
                # Add black bars at top and bottom
                # Calculate width of black bars: (aspect_ratio - letterbox_ratio) * inverse_ratio
                width = (aspect_ratio - letterbox_ratio) * inverse_ratio
                rect_width = width / 2  # Split width between top and bottom
                rect_offset = 1 - rect_width  # Offset from center
                build_letterbox_helper(rect_width, inverse_ratio, rect_offset, 0)


class ReticleMenu:
    """The popup reticle menu"""

    def __init__(self, model: ReticleModel):
        """ReticleMenu constructor

        Stores the model and builds the Reticle button.

        Args:
            model (ReticleModel): The reticle model
        """
        self.model = model
        self.button = ui.Button(
            "Reticle",
            width=120,
            height=0,
            mouse_pressed_fn=self.show_reticle_menu,
            style={"margin": 64, "padding": 15, "margin_height": 64, "margin_width": 16},
        )
        self.reticle_menu = None

    def destroy(self):
        self.button.destroy()
        self.button = None
        self.reticle_menu = None

    def on_group_check_changed(self, safe_area_group, model):
        """Enables/disables safe area groups

        When a safe area checkbox state changes, all the widgets of the respective
        group should be enabled/disabled.

        Args:
            safe_area_group (HStack): The safe area group to enable/disable
            model (SimpleBoolModel): The safe group checkbox model.
        """
        safe_area_group.enabled = model.as_bool

    def on_composition_mode_changed(self, guideline_type):
        """Sets the selected composition mode.

        When a composition button is clicked, it should be checked on and the other
        buttons should be checked off. Sets the composition mode on the ReticleModel too.

        Args:
            guideline_type (CompositionGuidelines): The composition guideline type to set.
        """
        self.model.composition_mode.set_value(guideline_type)
        self.comp_off_button.checked = guideline_type == CompositionGuidelines.OFF
        self.comp_thirds_button.checked = guideline_type == CompositionGuidelines.THIRDS
        self.comp_quad_button.checked = guideline_type == CompositionGuidelines.QUAD
        self.comp_crosshair_button.checked = guideline_type == CompositionGuidelines.CROSSHAIR

    def show_reticle_menu(self, x, y, button, modifier):
        """Build and show the reticle menu popup."""
        self.reticle_menu = ui.Menu(menu_compatibility=False, width=400, height=200)
        self.reticle_menu.clear()

        with self.reticle_menu:
            with ui.Frame(width=0, height=100):
                with ui.HStack():
                    with ui.VStack():
                        ui.Label("Composition", alignment=ui.Alignment.LEFT, height=30)
                        with ui.VGrid(
                            style=styles.comp_group_style, width=150, height=0, column_count=2, row_height=75
                        ):
                            current_comp_mode = self.model.composition_mode.as_int
                            with ui.HStack():
                                off_checked = current_comp_mode == CompositionGuidelines.OFF
                                callback = partial(self.on_composition_mode_changed, CompositionGuidelines.OFF)
                                self.comp_off_button = ui.Button(
                                    "Off", name="Off", checked=off_checked, width=70, height=70, clicked_fn=callback
                                )
                            with ui.HStack():
                                thirds_checked = current_comp_mode == CompositionGuidelines.THIRDS
                                callback = partial(self.on_composition_mode_changed, CompositionGuidelines.THIRDS)
                                self.comp_thirds_button = ui.Button(
                                    "Thirds",
                                    name="Thirds",
                                    checked=thirds_checked,
                                    width=70,
                                    height=70,
                                    clicked_fn=callback,
                                )
                            with ui.HStack():
                                quad_checked = current_comp_mode == CompositionGuidelines.QUAD
                                callback = partial(self.on_composition_mode_changed, CompositionGuidelines.QUAD)
                                self.comp_quad_button = ui.Button(
                                    "Quad", name="Quad", checked=quad_checked, width=70, height=70, clicked_fn=callback
                                )
                            with ui.HStack():
                                crosshair_checked = current_comp_mode == CompositionGuidelines.CROSSHAIR
                                callback = partial(self.on_composition_mode_changed, CompositionGuidelines.CROSSHAIR)
                                self.comp_crosshair_button = ui.Button(
                                    "Crosshair",
                                    name="Crosshair",
                                    checked=crosshair_checked,
                                    width=70,
                                    height=70,
                                    clicked_fn=callback,
                                )
                    ui.Spacer(width=10)
                    with ui.VStack(style=styles.safe_areas_group_style):
                        ui.Label("Safe Areas", alignment=ui.Alignment.LEFT, height=30)
                        with ui.HStack(width=0):
                            ui.Spacer(width=20)
                            cb = ui.CheckBox(model=self.model.action_safe_enabled)
                            action_safe_group = ui.HStack(enabled=self.model.action_safe_enabled.as_bool)
                            callback = partial(self.on_group_check_changed, action_safe_group)
                            cb.model.add_value_changed_fn(callback)
                            with action_safe_group:
                                ui.Spacer(width=10)
                                ui.Label("Action Safe", alignment=ui.Alignment.TOP)
                                ui.Spacer(width=14)
                                with ui.VStack():
                                    ui.FloatSlider(
                                        self.model.action_safe_percentage,
                                        width=100,
                                        format="%.0f%%",
                                        min=0,
                                        max=100,
                                        step=1,
                                    )
                                    ui.Rectangle(name="ActionSwatch", height=5)
                                    ui.Spacer()
                        with ui.HStack(width=0):
                            ui.Spacer(width=20)
                            cb = ui.CheckBox(model=self.model.title_safe_enabled)
                            title_safe_group = ui.HStack(enabled=self.model.title_safe_enabled.as_bool)
                            callback = partial(self.on_group_check_changed, title_safe_group)
                            cb.model.add_value_changed_fn(callback)
                            with title_safe_group:
                                ui.Spacer(width=10)
                                ui.Label("Title Safe", alignment=ui.Alignment.TOP)
                                ui.Spacer(width=25)
                                with ui.VStack():
                                    ui.FloatSlider(
                                        self.model.title_safe_percentage,
                                        width=100,
                                        format="%.0f%%",
                                        min=0,
                                        max=100,
                                        step=1,
                                    )
                                    ui.Rectangle(name="TitleSwatch", height=5)
                                    ui.Spacer()
                        with ui.HStack(width=0):
                            ui.Spacer(width=20)
                            cb = ui.CheckBox(model=self.model.custom_safe_enabled)
                            custom_safe_group = ui.HStack(enabled=self.model.custom_safe_enabled.as_bool)
                            callback = partial(self.on_group_check_changed, custom_safe_group)
                            cb.model.add_value_changed_fn(callback)
                            with custom_safe_group:
                                ui.Spacer(width=10)
                                ui.Label("Custom Safe", alignment=ui.Alignment.TOP)
                                ui.Spacer(width=5)
                                with ui.VStack():
                                    ui.FloatSlider(
                                        self.model.custom_safe_percentage,
                                        width=100,
                                        format="%.0f%%",
                                        min=0,
                                        max=100,
                                        step=1,
                                    )
                                    ui.Rectangle(name="CustomSwatch", height=5)
                                    ui.Spacer()
                        ui.Label("Letterbox", alignment=ui.Alignment.LEFT, height=30)
                        with ui.HStack(width=0):
                            ui.Spacer(width=20)
                            cb = ui.CheckBox(model=self.model.letterbox_enabled)
                            letterbox_group = ui.HStack(enabled=self.model.letterbox_enabled.as_bool)
                            callback = partial(self.on_group_check_changed, letterbox_group)
                            cb.model.add_value_changed_fn(callback)
                            with letterbox_group:
                                ui.Spacer(width=10)
                                ui.Label("Letterbox Ratio", alignment=ui.Alignment.TOP)
                                ui.Spacer(width=5)
                                ui.FloatDrag(self.model.letterbox_ratio, width=35, min=0.001, step=0.01)
        self.reticle_menu.show_at(x - self.reticle_menu.width, y - self.reticle_menu.height)
