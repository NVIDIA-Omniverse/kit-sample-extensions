import gc

import omni.ext
from carb.input import KEYBOARD_MODIFIER_FLAG_ALT as ALT
from carb.input import KeyboardInput as InputKey

from ..bindings._animcurve import *
from . import commands, primCmdCallback, utils
from .commands import is_authoring
from .hotkey import anim_hotkey_callback
from .keySelection import *

_extension_instance = None


class _PublicExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        global _extension_instance
        _extension_instance = self
        utils.curve_plugin = acquire_interface()

        self.ext_id = ext_id
        self._reg_actions = False
        self._reg_hotkeys = False

        ext_manager = omni.kit.app.get_app().get_extension_manager()
        # Please note that, upon subscription (when the next line is executed), if the ext is on, on_enable_fn func will be called immediately.
        # However, if it's off, on_disable_fn func will NOT be called immediately.
        # So you don't have to exam the extension state explicitly for the CURRENT time. Instead, you can assume it's off.
        # should save the handle in that case
        self._action_sub = ext_manager.subscribe_to_extension_enable(
            lambda _: self.build_actions(),
            lambda _: self.clear_actions(),
            ext_name="omni.kit.actions.core",
            hook_name="omni.anim.curve.core-actions",
        )
        self._hotkeys_sub = ext_manager.subscribe_to_extension_enable(
            lambda _: self.build_hotkeys(),
            lambda _: self.clear_hotkeys(),
            ext_name="omni.kit.hotkeys.core",
            hook_name="omni.anim.curve.core-hotkeys",
        )

        KeySelectionState._startup()
        self._reg_cmds = omni.kit.commands.register_all_commands_in_module(commands)
        self._prim_dup_handler = primCmdCallback.PrimCmdCallback()

    def on_shutdown(self):
        global _extension_instance
        _extension_instance = None
        self._prim_dup_handler = None
        KeySelectionState._shutdown()
        release_interface(utils.curve_plugin)
        utils.curve_plugin = None
        self._hotkey = None
        omni.kit.commands.unregister_module_commands(self._reg_cmds)
        self._reg_cmds = None
        utils.shutdown_curvekey_clipboard()

        self.clear_hotkeys()
        self.clear_actions()
        self._action_sub = None
        self._hotkeys_sub = None

        gc.collect()

    def build_hotkeys(self):
        hotkey_registry = omni.kit.hotkeys.core.get_hotkey_registry()
        hotkey_registry.register_hotkey(self.ext_id, "ALT + S", self.ext_id, "add_key", None)
        self._reg_hotkeys = True

    def clear_hotkeys(self):
        if self._reg_hotkeys:
            hotkey_registry = omni.kit.hotkeys.core.get_hotkey_registry()
            hotkey_registry.deregister_all_hotkeys_for_extension(self.ext_id)
            self._reg_hotkeys = False

    def build_actions(self):
        action_registry = omni.kit.actions.core.get_action_registry()
        action_registry.register_action(self.ext_id, "add_key", anim_hotkey_callback, "Add Key", "Add Key")
        self._reg_actions = True

    def clear_actions(self):
        if self._reg_actions:
            action_registry = omni.kit.actions.core.get_action_registry()
            action_registry.deregister_all_actions_for_extension(self.ext_id)
            self._reg_actions = False


def get_instance():
    global _extension_instance
    return _extension_instance
