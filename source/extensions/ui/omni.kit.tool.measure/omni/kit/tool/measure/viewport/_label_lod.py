# Copyright (c) 2026, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

"""Zoom-out label level of detail: show the measurement name when a measurement is small on screen."""

from enum import Enum
from math import hypot, inf
from typing import Iterable, Optional

from carb.settings import get_settings
from pxr import Gf

SETTINGS_LABEL_LOD_ENABLED = "/exts/omni.kit.tool.measure/label_lod_enabled"
SETTINGS_LABEL_LOD_ENTER_PX = "/exts/omni.kit.tool.measure/label_lod_enter_px"
SETTINGS_LABEL_LOD_EXIT_PX = "/exts/omni.kit.tool.measure/label_lod_exit_px"
DEFAULT_ENTER_PX = 60.0
DEFAULT_EXIT_PX = 90.0


class LabelMode(Enum):
    DETAIL = 0
    NAME = 1


def clamp_thresholds(enter_px: float, exit_px: float):
    """Return (enter, exit) with exit strictly greater than enter."""
    enter_px = max(0.0, float(enter_px))
    exit_px = float(exit_px)
    if exit_px <= enter_px:
        exit_px = enter_px + 1.0
    return enter_px, exit_px


def decide_label_mode(span_px: float, previous: LabelMode, enter_px: float, exit_px: float) -> LabelMode:
    """Hysteresis: switch to NAME below enter, back to DETAIL above exit, otherwise keep the previous mode."""
    enter_px, exit_px = clamp_thresholds(enter_px, exit_px)
    if span_px < enter_px:
        return LabelMode.NAME
    if span_px > exit_px:
        return LabelMode.DETAIL
    return previous


def compute_screen_span(points: Iterable, viewport_api, viewport_size: Optional[tuple] = None) -> float:
    """Return the projected bounding-box diagonal in viewport pixels (inf if unknown).

    Pass the displayed viewport size to measure in UI pixels. The render resolution
    remains the fallback for callers that do not provide a display size.

    If any point is on or behind the camera plane (clip w <= 1e-9), return inf to
    retain DETAIL labels. Projecting only the points in front would underestimate
    a segment crossing that plane; clipping such segments is not supported here.
    """
    if viewport_api is None:
        return inf
    resolution = viewport_size if viewport_size is not None else viewport_api.resolution
    if not resolution or resolution[0] <= 0 or resolution[1] <= 0:
        return inf
    world_to_ndc = viewport_api.world_to_ndc
    half_w, half_h = resolution[0] * 0.5, resolution[1] * 0.5

    min_x = min_y = inf
    max_x = max_y = -inf
    for point in points:
        clip = Gf.Vec4d(point[0], point[1], point[2], 1.0) * world_to_ndc
        if clip[3] <= 1e-9:
            return inf
        x, y = clip[0] / clip[3] * half_w, clip[1] / clip[3] * half_h
        min_x, max_x = min(min_x, x), max(max_x, x)
        min_y, max_y = min(min_y, y), max(max_y, y)

    if min_x == inf:
        return inf
    return hypot(max_x - min_x, max_y - min_y)


class LabelLodController:
    """Re-evaluates labels on camera, viewport size, or settings changes and redraws only items that flip."""

    def __init__(self, viewport_api, model, scene_view=None):
        self._viewport_api = viewport_api
        self._model = model
        self._scene_view = scene_view
        self._settings = get_settings()
        self._cached_settings = self._read_settings()
        self._settings_subs = [
            self._settings.subscribe_to_node_change_events(path, self._on_setting_changed)
            for path in (SETTINGS_LABEL_LOD_ENABLED, SETTINGS_LABEL_LOD_ENTER_PX, SETTINGS_LABEL_LOD_EXIT_PX)
        ]
        self._view_sub = viewport_api.subscribe_to_view_change(self._on_view_changed) if viewport_api else None
        if self._scene_view is not None:
            self._scene_view.set_computed_content_size_changed_fn(self._on_viewport_size_changed)

    def destroy(self) -> None:
        scene_view, self._scene_view = self._scene_view, None
        try:
            if scene_view is not None:
                scene_view.set_computed_content_size_changed_fn(None)
        except (RuntimeError, ReferenceError):
            # The viewport window may have destroyed its SceneView first.
            pass
        finally:
            # Subscription cleanup must not depend on the widget's lifetime.
            for sub in self._settings_subs:
                self._settings.unsubscribe_to_change_events(sub)
            self._settings_subs = []
            self._view_sub = None
            self._viewport_api = None
            self._model = None

    def _read_settings(self):
        enabled = self._settings.get(SETTINGS_LABEL_LOD_ENABLED)
        enter_px = self._settings.get(SETTINGS_LABEL_LOD_ENTER_PX)
        exit_px = self._settings.get(SETTINGS_LABEL_LOD_EXIT_PX)
        enabled = False if enabled is None else bool(enabled)
        enter_px = DEFAULT_ENTER_PX if enter_px is None else enter_px
        exit_px = DEFAULT_EXIT_PX if exit_px is None else exit_px
        return (enabled, *clamp_thresholds(enter_px, exit_px))

    def _get_viewport_size(self) -> Optional[tuple]:
        if self._scene_view is None:
            return None
        # world_to_ndc is conformed to this canvas, not to the rendered texture.
        # Logical UI pixels also match the screen-scaled measurement labels.
        return self._scene_view.computed_width, self._scene_view.computed_height

    def resolve(self, item, settings: Optional[tuple] = None, viewport_size: Optional[tuple] = None) -> LabelMode:
        """Update the item's hysteresis state and return the label mode it should render."""
        enabled, enter_px, exit_px = settings if settings is not None else self._cached_settings
        if not enabled:
            item._lod_state = LabelMode.DETAIL
            return LabelMode.DETAIL

        points = item.payload.computed_points or []
        if viewport_size is None:
            viewport_size = self._get_viewport_size()
        span = compute_screen_span(points, self._viewport_api, viewport_size)
        item._lod_state = decide_label_mode(span, item._lod_state, enter_px, exit_px)
        if item._lod_state == LabelMode.NAME and item.payload.name:
            return LabelMode.NAME
        return LabelMode.DETAIL

    def refresh(self) -> None:
        if not self._model:
            return
        settings = self._cached_settings
        viewport_size = self._get_viewport_size()
        for item in list(self._model.measurements.values()):
            if item._label_lod is not self or item._lbl_root is None or not item.visible:
                continue
            if self.resolve(item, settings, viewport_size) != item._label_mode:
                self._model._item_changed(item)

    def _on_view_changed(self, *_):
        if self._cached_settings[0]:
            self.refresh()

    def _on_viewport_size_changed(self, *_):
        # A resize with unchanged aspect ratio does not trigger a view change.
        if self._cached_settings[0]:
            self.refresh()

    def _on_setting_changed(self, *_):
        self._cached_settings = self._read_settings()
        # Disabling must refresh once to restore detail labels. Subsequent camera
        # and viewport size changes can skip the measurement loop while disabled.
        self.refresh()
