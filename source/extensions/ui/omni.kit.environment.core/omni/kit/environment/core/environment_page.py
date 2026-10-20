# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
import collections
import os.path as op
import re
from email.policy import default
from functools import partial
from typing import Callable, List, Union

import carb
import carb.settings
import omni.client
from omni import ui
from omni.kit.widget.settings import create_setting_widget, create_setting_widget_combo
from omni.kit.window.preferences import PreferenceBuilder, SettingType

from .constants import EnvironmentSettings
from .style import PREFERENCE_PAGE_STYLES
from .utils import get_subidentifier_from_mdl_async


class SkyType:
    HDRI = "HDRI"
    DYNAMIC = "Sky"
    SCENE = "Scene"


SKY_TYPES = [SkyType.HDRI, SkyType.DYNAMIC, SkyType.SCENE]


class PathWidget:
    def __init__(self, label, field, folder_button, reset_button):
        self._label = label
        self._field = field
        self._folder_button = folder_button
        self._reset_button = reset_button

    @property
    def enabled(self):
        return self._field.enabled

    @enabled.setter
    def enabled(self, value):
        self._label.enabled = value
        self._field.enabled = value
        self._folder_button.enabled = value
        self._reset_button.enabled = value

    @property
    def model(self):
        return self._field.model


class EnvironmentPage(PreferenceBuilder):
    """
    Represent a pereference page to show and edit environment settings.
    """

    def __init__(self):
        super().__init__("Environment")
        self._settings = carb.settings.get_settings()
        self._models = []
        self._widgets = []

        saved_settings = [
            EnvironmentSettings.ENV_AUTO,
            EnvironmentSettings.ENV_DEFAULT,
            EnvironmentSettings.GROUND_ENABLE,
            EnvironmentSettings.GROUND_MATERIAL,
            EnvironmentSettings.GROUND_SUB_MATERIAL,
        ]

        # save default setting, make reset button work
        for setting in saved_settings:
            value = self._settings.get(setting)
            if value is None:
                if setting.startswith("/persistent"):
                    default_setting = setting[len("/persistent") :]
                    value = self._settings.get(default_setting)
                    self._settings.set(setting, value)

            self._settings.set(self._get_default_setting_path(setting), value)

    def destroy(self):
        self._sub_ground_material_asset = None
        self._sub_ground_enabled = None
        self._sub_env_auto = None

    def _create_setting_widget_with_reset(
        self, label_name: str, setting_path: str, setting_type: SettingType, **kwargs
    ):
        clicked_fn = None
        if "clicked_fn" in kwargs:
            clicked_fn = kwargs["clicked_fn"]
            del kwargs["clicked_fn"]

        vheight = 24
        vpadding = 0
        if setting_type == SettingType.FLOAT or setting_type == SettingType.INT or setting_type == SettingType.STRING:
            vheight = 20
            vpadding = 3
        with ui.HStack(height=vheight):
            label = ui.Label(label_name, style_type_name_override="Setting.Label", word_wrap=True, width=ui.Percent(50))
            widget, model = create_setting_widget(setting_path, setting_type, **kwargs)
            if clicked_fn:
                folder_button = ui.Button(
                    style_type_name_override="Setting.Button",
                    clicked_fn=partial(clicked_fn, widget),
                    width=24,
                    image_width=24,
                )
            button = self._build_reset_button(setting_path)
        if widget:
            try:
                model = widget.model
                model.set_reset_button(button)

                self._widgets.append(widget)
                self._models.append(model)
            except:
                pass
        if clicked_fn:
            return PathWidget(label, widget, folder_button, button)
        else:
            return widget

    def _create_combo_widget_with_reset(
        self, label_name: str, setting_path: str, items: Union[list, dict], has_reset: bool = False
    ):
        with ui.HStack(height=0):
            label = ui.Label(label_name, style_type_name_override="Setting.Label", word_wrap=True, width=ui.Percent(50))
            widget, model = create_setting_widget_combo(setting_path, items, setting_is_index=False)
            if has_reset:
                button = self._build_reset_button(setting_path)
        if widget:
            try:
                model = widget.model
                if has_reset:
                    model.set_reset_button(button)

                self._widgets.append(widget)
                self._models.append(model)
            except:
                pass
        return widget

    def _build_reset_button(self, path) -> ui.Rectangle:
        with ui.VStack(width=15, height=20):
            ui.Spacer(height=5)
            with ui.ZStack(width=15, height=15):
                with ui.HStack(spacing=0):
                    ui.Spacer()
                    with ui.VStack(width=0):
                        ui.Spacer()
                        ui.Rectangle(width=5, height=5, style_type_name_override="Reset_invalid.Rect")
                        ui.Spacer()
                    ui.Spacer()
                btn = ui.Rectangle(
                    width=12, height=12, style_type_name_override="Reset.Rect", tooltip="Click to reset value"
                )
                btn.visible = False

            btn.set_mouse_pressed_fn(lambda x, y, m, w, p=path, b=btn: self._restore_defaults(path, b))
            ui.Spacer()
        return btn

    def _restore_defaults(self, path: str, button: ui.Widget = None) -> None:
        default_path = self._get_default_setting_path(path)
        default_value = self._settings.get(default_path)
        self._settings.set(path, default_value)
        if button:
            button.visible = False

    def build(self):
        with ui.VStack(height=0):
            with self.add_frame("Auto Environment"):
                with ui.VStack(spacing=2, height=200, style=PREFERENCE_PAGE_STYLES):
                    self._build_sky_settings()

                    ui.Spacer(height=4)
                    with ui.HStack(height=0):
                        ui.Spacer(width=10)
                        ui.Line(style_type_name_override="Seperator", width=ui.Fraction(0.8))
                        ui.Spacer(width=10)
                    ui.Spacer(height=4)

                    self._build_ground_setting()

    def _build_sky_settings(self):
        # Auto Sky
        self._env_auto_model = self._create_setting_widget_with_reset(
            "Enable Auto add on scene open", EnvironmentSettings.ENV_AUTO, SettingType.BOOL
        ).model

        self._default_env_widget = self._create_setting_widget_with_reset(
            "Default Env",
            EnvironmentSettings.ENV_DEFAULT,
            SettingType.STRING,
            clicked_fn=self._on_default_env_button_fn,
            style_type_name_override="Setting.Field",
        )

        # Models
        self._sub_env_auto = self._env_auto_model.subscribe_value_changed_fn(self._on_env_auto_changed)
        self._on_env_auto_changed(self._env_auto_model)

    def _build_ground_setting(self):
        self._ground_enable_model = self._create_setting_widget_with_reset(
            "Include Ground", EnvironmentSettings.GROUND_ENABLE, SettingType.BOOL
        ).model
        self._ground_widget = self._create_setting_widget_with_reset(
            "Default Ground Material",
            EnvironmentSettings.GROUND_MATERIAL,
            SettingType.STRING,
            clicked_fn=self._on_ground_button_fn,
            style_type_name_override="Setting.Field",
        )
        self._ground_material_asset_model: ui.AbstractValueModel = self._ground_widget.model
        self._sub_ground_material_asset = self._ground_material_asset_model.subscribe_value_changed_fn(
            self._on_ground_material_asset_changed
        )
        self._ground_material_sub_id_container = ui.HStack()
        with self._ground_material_sub_id_container:
            self._ground_material_sub_id_widget = self._create_combo_widget_with_reset(
                "Material Sub Identifier", EnvironmentSettings.GROUND_SUB_MATERIAL, []
            )
        self._ground_material_sub_id_model = self._ground_material_sub_id_widget.model

        self._sub_ground_enabled = self._ground_enable_model.subscribe_value_changed_fn(self._on_ground_enable_changed)
        self._on_ground_material_asset_changed(self._ground_material_asset_model)
        self._on_ground_enable_changed(self._ground_enable_model)

    def _on_default_env_button_fn(self, owner):
        """Called when the user picks the Browse button."""
        path = self._default_env_widget.model.get_value_as_string()
        if path:
            path = op.dirname(path)
        self._show_filepicker(
            "Select Env", path, click_apply_fn=partial(self._on_pick_folder, self._default_env_widget)
        )

    def _on_ground_button_fn(self, owner):
        """Called when the user picks the Browse button."""
        path = self._ground_widget.model.get_value_as_string()
        self._show_filepicker(
            "Select ground material",
            click_apply_fn=partial(self._on_pick_folder, self._ground_widget),
            path=op.dirname(path),
        )

    def _on_pick_folder(self, widget, path: str) -> None:
        widget.model.set_value(path)

    def _get_default_setting_path(self, path: str) -> str:
        return path.replace("/rtx/", "/rtx-defaults/")

    def _on_env_auto_changed(self, model: ui.AbstractValueModel) -> None:
        env_auto = model.as_bool
        self._default_env_widget.enabled = env_auto

    def _on_ground_enable_changed(self, model: ui.AbstractValueModel) -> None:
        self._ground_widget.enabled = model.as_bool
        self._ground_material_sub_id_container.enabled = model.as_bool

    def _on_ground_material_asset_changed(self, model: ui.AbstractValueModel) -> None:
        async def __update_ground_material_settings():
            material_asset = model.as_string
            if material_asset and material_asset.lower().endswith(".mdl"):
                self._ground_material_sub_id_container.enabled = False
                material_sub_ids = await get_subidentifier_from_mdl_async(material_asset)
                self._ground_material_sub_id_container.enabled = self._ground_enable_model.as_bool
                if material_sub_ids and len(material_sub_ids) > 1:
                    self._ground_material_sub_id_container.visible = True
                    name_to_value = collections.OrderedDict(zip(material_sub_ids, range(0, len(material_sub_ids))))
                    self._ground_material_sub_id_model.set_items(name_to_value)
                    default_sub_id = self._settings.get(EnvironmentSettings.GROUND_SUB_MATERIAL)
                    if default_sub_id and default_sub_id in material_sub_ids:
                        self._settings.set(EnvironmentSettings.GROUND_SUB_MATERIAL, default_sub_id)
                    else:
                        self._settings.set(EnvironmentSettings.GROUND_SUB_MATERIAL, material_sub_ids[0])
                    return
            self._ground_material_sub_id_container.visible = False

        asyncio.ensure_future(__update_ground_material_settings())

    @staticmethod
    def _show_filepicker(title: str, path: str, click_apply_fn: Callable = None):
        try:
            from omni.kit.window.preferences import show_file_importer

            show_file_importer(title, click_apply_fn=click_apply_fn, filename_url=path)

        # fallback to api in Kit 104.x
        except ImportError:
            from omni.kit.window.preferences import create_filepicker

            file_picker = create_filepicker(title=title, click_apply_fn=click_apply_fn)
            file_picker.show(path)
