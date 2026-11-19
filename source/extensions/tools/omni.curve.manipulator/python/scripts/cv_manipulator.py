# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import carb.events
import omni.usd
from omni.kit.manipulator.tool.snap import SnapProviderManager
from omni.kit.manipulator.tool.snap import settings_constants as snap_c
from omni.kit.manipulator.transform.manipulator import TransformManipulator
from omni.kit.manipulator.transform.settings_constants import Constants
from omni.kit.manipulator.transform.settings_listener import OpSettingsListener, SnapSettingsListener
from omni.kit.manipulator.transform.style import get_default_style
from omni.kit.manipulator.viewport import ManipulatorFactory
from pxr import Tf, Usd

from ..bindings import CurveManipulatorContext, CurvesEventType, get_interface
from .cv_selection import CvSelection
from .model import CvRotateChangedGesture, CvScaleChangedGesture, CvTransformModel, CvTranslateChangedGesture
from .toolbar_registry import get_toolbar_registry


class CvManipulator:
    def __init__(
        self,
        cv_selection: CvSelection,
        curve_context: CurveManipulatorContext,
        usd_context_name: str = "",
        viewport_api=None,
    ):
        self._curve_manip = get_interface()
        self._legacy_mode = viewport_api is None
        self._cv_selection = cv_selection
        self._curve_context = curve_context
        self._cv_model = CvTransformModel(cv_selection, usd_context_name)  # TODO make model an arg
        self._usd_context = omni.usd.get_context(usd_context_name)
        self._snap_manager = SnapProviderManager(viewport_api=viewport_api)

        if self._legacy_mode:
            self._cv_manipulator = ManipulatorFactory.create_manipulator(
                TransformManipulator,
                model=self._cv_model,
                enabled=False,
                gestures=[
                    CvTranslateChangedGesture(
                        self._snap_manager, usd_context_name=usd_context_name, viewport_api=viewport_api
                    ),
                    CvRotateChangedGesture(usd_context_name=usd_context_name, viewport_api=viewport_api),
                    CvScaleChangedGesture(usd_context_name=usd_context_name, viewport_api=viewport_api),
                ],
                tool_registry=get_toolbar_registry(),
            )
        else:
            self._cv_manipulator = TransformManipulator(
                model=self._cv_model,
                enabled=False,
                gestures=[
                    CvTranslateChangedGesture(
                        self._snap_manager, usd_context_name=usd_context_name, viewport_api=viewport_api
                    ),
                    CvRotateChangedGesture(usd_context_name=usd_context_name, viewport_api=viewport_api),
                    CvScaleChangedGesture(usd_context_name=usd_context_name, viewport_api=viewport_api),
                ],
                tool_registry=get_toolbar_registry(),
                tool_button_additional_payload={"viewport_api": viewport_api},
            )

        self._stage_listener = None

        self._curve_event_sub = self._curve_manip.get_curves_event_stream(
            self._curve_context
        ).create_subscription_to_pop(self.on_curves_event, name="omni.curve.manipulator.CvManipulator")
        self._cv_selection_sub = self._cv_selection.subscribe_to_selection_changed(self._on_cv_selection_changed)

        self._default_style = get_default_style()
        self._snap_style = get_default_style()
        self._snap_style["Translate.Focal"]["visible"] = True

        self._snap_settings_listener = SnapSettingsListener(
            enabled_setting_path=None,
            move_x_setting_path=snap_c.SNAP_TRANSLATE_SETTING_PATH,
            move_y_setting_path=snap_c.SNAP_TRANSLATE_SETTING_PATH,
            move_z_setting_path=snap_c.SNAP_TRANSLATE_SETTING_PATH,
            rotate_setting_path=snap_c.SNAP_ROTATE_SETTING_PATH,
            scale_setting_path=snap_c.SNAP_SCALE_SETTING_PATH,
            provider_setting_path=snap_c.SNAP_PROVIDER_NAME_SETTING_PATH,
        )
        self._snap_settings_listener_sub = self._snap_settings_listener.subscribe_listener(
            self._on_snap_listener_changed
        )

        self._set_style()

        self._op_settings_listener = OpSettingsListener()
        self._op_settings_listener_sub = self._op_settings_listener.subscribe_listener(self._on_op_listener_changed)

    def destroy(self):
        self._curve_event_sub = None

        if self._cv_manipulator:
            if self._legacy_mode:
                ManipulatorFactory.destroy_manipulator(self._cv_manipulator)
            else:
                self._cv_manipulator.enabled = False
                self._cv_manipulator.destroy()

        self._cv_manipulator = None

        if self._cv_model:
            self._cv_model.destroy()
            self._cv_model = None

        if self._snap_settings_listener:
            self._snap_settings_listener.destroy()
            self._snap_settings_listener = None

        if self._op_settings_listener:
            self._op_settings_listener.destroy()
            self._op_settings_listener = None

        if self._stage_listener:
            self._stage_listener.Revoke()
            self._stage_listener = None

        if self._snap_manager:
            self._snap_manager.destroy()
            self._snap_manager = None

    def __del__(self):
        self.destroy()

    def on_curves_event(self, event: carb.events.IEvent):
        if event.type == int(CurvesEventType.BEGIN_CURVE_EDIT):
            if self._stage_listener is None:
                self._stage_listener = Tf.Notice.Register(
                    Usd.Notice.ObjectsChanged, self._on_objects_changed, self._usd_context.get_stage()
                )
        elif event.type == int(CurvesEventType.END_CURVE_EDIT):
            self._cv_manipulator.enabled = False
            self._cv_model.reset()
            if self._stage_listener:
                self._stage_listener.Revoke()
                self._stage_listener = None

    def _on_objects_changed(self, notice, sender):
        self._cv_model.on_objects_changed(notice, sender)

    def _on_cv_selection_changed(self, selected_cvs):
        if self._cv_manipulator:
            self._cv_manipulator.enabled = self._should_enable_manipulator()

    def _set_style(self):
        style = (
            self._snap_style
            if self._snap_settings_listener.snap_enabled and self._snap_settings_listener.snap_provider
            else self._default_style
        )
        self._cv_manipulator.style = style

    def _on_snap_listener_changed(self, setting_val_name: str, value: str):
        if (
            setting_val_name == "snap_enabled"
            or setting_val_name == "snap_to_surface"
            or setting_val_name == "snap_provider"
        ):
            self._set_style()

    def _on_op_listener_changed(self, type: OpSettingsListener.CallbackType, value: str):
        if type == OpSettingsListener.CallbackType.OP_CHANGED:
            self._cv_manipulator.enabled = self._should_enable_manipulator()

    def _should_enable_manipulator(self) -> bool:
        return (
            self._op_settings_listener.selected_op != Constants.TRANSFORM_OP_SELECT
            and self._curve_manip.is_in_curve_editing_mode(self._curve_context)
            and len(self._cv_selection.get_selected_cvs()) > 0
        )
