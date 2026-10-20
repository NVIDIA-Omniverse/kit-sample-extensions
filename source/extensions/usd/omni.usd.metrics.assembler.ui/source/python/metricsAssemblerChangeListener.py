# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from collections import namedtuple

import carb
import carb.profiler
import carb.settings
import omni.metrics.assembler.core.bindings._metricsAssembler as metricsAssembler
import omni.usd
from carb.eventdispatcher import get_eventdispatcher
from pxr import Sdf, Tf, Usd

from .tools import re_resolve_layer, remove_resolve_information

ResolveData = namedtuple("ResolveData", ["url", "layer_id"])


class MetricsAssemblerChangeListener:
    """Listener class that monitors and handles changes to metrics assembly operations.

    This class listens for changes to USD stages and prims that may affect metrics assembly,
    such as unit mismatches between referenced files. It handles re-resolving metrics when
    needed and maintains state about which paths need updating.
    """

    def __init__(self, maManager: "MetricsAssemblerManager") -> None:
        """Initialize the metrics assembler change listener.

        Args:
            maManager: The metrics assembler manager instance
        """
        self.__settings_subs = []
        self.__settings_subs.append(
            omni.kit.app.SettingChangeSubscription(
                metricsAssembler.SETTINGS_METRICS_ASSEMBLER_PARAMS_CHANGE_LISTENER_ENABLED,
                self._param_listener_setting_changed,
            )
        )
        self.__listener_enabled = carb.settings.get_settings().get_as_int(
            metricsAssembler.SETTINGS_METRICS_ASSEMBLER_PARAMS_CHANGE_LISTENER_ENABLED
        )
        self.__params_usd_listener = None
        self.__paths_dict = {}
        self.__re_resolved_paths = set()
        self.__resync_paths = set()
        self.__update_sub = None
        self.__listen_to_changes = True
        self.__stage = None
        self.__ma_manager = maManager

    def on_shutdown(self) -> None:
        """Clean up resources when shutting down."""
        self.__settings_subs = []
        self._reset()

    def on_stage_opened(self, stage: Usd.Stage) -> None:
        """Handle a new stage being opened.

        Args:
            stage: The USD stage that was opened
        """
        self._reset()
        self.__stage = stage

    def on_stage_closed(self) -> None:
        """Handle the current stage being closed."""
        self._reset()
        self.__stage = None

    def set_stage(self, stage: Usd.Stage) -> None:
        """Set the current USD stage.

        Args:
            stage: The USD stage to set as current
        """
        self.__stage = stage

    def add_path(self, path: Sdf.Path, url: str, write_layer: Sdf.Layer | None) -> None:
        """Add a path to monitor for metrics assembly changes.

        Args:
            path: USD path to monitor
            url: Asset URL associated with the path
            write_layer: Layer to write changes to
        """
        layer_id = None
        if write_layer:
            layer_id = write_layer.identifier
        self.__paths_dict[path] = ResolveData(url, layer_id)
        self._register_listener()
        if not self.__update_sub:
            self.__update_sub = get_eventdispatcher().observe_event(
                event_name=omni.kit.app.GLOBAL_EVENT_UPDATE,
                on_event=self._on_metrics_assembler_update,
                observer_name="omni.metrics.assembler.ui",
            )

    def get_path_url_info(self, path: Sdf.Path) -> str | None:
        """Get the asset URL associated with a monitored path.

        Args:
            path: USD path to get URL for

        Returns:
            str: The asset URL, or None if path not found
        """
        data = self.__paths_dict.get(path)
        if data:
            return data.url
        else:
            return None

    def prim_rename(self, pre_path: Sdf.Path, post_path: Sdf.Path) -> None:
        """Update monitoring when a prim is renamed.

        Args:
            pre_path: Original path of the prim
            post_path: New path of the prim
        """
        data = self.__paths_dict.get(pre_path)
        if data:
            self.__paths_dict[post_path] = data
            del self.__paths_dict[pre_path]

    def _re_resolve_path_check(self, path: Sdf.Path) -> bool:
        """Check if a path needs metrics re-resolution and perform it if needed.

        Args:
            path: USD path to check

        Returns:
            bool: True if resolution succeeded or wasn't needed, False if failed
        """
        parentPath = path
        while (parentPath != Sdf.Path.emptyPath) and (parentPath.name != Sdf.Path.parentPathElement):
            data = self.__paths_dict.get(parentPath)
            if data and parentPath not in self.__re_resolved_paths:
                url = data.url
                layer_id = data.layer_id
                if path == parentPath and self.__stage:
                    prim = self.__stage.GetPrimAtPath(path)
                    if prim:
                        # resync on the top prim happened, check if payload or reference name did not changed
                        ref_and_layers = omni.usd.get_composed_payloads_from_prim(prim, False)
                        asset_path = None
                        if len(ref_and_layers) == 0:
                            ref_and_layers = omni.usd.get_composed_references_from_prim(prim, False)
                        if len(ref_and_layers) > 0:
                            ref, _ = ref_and_layers[0]
                            asset_path = ref.assetPath
                        else:
                            return False
                        if asset_path != url:
                            url = asset_path

                # re-resolve on the full path for now
                write_layer = re_resolve_layer(self.__stage, self.__ma_manager, url, parentPath, layer_id)
                if write_layer:
                    layer_id = write_layer.identifier
                else:
                    layer_id = None

                self.__re_resolved_paths.add(parentPath)
                self.__paths_dict[parentPath] = ResolveData(url, layer_id)
                return True
            parentPath = parentPath.GetParentPath()
        return True

    def _remove_path_check(self, path: Sdf.Path) -> None:
        """Remove a path from monitoring and clean up its metrics resolution.

        Args:
            path: USD path to remove
        """
        data = self.__paths_dict.get(path)
        if data:
            remove_resolve_information(self.__stage, path)
            self.__paths_dict.pop(path, None)
            if len(self.__paths_dict) == 0:
                self.__ma_manager.remove_ref_layer()
                self.__params_usd_listener = None
                self.__update_sub = None

    @carb.profiler.profile
    def _on_metrics_assembler_update(self, e: dict) -> None:
        """Handle updates to metrics assembly state.

        Args:
            e: Update event data
        """
        if not self.__stage:
            self.__resync_paths = set()
            return

        self.__listen_to_changes = False

        # process paths
        try:
            for path in self.__resync_paths:
                if len(self.__re_resolved_paths) >= len(self.__paths_dict):
                    break
                prim = self.__stage.GetPrimAtPath(path)
                if prim and prim.IsValid():
                    if prim.IsPrototype():
                        prim_instances = prim.GetInstances()
                        for primi in prim_instances:
                            primi_path = primi.GetPrimPath()
                            if not self._re_resolve_path_check(primi_path):
                                self._remove_path_check(path)
                    else:
                        if not self._re_resolve_path_check(path):
                            self._remove_path_check(path)
                else:
                    # prim got deleted remove the possible write in metadata
                    self._remove_path_check(path)
        except:
            carb.log_info("Failed to process MetricsAssembler changes.")
            pass

        self.__re_resolved_paths = set()
        self.__resync_paths = set()
        self.__listen_to_changes = True

    def _reset(self) -> None:
        """Reset the listener state."""
        self.__params_usd_listener = None
        self.__paths_dict = {}
        self.__resync_paths = set()
        self.__update_sub = None

    def _register_listener(self) -> None:
        """Register for USD change notifications if enabled."""
        if self.__listener_enabled and not self.__params_usd_listener:
            self.__params_usd_listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._on_objects_changed, None)

    def _param_listener_setting_changed(self, item: str, event_type: carb.settings.ChangeEventType) -> None:
        """Handle changes to listener settings.

        Args:
            item: Setting that changed
            event_type: Type of setting change
        """
        if event_type == carb.settings.ChangeEventType.CHANGED:
            self.__listener_enabled = carb.settings.get_settings().get_as_int(
                metricsAssembler.SETTINGS_METRICS_ASSEMBLER_PARAMS_CHANGE_LISTENER_ENABLED
            )
            if not self.__listener_enabled:
                self.__params_usd_listener = None
            else:
                if len(self.__paths_dict) > 0:
                    self._register_listener()

    @carb.profiler.profile
    def _on_objects_changed(self, notice: Usd.Notice.ObjectsChanged, sender: object) -> None:
        """Handle USD object change notifications.

        Args:
            notice: The change notification
            sender: Object that sent the notification
        """
        if self.__listen_to_changes:
            for path in notice.GetResyncedPaths():
                if path.IsPrimPath():
                    self.__resync_paths.add(path)
