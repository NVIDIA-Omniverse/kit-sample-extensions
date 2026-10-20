# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import carb
import omni.kit.actions.core

from . import ui_const as ui_c
from .window import VariantEditorWindow


class HotkeyBuilder:

    def __init__(self, ext_id: str, var_window: VariantEditorWindow):
        self._ext_id = ext_id
        self._build_actions(ext_id, var_window)
        self._build_hotkeys(ext_id)

    def on_shutdown(self):
        self._clear_hotkeys(self._ext_id)
        self._clear_actions(self._ext_id)
        self._ext_id = None

    def _build_actions(self, ext_id: str, var_window: VariantEditorWindow):
        self._action_registry = omni.kit.actions.core.get_action_registry()
        # Duplicate the Variant action
        self._action_registry.register_action(
            ext_id,
            "duplicate_variant",
            var_window.duplicate_variant_action,
            "Duplicate Variant",
            "Duplicate the currently displayed active variant",
        )
        self._action_registry.register_action(
            ext_id,
            "rename_variant",
            var_window.rename_variant_action,
            "Rename Variant",
            "Rename the currently displayed active variant",
        )

    def _build_hotkeys(self, ext_id: str):
        try:
            import omni.kit.hotkeys.core
        except ImportError:
            carb.log_warn("Failed to register hotkeys.")
            return

        self._hotkey_registry = omni.kit.hotkeys.core.get_hotkey_registry()
        self._hotkey_filter_by_window = omni.kit.hotkeys.core.filter.HotkeyFilter(windows=[ui_c.PATH_NAME_TOOL])

        # Duplicate Variant, Ctrl+D
        self._hotkey_registry.register_hotkey(
            ext_id,
            "CTRL + D",
            ext_id,
            "duplicate_variant",
            self._hotkey_filter_by_window,
        )
        self._hotkey_registry.register_hotkey(ext_id, "F2", ext_id, "rename_variant", self._hotkey_filter_by_window)

    def _clear_hotkeys(self, ext_id: str):
        if self._hotkey_registry:
            self._hotkey_registry.deregister_all_hotkeys_for_extension(ext_id)
        self._hotkey_registry = None
        self._hotkey_filter_by_window = None

    def _clear_actions(self, ext_id: str):
        if self._action_registry:
            self._action_registry.deregister_all_actions_for_extension(ext_id)
