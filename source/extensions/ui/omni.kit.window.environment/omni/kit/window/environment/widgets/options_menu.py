# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Callable, Optional

import carb
import omni.client
import omni.kit.window.preferences as preferences
import omni.usd
from omni.kit.browser.core import OptionMenuDescription
from omni.kit.browser.folder.core import FolderOptionsMenu
from omni.kit.environment.core import (
    ENVIRONMENT_MATERIALS_ROOT,
    ENVIRONMENT_PRIM_ROOT,
    EnvironmentProperties,
    EnvironmentSettings,
    GroundHelper,
    SceneTemplateHelper,
    SettingModel,
)
from omni.kit.notification_manager import NotificationButtonInfo, NotificationStatus, post_notification


class EnvironmentOptionsMenu(FolderOptionsMenu):
    """
    Represent options menu used in environment browser.
    """

    def __init__(self, on_new_scene_template_saved: Callable[[str], None]):
        super().__init__(None)

        self._on_new_scene_template_saved = on_new_scene_template_saved
        self._usd_context = omni.usd.get_context()
        self._auto_add_desc = OptionMenuDescription("Auto Add to Scenes", clicked_fn=self._on_auto_add_to_scene)
        self._show_light_warning_desc = OptionMenuDescription(
            "Show warning on extra lights", clicked_fn=self._on_show_light_warning
        )

        self.append_menu_item(OptionMenuDescription("", None))
        self.append_menu_item(
            OptionMenuDescription("Set to Stage", clicked_fn=self._on_set_to_stage, enabled_fn=self._has_item_selected)
        )
        self.append_menu_item(self._auto_add_desc)
        self.append_menu_item(self._show_light_warning_desc)
        self.append_menu_item(
            OptionMenuDescription(
                "Remove Env from Stage", clicked_fn=self._remove_env_from_stage, enabled_fn=self._has_enviroment_prim
            )
        )
        self.append_menu_item(OptionMenuDescription("", None))
        self.append_menu_item(
            OptionMenuDescription(
                "Save Scene Template", clicked_fn=self._on_save_scene_template, enabled_fn=self._can_save_scene_template
            )
        )
        self.append_menu_item(
            OptionMenuDescription(
                "Save as New Scene Template",
                clicked_fn=self._on_save_as_new_scene_template,
                enabled_fn=self._has_enviroment_prim,
            )
        )
        self.append_menu_item(OptionMenuDescription("", None))
        self.append_menu_item(
            OptionMenuDescription("Environment Preferences", clicked_fn=self._show_environment_pereference)
        )

        self._auto_add_setting_model = SettingModel(EnvironmentSettings.ENV_AUTO)
        self._show_light_warning_model = SettingModel(EnvironmentSettings.SHOW_LIGHT_WARNING)

        self._scene_template_helper = SceneTemplateHelper()

    def show(self) -> None:
        super().show()
        self._menu_items[self._auto_add_desc].checkable = True
        self._menu_items[self._auto_add_desc].checked = self._auto_add_setting_model.as_bool

        self._menu_items[self._show_light_warning_desc].checkable = True
        self._menu_items[self._show_light_warning_desc].checked = self._show_light_warning_model.as_bool

    def _on_set_to_stage(self) -> None:
        selections = self._browser_widget.detail_selection
        if len(selections):
            selected = selections[0]
            self._browser_widget.model.execute(selected)

    def _on_auto_add_to_scene(self) -> None:
        self._auto_add_setting_model.set_value(not self._auto_add_setting_model.as_bool)

    def _on_show_light_warning(self) -> None:
        self._show_light_warning_model.set_value(not self._show_light_warning_model.as_bool)

    def _remove_env_from_stage(self) -> None:
        env_prim = self._usd_context.get_stage().GetPrimAtPath(ENVIRONMENT_PRIM_ROOT)
        if env_prim:
            omni.kit.commands.execute("DeletePrimsCommand", paths=[ENVIRONMENT_PRIM_ROOT])

    def _verify_env_prim(self, on_verified_fn: Callable = None) -> bool:
        ground_material = GroundHelper().ground_material
        if ground_material and not ground_material.startswith(ENVIRONMENT_MATERIALS_ROOT):
            button_infos = [
                NotificationButtonInfo(
                    "Copy", on_complete=lambda m=ground_material, f=on_verified_fn: self._update_ground_material(m, f)
                ),
                NotificationButtonInfo("Cancel", on_complete=None),
            ]
            post_notification(
                f"Copy ground material from '{ground_material}' to {ENVIRONMENT_MATERIALS_ROOT}?",
                hide_after_timeout=False,
                status=NotificationStatus.INFO,
                button_infos=button_infos,
            )
        else:
            if on_verified_fn:
                on_verified_fn()

    def _update_ground_material(self, material_path: str, on_verified_fn: Callable = None) -> None:
        GroundHelper().update_ground_material(material_path)
        if on_verified_fn:
            on_verified_fn()

    def _on_save_scene_template(self) -> None:
        self._verify_env_prim(self._save_scene_template)

    def _save_scene_template(self) -> None:
        url = self._scene_template_helper.get_scene_template_url()
        result, list_entry = omni.client.stat(url)
        if result == omni.client.Result.OK:
            if not list_entry.access & omni.client.AccessFlags.WRITE:
                button_infos = [
                    NotificationButtonInfo("Save as ...", on_complete=self._save_as_new_scene_template),
                    NotificationButtonInfo("Cancel", on_complete=None),
                ]
                post_notification(
                    f"Scene template '{url}' is readonly, please save to another one!",
                    hide_after_timeout=False,
                    status=NotificationStatus.WARNING,
                    button_infos=button_infos,
                )
            else:

                def __on_save_done():
                    post_notification(
                        f"Saved to scene template '{url}'!", hide_after_timeout=True, status=NotificationStatus.INFO
                    )

                if not self._scene_template_helper.save(on_save_done=__on_save_done):
                    post_notification(
                        f"Failed when saving to scene template '{url}'!",
                        hide_after_timeout=True,
                        status=NotificationStatus.INFO,
                    )

    def _on_save_as_new_scene_template(self) -> None:
        self._verify_env_prim(self._save_as_new_scene_template)

    def _save_as_new_scene_template(self) -> None:
        def __save_as_done(url: str):
            post_notification(
                f"Saved to scene template '{url}'!", hide_after_timeout=True, status=NotificationStatus.INFO
            )
            if self._on_new_scene_template_saved:
                self._on_new_scene_template_saved(url)

        self._scene_template_helper.save_as(on_save_done=__save_as_done)

    def _show_environment_pereference(self) -> None:
        ENVIRONMENT_PAGE_TITLE = "Environment"
        inst = preferences.get_instance()
        if not inst:
            carb.log_error("Preferences extension is not loaded yet")
            return False

        pages = preferences.get_page_list()
        for page in pages:
            if page.get_title() == ENVIRONMENT_PAGE_TITLE:
                inst.select_page(page)
                if not inst._window_is_visible:
                    inst._toggle_preferences_window()
                return page
        else:
            carb.log_error(f"Environment Preferences page not found!")

    def _has_enviroment_prim(self) -> bool:
        return omni.usd.get_context().get_stage().GetPrimAtPath(ENVIRONMENT_PRIM_ROOT)

    def _get_scene_template(self) -> Optional[str]:
        prop_scene_template = self._usd_context.get_stage().GetPropertyAtPath(EnvironmentProperties.SCENE_TEMPLATE)
        if prop_scene_template:
            url = prop_scene_template.Get()
            if url:
                result, list_entry = omni.client.stat(url)
                if result == omni.client.Result.OK:
                    return url
        return None

    def _can_save_scene_template(self) -> bool:
        return self._has_enviroment_prim() and self._get_scene_template() is not None

    def _has_item_selected(self) -> bool:
        return len(self._browser_widget.detail_selection) > 0
