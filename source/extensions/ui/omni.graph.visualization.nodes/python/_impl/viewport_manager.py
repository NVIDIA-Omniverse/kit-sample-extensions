# Copyright (c) 2022-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from typing import Callable

import carb.events
import omni.graph.core as ogc
import omni.kit.app
import omni.kit.viewport.utility as vp_utils
import omni.ui as ui
from carb import log_error
from omni.kit.viewport.registry import RegisterViewportLayer

DRAW_ON_VP1 = True


# This borrows heavily from the approach in omni.kit.manipulator.viewport, but simplified
# because we are only providing a layout for omni.ui elements (no omni.ui.scene stuff)
class ViewportManager:
    _instance = None

    class ViewportNextFactory:
        def __init__(self, factory_args, *ui_args, **ui_kwargs):
            ui_kwargs["build_fn"] = ViewportManager._instance._build_fn
            self._ui_frame = ui.Frame(*ui_args, **ui_kwargs)

            if ViewportManager._instance is not None:
                ViewportManager._instance._factories.append(self)

        def destroy(self):
            self._ui_frame.destroy()
            self._ui_frame = None

    @classmethod
    def request_rebuild(cls):
        cls._instance._needs_rebuild = True

    @classmethod
    def add_layout_builder(cls, node_path, build_fn: Callable):
        if cls._instance._layout_builders.get(node_path) == build_fn:
            return
        cls._instance._layout_builders[node_path] = build_fn
        cls.request_rebuild()

    @classmethod
    def remove_layout_builder(cls, node_path):
        cls._instance._layout_builders.pop(node_path, None)
        cls.request_rebuild()

    def __init__(self):
        self._vp2_layer = None
        self._vp1_overlay_window = None
        self._vp1_window = None
        self._update_sub = None
        self._factories = None
        self._layout_builders = None

    def startup(self):
        self._layout_builders = {}
        self._factories = []

        ViewportManager._instance = self
        ViewportManager.request_rebuild()

        self._update_sub = omni.kit.app.get_app().get_update_event_stream().create_subscription_to_pop(self._on_update)

        # This remains messy -- choosing either VP1 or VP2, but not both.
        # In the future this should be moved to VP2-only, and tested with multiple VP2 windows.
        global DRAW_ON_VP1
        DRAW_ON_VP1 = False
        viewport_api = vp_utils.get_active_viewport()
        if hasattr(viewport_api, "legacy_window"):
            DRAW_ON_VP1 = True

        if DRAW_ON_VP1:
            self._vp1_window = None
            self._vp1_overlay_window = None
            self._create_vp1_overlay()
        else:
            self._vp2_layer = RegisterViewportLayer(
                self.ViewportNextFactory, "omni.graph.visualization.nodes.ViewportManager"
            )

    def shutdown(self):
        self._layout_builders.clear()
        self._factories.clear()
        ViewportManager._instance = None
        self._update_sub = None
        if DRAW_ON_VP1:
            self._vp1_window = None
            self._vp1_overlay_window.destroy()
            self._vp1_overlay_window = None
        else:
            self._vp2_layer.destroy()
            self._vp2_layer = None

    def _create_vp1_overlay(self):
        self._vp1_window = vp_utils.get_active_viewport_window()
        self._vp1_overlay_window = ui.Window(self._vp1_window.name, detachable=False)

    def _on_update(self, e: carb.events.IEvent):
        if DRAW_ON_VP1:
            self._update_vp1()
        else:
            self._update_vp2()
        self._needs_rebuild = False

    def _build_fn(self):
        with ui.ZStack():
            for node_path, builder in self._layout_builders.items():
                node = ogc.get_node_by_path(node_path)
                if node.is_valid():
                    builder(node)
                else:
                    log_error(f"Invalid node: {node_path}")

    def _update_vp1(self):
        if self._vp1_overlay_window and self._vp1_window:
            if self._needs_rebuild:
                with self._vp1_overlay_window.frame:
                    self._build_fn()

    def _update_vp2(self):
        if self._needs_rebuild:
            for factory in self._factories:
                if factory._ui_frame is not None:
                    factory._ui_frame.rebuild()
