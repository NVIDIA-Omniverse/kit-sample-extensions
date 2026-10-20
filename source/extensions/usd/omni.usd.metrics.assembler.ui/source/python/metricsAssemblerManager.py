# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import string

import carb
import carb.profiler
import carb.settings
import omni.kit.commands
import omni.metrics.assembler.core.bindings._metricsAssembler as metricsAssembler
import omni.usd
from omni.metrics.assembler.core import get_metrics_assembler_interface
from pxr import Ar, Sdf, Tf, Usd, UsdUtils

from .metricsAssemblerChangeListener import MetricsAssemblerChangeListener
from .tools import (
    add_anonymous_layer,
    read_and_resolve_metrics_assembler,
    read_resolve_layer,
    remove_anonymous_layer,
    rename_resolve_information,
    resolve_layer_hierarchy,
    store_resolve_information,
)

ROTATE_REFERENCE_SETTING = "/exts/omni.usd/commands/rotateOnCreatingReference"


class MetricsAssemblerMode:
    DISABLED = 0
    WARN = 1
    ASK = 2
    AUTO = 3


class MetricsAssemblerManager:
    """
    Manager class for handling metrics assembly operations in USD.

    This class manages settings, callbacks, and operations related to metrics assembly,
    including handling references, payloads, and unit conversions between USD files.
    """

    def __init__(self):
        """Initialize the MetricsAssemblerManager with default settings and callbacks."""
        self.__settings = carb.settings.get_settings()
        self.__settings_subs = []
        self.__settings_subs.append(
            omni.kit.app.SettingChangeSubscription(
                metricsAssembler.SETTINGS_METRICS_ASSEMBLER_OPERATION_MODE, self._ma_mode_setting_changed
            )
        )

        self.__resolve_path = None
        self.__url_prim_name = None
        self.__notice_listener = None

        self.__block_add_reference_payload = False

        self.__create_post_do_reference_cb = None
        self.__create_post_do_payload_cb = None
        self.__create_pre_do_reference_cb = None
        self.__create_pre_do_payload_cb = None
        self.__add_post_do_reference_cb = None
        self.__add_post_do_payload_cb = None
        self.__add_pre_do_reference_cb = None
        self.__add_pre_do_payload_cb = None

        self.__ma_mode = self.__settings.get_as_int(metricsAssembler.SETTINGS_METRICS_ASSEMBLER_OPERATION_MODE)
        self.__ma_change_listener = MetricsAssemblerChangeListener(self)
        self.__rotate_reference_val = self.__settings.get_as_bool(ROTATE_REFERENCE_SETTING)
        if self.__ma_mode != MetricsAssemblerMode.DISABLED:
            self._register_reference_command_post_event()
            self.__settings.set(ROTATE_REFERENCE_SETTING, False)
        else:
            self._unregister_reference_command_post_event()
            self.__settings.set(ROTATE_REFERENCE_SETTING, self.__rotate_reference_val)

        self.__reference_resolve_layer = None
        self.__pre_do_move_prim_cb = omni.kit.commands.register_callback(
            "MovePrimCommand", omni.kit.commands.PRE_DO_CALLBACK, self.prim_move_callback
        )
        self.__post_do_copy_prim_cb = omni.kit.commands.register_callback(
            "CopyPrimCommand", omni.kit.commands.POST_DO_CALLBACK, self.prim_copy_callback
        )

    def on_shutdown(self):
        """Clean up resources and restore settings when shutting down."""
        self.__settings.set(ROTATE_REFERENCE_SETTING, self.__rotate_reference_val)
        self.__ma_change_listener.on_shutdown()
        self.__ma_change_listener = None
        self._unregister_reference_command_post_event()
        self.__reference_resolve_layer = None

        omni.kit.commands.unregister_callback(self.__pre_do_move_prim_cb)
        self.__pre_do_move_prim_cb = None

        omni.kit.commands.unregister_callback(self.__post_do_copy_prim_cb)
        self.__post_do_copy_prim_cb = None

    @staticmethod
    def __post_notification(message: str, status: str = "info", duration: int = 5):
        """
        Post a notification to the UI.

        Args:
            message (str): The notification message
            status (str): Status level ("info" or "warning")
            duration (int): How long to display the notification in seconds
        """
        try:
            import omni.kit.notification_manager as nm

            if status == "info":
                nm.post_notification(message, status=nm.notification_info.NotificationStatus.INFO, duration=duration)
            elif status == "warning":
                nm.post_notification(message, status=nm.notification_info.NotificationStatus.WARNING, duration=duration)
        except:
            pass

    def on_reset(self):
        """Reset the reference resolve layer."""
        self.__reference_resolve_layer = None

    def remove_ref_layer(self):
        """Remove the reference resolve layer from the stage."""
        stage = omni.usd.get_context().get_stage()
        root_layer = stage.GetRootLayer()
        root_layer.subLayerPaths.remove(self.__reference_resolve_layer.identifier)
        self.__reference_resolve_layer = None

    def get_metrics_assembler_change_listener(self):
        """Get the metrics assembler change listener.

        Returns:
            MetricsAssemblerChangeListener: The change listener instance
        """
        return self.__ma_change_listener

    def _ma_mode_setting_changed(self, item: str, event_type: carb.settings.ChangeEventType):
        """
        Handle changes to the metrics assembler mode setting.

        Args:
            item (str): The setting item that changed
            event_type (carb.settings.ChangeEventType): The type of change event
        """
        if event_type == carb.settings.ChangeEventType.CHANGED:
            self.__ma_mode = self.__settings.get_as_int(metricsAssembler.SETTINGS_METRICS_ASSEMBLER_OPERATION_MODE)
            if self.__ma_mode != MetricsAssemblerMode.DISABLED:
                self._register_reference_command_post_event()
                self.__settings.set(ROTATE_REFERENCE_SETTING, False)
            else:
                self._unregister_reference_command_post_event()
                self.__settings.set(ROTATE_REFERENCE_SETTING, self.__rotate_reference_val)

    def _register_reference_command_post_event(self):
        """Register all reference and payload command callbacks."""
        # create callbacks
        if self.__create_post_do_reference_cb is None:
            self.__create_post_do_reference_cb = omni.kit.commands.register_callback(
                "CreateReferenceCommand", omni.kit.commands.POST_DO_CALLBACK, self.create_post_do_callback
            )
        if self.__create_post_do_payload_cb is None:
            self.__create_post_do_payload_cb = omni.kit.commands.register_callback(
                "CreatePayloadCommand", omni.kit.commands.POST_DO_CALLBACK, self.create_post_do_callback
            )
        if self.__create_pre_do_reference_cb is None:
            self.__create_pre_do_reference_cb = omni.kit.commands.register_callback(
                "CreateReferenceCommand", omni.kit.commands.PRE_DO_CALLBACK, self.create_pre_do_callback
            )
        if self.__create_pre_do_payload_cb is None:
            self.__create_pre_do_payload_cb = omni.kit.commands.register_callback(
                "CreatePayloadCommand", omni.kit.commands.PRE_DO_CALLBACK, self.create_pre_do_callback
            )

        # add callbacks
        if self.__add_post_do_reference_cb is None:
            self.__add_post_do_reference_cb = omni.kit.commands.register_callback(
                "AddReferenceCommand", omni.kit.commands.POST_DO_CALLBACK, self.add_reference_post_do_callback
            )
        if self.__add_post_do_payload_cb is None:
            self.__add_post_do_payload_cb = omni.kit.commands.register_callback(
                "AddPayloadCommand", omni.kit.commands.POST_DO_CALLBACK, self.add_payload_post_do_callback
            )
        if self.__add_pre_do_reference_cb is None:
            self.__add_pre_do_reference_cb = omni.kit.commands.register_callback(
                "AddReferenceCommand", omni.kit.commands.PRE_DO_CALLBACK, self.add_reference_pre_do_callback
            )
        if self.__add_pre_do_payload_cb is None:
            self.__add_pre_do_payload_cb = omni.kit.commands.register_callback(
                "AddPayloadCommand", omni.kit.commands.PRE_DO_CALLBACK, self.add_payload_pre_do_callback
            )

    def _unregister_reference_command_post_event(self):
        """Unregister all reference and payload command callbacks."""
        # create
        if self.__create_post_do_reference_cb:
            omni.kit.commands.unregister_callback(self.__create_post_do_reference_cb)
            self.__create_post_do_reference_cb = None
        if self.__create_post_do_payload_cb:
            omni.kit.commands.unregister_callback(self.__create_post_do_payload_cb)
            self.__create_post_do_payload_cb = None
        if self.__create_pre_do_reference_cb:
            omni.kit.commands.unregister_callback(self.__create_pre_do_reference_cb)
            self.__create_pre_do_reference_cb = None
        if self.__create_pre_do_payload_cb:
            omni.kit.commands.unregister_callback(self.__create_pre_do_payload_cb)
            self.__create_pre_do_payload_cb = None

        # add
        if self.__add_post_do_payload_cb:
            omni.kit.commands.unregister_callback(self.__add_post_do_payload_cb)
            self.__add_post_do_payload_cb = None
        if self.__add_post_do_reference_cb:
            omni.kit.commands.unregister_callback(self.__add_post_do_reference_cb)
            self.__add_post_do_reference_cb = None
        if self.__add_pre_do_payload_cb:
            omni.kit.commands.unregister_callback(self.__add_pre_do_payload_cb)
            self.__add_pre_do_payload_cb = None
        if self.__add_pre_do_reference_cb:
            omni.kit.commands.unregister_callback(self.__add_pre_do_reference_cb)
            self.__add_pre_do_reference_cb = None

    def stage_closed(self):
        """Handle stage closed event."""
        self.__ma_change_listener.on_stage_closed()
        self.on_reset()

    def stage_opened(self, stage: Usd.Stage):
        """
        Handle stage opened event.

        Args:
            stage (Usd.Stage): The USD stage that was opened
        """
        self.__ma_change_listener.on_stage_opened(stage)
        self.on_reset()
        root_layer = stage.GetRootLayer()
        for sub_path in root_layer.subLayerPaths:
            if sub_path.startswith("metrics:UnitsAdjust"):
                self.__reference_resolve_layer = Sdf.Layer.Find(sub_path)
                if self.__reference_resolve_layer:
                    break
        try:
            read_and_resolve_metrics_assembler(stage, self.__ma_change_listener)
        except:
            carb.log_error("Failed to run MetricsAssembler stage open.")
            pass

    def prim_move_callback(self, info: dict):
        """
        Handle prim move events.

        Args:
            info (dict): Information about the move operation
        """
        try:
            stage = omni.usd.get_context().get_stage()
            pre_name = str(info.get("path_from"))
            post_name = str(info.get("path_to"))
            if pre_name and post_name and stage:
                self.__ma_change_listener.prim_rename(Sdf.Path(pre_name), Sdf.Path(post_name))
                rename_resolve_information(stage, pre_name, post_name)
        except:
            carb.log_error("Failed to run MetricsAssembler for move prim command.")
            pass

    def prim_copy_callback(self, info: dict):
        """
        Handle prim copy events.

        Args:
            info (dict): Information about the copy operation
        """
        try:
            stage = omni.usd.get_context().get_stage()
            src_path = str(info.get("path_from"))
            dest_path = str(info.get("path_to"))
            if src_path and dest_path and stage:
                url = self.__ma_change_listener.get_path_url_info(Sdf.Path(src_path))
                if url:
                    if not self.__reference_resolve_layer:
                        self.__reference_resolve_layer = add_anonymous_layer(stage)

                    stage_id = UsdUtils.StageCache.Get().GetId(stage).ToLongInt()
                    write_layer = resolve_layer_hierarchy(
                        stage, stage_id, dest_path, self.__reference_resolve_layer.identifier, False
                    )
                    if write_layer.empty:
                        remove_anonymous_layer(stage, write_layer)
                        write_layer = None
                        self.__reference_resolve_layer = None
                    store_resolve_information(stage, dest_path, write_layer)
                    self.__ma_change_listener.add_path(Sdf.Path(dest_path), url, write_layer)

        except:
            carb.log_error("Failed to run MetricsAssembler for copy prim command.")
            pass

    def create_pre_do_callback(self, info: dict):
        """
        Handle pre-do events for create operations.

        Args:
            info (dict): Information about the create operation
        """
        if self.__ma_mode == MetricsAssemblerMode.DISABLED:
            return

        self.__resolve_path = None
        self.__url_prim_name = str(info.get("path_to"))
        if not self.__notice_listener:
            self.__notice_listener = Tf.Notice.Register(
                Usd.Notice.ObjectsChanged, self._on_objects_changed_metrics_assembler, None
            )

    def set_resolve_layer(self, layer: Sdf.Layer):
        """
        Set the reference resolve layer.

        Args:
            layer (Sdf.Layer): The layer to set as the reference resolve layer
        """
        self.__reference_resolve_layer = layer

    def get_resolve_layer(self):
        """
        Get the current reference resolve layer.

        Returns:
            Sdf.Layer: The reference resolve layer
        """
        return self.__reference_resolve_layer

    @carb.profiler.profile
    def _metrics_assembler_post_do_callback(self, stage: Usd.Stage, path_to: Sdf.Path, url: str):
        """
        Handle post-do operations for metrics assembly.

        Args:
            stage (Usd.Stage): The USD stage
            path_to (Sdf.Path): Target path for the operation
            url (str): Asset URL being processed
        """
        if stage and path_to and url:
            self.__ma_change_listener.set_stage(stage)
            sdf_layer = Sdf.Layer.FindOrOpen(url)
            if sdf_layer:
                read_resolve_layer(stage, sdf_layer, self.__ma_change_listener)

            units_divergent = self.check_units_divergency(stage, url)
            if units_divergent["ret_val"]:
                units0 = units_divergent["units_info0"]
                units1 = units_divergent["units_info1"]

                if not self.__reference_resolve_layer:
                    self.__reference_resolve_layer = add_anonymous_layer(stage)

                # divergent units found, lets kick in the work
                if self.__ma_mode == MetricsAssemblerMode.AUTO:
                    stage_id = UsdUtils.StageCache.Get().GetId(stage).ToLongInt()
                    omni.kit.commands.create("TransformPrimSRTCommand", path=path_to).do()
                    write_layer = resolve_layer_hierarchy(
                        stage, stage_id, path_to, self.__reference_resolve_layer.identifier, False
                    )
                    if write_layer.empty:
                        remove_anonymous_layer(stage, write_layer)
                        write_layer = None
                        self.__reference_resolve_layer = None
                    store_resolve_information(stage, path_to, write_layer)
                    self.__ma_change_listener.add_path(path_to, url, write_layer)
                    MetricsAssemblerManager.__post_notification(
                        message=f"Mismatched units found on drag and drop, resolved in current authoring layer path: {str(path_to)}.",
                        status="info",
                        duration=5,
                    )
                elif self.__ma_mode == MetricsAssemblerMode.WARN:
                    MetricsAssemblerManager.__post_notification(
                        message=f"Mismatched units found in dropped file {str(path_to)}.",
                        status="warning",
                        duration=5,
                    )
                elif self.__ma_mode == MetricsAssemblerMode.ASK:
                    stage_id = UsdUtils.StageCache.Get().GetId(stage).ToLongInt()
                    text = f"Mismatched units found in dropped file {str(path_to)}.\nRootLayerUnits: {str(units0)}\nDraggedLayerUnits: {str(units1)}"
                    try:
                        from .metricsAssemblerDialog import MetricsAssemblerDialog

                        MetricsAssemblerDialog(
                            self, text, stage, stage_id, url, str(path_to), self.__reference_resolve_layer.identifier
                        ).show()
                    except:
                        carb.log_error("Failed to show MetricsAssemblerDialog.")
                        pass

    def create_post_do_callback(self, info: dict):
        """
        Handle post-do events for create operations.

        Args:
            info (dict): Information about the create operation
        """
        if self.__ma_mode == MetricsAssemblerMode.DISABLED:
            return

        self.__notice_listener = None

        try:
            # expecting
            # usd_context (omni.usd.UsdContext): UsdContext this command to run on.
            # path_to (Sdf.Path): Path to create a new prim.
            # asset_path (str): The asset it's necessary to add to payloads.
            usd_context = info.get("usd_context")
            path_to = self.__resolve_path
            url = info.get("asset_path")
            if usd_context:
                self._metrics_assembler_post_do_callback(usd_context.get_stage(), path_to, url)
        except:
            carb.log_error("Failed to run MetricsAssembler.")
            pass

    @carb.profiler.profile
    def metrics_assembler_check_reference_payload(self, stage: Usd.Stage, path_to: Sdf.Path, url: str):
        """
        Check if reference/payload operations can be performed safely.

        Args:
            stage (Usd.Stage): The USD stage
            path_to (Sdf.Path): Target path for the operation
            url (str): Asset URL being processed

        Returns:
            bool: True if operation can proceed, False otherwise
        """
        if self.__ma_mode == MetricsAssemblerMode.DISABLED:
            return True

        sdf_layer = Sdf.Layer.FindOrOpen(url)
        if sdf_layer:
            stage_id = UsdUtils.StageCache.Get().GetId(stage).ToLongInt()
            units_divergent = get_metrics_assembler_interface().check_layers(
                stage.GetRootLayer().identifier, sdf_layer.identifier, stage_id
            )
            if units_divergent["ret_val"]:
                prim = stage.GetPrimAtPath(path_to)
                if not prim:
                    return True

                ref_and_layers = omni.usd.get_composed_payloads_from_prim(prim, False)
                if len(ref_and_layers) == 0:
                    ref_and_layers = omni.usd.get_composed_references_from_prim(prim, False)
                if len(ref_and_layers) > 0:
                    # have already ref/payload check the units
                    for ref, _ in ref_and_layers:
                        asset_path = ref.assetPath
                        if asset_path != url:
                            asset_id = Sdf.ComputeAssetPathRelativeToLayer(stage.GetRootLayer(), asset_path)
                            resolved_path = Ar.GetResolver().Resolve(asset_id)
                            layer = Sdf.Layer.Find(resolved_path)

                            units_divergent = get_metrics_assembler_interface().check_layers(
                                layer.identifier, sdf_layer.identifier, stage_id
                            )
                            if units_divergent["ret_val"]:
                                MetricsAssemblerManager.__post_notification(
                                    message=f"MetricsAssembler aborted work. Mismatched units found in add reference/payload on path {str(path_to)}, but path already contains other references/payloads with different scale, cannot adjust transformation.",
                                    status="warning",
                                    duration=5,
                                )
                                return False
                else:
                    # does not have ref/payload check the childs
                    if len(prim.GetChildren()) > 0:
                        MetricsAssemblerManager.__post_notification(
                            message=f"MetricsAssembler aborted work. Mismatched units found in add reference/payload on path {str(path_to)}, but path already contains children prims, cannot adjust transformation.",
                            status="warning",
                            duration=5,
                        )
                        return False

        return True

    def add_reference_pre_do_callback(self, info: dict):
        """
        Handle pre-do events for add reference operations.

        Args:
            info (dict): Information about the add reference operation
        """
        try:
            stage = info.get("stage")
            path_to = info.get("prim_path")
            reference = info.get("reference")
            if reference:
                url = reference.assetPath
                if not self.metrics_assembler_check_reference_payload(stage, path_to, url):
                    self.__block_add_reference_payload = True
        except Exception as e:
            carb.log_error("Failed to run MetricsAssembler.")
            pass

    def add_payload_pre_do_callback(self, info: dict):
        """
        Handle pre-do events for add payload operations.

        Args:
            info (dict): Information about the add payload operation
        """
        try:
            stage = info.get("stage")
            path_to = info.get("prim_path")
            payload = info.get("payload")
            if payload:
                url = payload.assetPath
                if not self.metrics_assembler_check_reference_payload(stage, path_to, url):
                    self.__block_add_reference_payload = True
        except Exception as e:
            carb.log_error("Failed to run MetricsAssembler.")
            pass

    def add_reference_post_do_callback(self, info: dict):
        """
        Handle post-do events for add reference operations.

        Args:
            info (dict): Information about the add reference operation
        """
        if self.__block_add_reference_payload:
            self.__block_add_reference_payload = False
        else:
            try:
                stage = info.get("stage")
                path_to = info.get("prim_path")
                reference = info.get("reference")
                if reference:
                    url = reference.assetPath
                    self._metrics_assembler_post_do_callback(stage, path_to, url)
            except Exception as e:
                carb.log_error("Failed to run MetricsAssembler.")
                pass

    def add_payload_post_do_callback(self, info: dict):
        """
        Handle post-do events for add payload operations.

        Args:
            info (dict): Information about the add payload operation
        """
        if self.__block_add_reference_payload:
            self.__block_add_reference_payload = False
        else:
            try:
                stage = info.get("stage")
                path_to = info.get("prim_path")
                payload = info.get("payload")
                if payload:
                    url = payload.assetPath
                    self._metrics_assembler_post_do_callback(stage, path_to, url)
            except Exception as e:
                carb.log_error("Failed to run MetricsAssembler.")
                pass

    def check_units_divergency(self, stage: Usd.Stage, url: str):
        """
        Check for unit mismatches between layers.

        Args:
            stage (Usd.Stage): The USD stage
            url (str): Asset URL to check

        Returns:
            dict: Results of the units check
        """
        sdf_layer = Sdf.Layer.Find(url)
        if not sdf_layer:
            carb.log_warn(f"Could not get Sdf layer for {url}")
            return {"ret_val": False}

        if not stage:
            carb.log_warn("Stage not found")
            return {"ret_val": False}

        stage_id = UsdUtils.StageCache.Get().GetId(stage).ToLongInt()
        ret_val = get_metrics_assembler_interface().check_layers(
            stage.GetRootLayer().identifier, sdf_layer.identifier, stage_id
        )
        return ret_val

    @carb.profiler.profile
    def _on_objects_changed_metrics_assembler(self, notice: Usd.Notice.ObjectsChanged, sender: Usd.Stage):
        """
        Handle object change notifications.

        Args:
            notice (Usd.Notice.ObjectsChanged): The change notice
            sender (Usd.Stage): The sender of the notice
        """
        if not self.__url_prim_name:
            return

        if self.__resolve_path:
            return

        cleaned = self.__url_prim_name.rstrip(string.digits)
        for path in notice.GetResyncedPaths():
            if path.IsPrimPath():
                if cleaned in str(path):
                    self.__resolve_path = path
