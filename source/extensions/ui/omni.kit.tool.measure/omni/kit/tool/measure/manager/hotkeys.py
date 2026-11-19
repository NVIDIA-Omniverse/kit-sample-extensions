from typing import Callable, Optional

import carb.settings

from ..common.settings import SETTINGS_MEASURE_ENABLE_HOTKEYS


class Hotkey:
    def __init__(
        self,
        name: str,
        callback: Callable[[], None],
        key: Optional[str],  # if None, settings will be fetched
        filter_context: Optional[str] = None,
    ) -> None:
        self._name = name
        self._key = key
        self._callback = callback
        self._filter_context = filter_context
        self._action = None
        self._kit_hotkey = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def key(self) -> str:
        return self._key

    @property
    def callback(self) -> Callable[[], None]:
        return self._callback

    @property
    def filter_context(self) -> str:
        return self._filter_context

    def register(self, extension_name: str, action_name: str, action_reg, hotkey_reg, display_name: str = ""):
        try:
            from omni.kit.hotkeys.core import HotkeyFilter
        except:  # pragma: no cover
            return
        if self._action is not None or self._kit_hotkey is not None:  # pragma: no cover
            carb.log_warn(f"Hotkey {self._name} is already registered")
            return
        if self.key is None:
            return
        self._action = action_reg.register_action(extension_name, action_name, self._callback, display_name)
        filter = None
        if self._filter_context is not None:
            filter = HotkeyFilter(context=self._filter_context)
        self._kit_hotkey = hotkey_reg.register_hotkey(
            extension_name, self.key, extension_name, action_name, filter=filter
        )

    def deregister(self, action_reg, hotkey_reg):
        if self._kit_hotkey:
            hotkey_reg.deregister_hotkey(self._kit_hotkey)
            self._kit_hotkey = None
        if self._action:
            action_reg.deregister_action(self._action)
            self._action = None


class HotkeyManager:
    def __singleton_init__(self):
        self._settings = carb.settings.get_settings()
        self._extension_name = "omni.kit.tool.measure"
        self._enable_hotkeys_sub = self._settings.subscribe_to_node_change_events(
            SETTINGS_MEASURE_ENABLE_HOTKEYS,
            self._update_hotkeys,
        )

        self._hotkey_reg = None
        self._hotkey_context = None
        self._action_reg = None
        self._hotkeys = {}
        self._hotkeys_enabled = self._settings.get_as_bool(SETTINGS_MEASURE_ENABLE_HOTKEYS) or False

        self._load_registry()

    # singleton model, set once - use everywhere
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls, *args, **kwargs)
            cls._instance.__singleton_init__()
        return cls._instance

    @property
    def extension_name(self) -> str:
        return self._extension_name

    @extension_name.setter
    def extension_name(self, value: str):
        self._extension_name = value

    @property
    def hotkey_context(self):
        return self._hotkey_context

    def add_hotkey(self, hotkey: Hotkey):
        if hotkey.name in self._hotkeys:  # pragma: no cover
            carb.log_warn(f"Hotkey {hotkey.name} is already defined")
            return
        self._hotkeys[hotkey.name] = hotkey
        self.register_hotkey(hotkey)

    def register_hotkey(self, hotkey: Hotkey):
        enabled = self._settings.get_as_bool(SETTINGS_MEASURE_ENABLE_HOTKEYS) or False
        if enabled and self._load_registry():
            self._register_hotkey(hotkey)

    def deregister_hotkey(self, hotkey: Hotkey):
        if self._load_registry():
            hotkey.deregister(self._action_reg, self._hotkey_reg)

    def deregister_all_hotkeys(self):  # pragma: no cover
        if self._load_registry():
            for hotkey in self._hotkeys.values():
                self._deregister_hotkey(hotkey)

    def get_key(self, setting_path: str, default: Optional[str]) -> Optional[str]:
        key = self._settings.get_as_string(setting_path)
        if key is None or key == "":
            return default
        return key

    def remove_hotkey_context(self, context: str):
        if self._load_registry():
            all_contexts = []
            while (top_context := self._hotkey_context.get()) is not None:
                all_contexts.append(top_context)
                self._hotkey_context.pop()
            for c in reversed(all_contexts):
                if c != context:
                    self._hotkey_context.push(c)

    def _register_hotkey(self, hotkey: Hotkey):
        action_name = self._extension_name + "-" + hotkey.name
        display_name = "measure::" + hotkey.name
        hotkey.register(self._extension_name, action_name, self._action_reg, self._hotkey_reg, display_name)

    def _deregister_hotkey(self, hotkey: Hotkey):
        hotkey.deregister(self._action_reg, self._hotkey_reg)

    def _load_registry(self) -> bool:
        if self._hotkey_reg is None or self._action_reg is None:
            try:
                import omni.kit.actions.core
                import omni.kit.hotkeys.core

                self._hotkey_reg = omni.kit.hotkeys.core.get_hotkey_registry()
                self._action_reg = omni.kit.actions.core.get_action_registry()
                self._hotkey_context = omni.kit.hotkeys.core.get_hotkey_context()
            except:  # pragma: no cover
                carb.log_warn("Failed to import hotkey extensions, measyre hotkeys are disabled.")
                return False
        return True

    def _update_hotkeys(self, item, event):
        if self._load_registry():
            enabled = self._settings.get_as_bool(SETTINGS_MEASURE_ENABLE_HOTKEYS) or False
            if enabled != self._hotkeys_enabled:
                self._hotkeys_enabled = enabled
                for hotkey in self._hotkeys.values():
                    if enabled:
                        self._register_hotkey(hotkey)
                    else:
                        self._deregister_hotkey(hotkey)

    @classmethod
    def deinit(cls):
        if hasattr(cls, "_instance"):
            cls._instance.destroy()
            del cls._instance

    def __del__(self):
        self.destroy()

    def destroy(self):
        if self._enable_hotkeys_sub:
            self._settings.unsubscribe_to_change_events(self._enable_hotkeys_sub)
            self._enable_hotkeys_sub = None
        self._settings = None
        self.deregister_all_hotkeys()
        self._hotkey_reg = None
        self._hotkey_context = None
        self._action_reg = None
        self._hotkeys = {}
