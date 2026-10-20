from functools import partial

import carb.settings
import omni.kit.app
from omni import ui
from omni.kit.window.preferences import PERSISTENT_SETTINGS_PREFIX, PreferenceBuilder, SettingType

USDSKEL_SETTINGS_TITLE = "UsdSkel Settings"

_g_settings = carb.settings.get_settings()


def on_enable_blendshape_change(item, event_type):
    if event_type == carb.settings.ChangeEventType.CHANGED:
        if _g_settings.get_as_bool(PERSISTENT_SETTINGS_PREFIX + "/omnihydra/useSkelAdapterBlendShape"):
            if not _g_settings.get_as_bool(PERSISTENT_SETTINGS_PREFIX + "/omnihydra/useSkelAdapter"):
                _g_settings.set_bool(PERSISTENT_SETTINGS_PREFIX + "/omnihydra/useSkelAdapter", True)


_usd_skel_adapter_blend_shape_setting_sub = omni.kit.app.SettingChangeSubscription(
    PERSISTENT_SETTINGS_PREFIX + "/omnihydra/useSkelAdapterBlendShape",
    partial(on_enable_blendshape_change),
)


def build_usdskel_preferences(pref_builder: PreferenceBuilder):
    with ui.VStack():
        if _g_settings.get(PERSISTENT_SETTINGS_PREFIX + "/omnihydra/useSkelAdapter") is None:
            _g_settings.set_default_bool(PERSISTENT_SETTINGS_PREFIX + "/omnihydra/useSkelAdapter", True)

        if _g_settings.get(PERSISTENT_SETTINGS_PREFIX + "/omnihydra/useSkelAdapterBlendShape") is None:
            _g_settings.set_default_bool(
                # OM-46552
                # https://nvidia-omniverse.atlassian.net/browse/OM-46552
                PERSISTENT_SETTINGS_PREFIX + "/omnihydra/useSkelAdapterBlendShape",
                False,
            )
        pref_builder.create_setting_widget(
            "Enable BlendShape",
            PERSISTENT_SETTINGS_PREFIX + "/omnihydra/useSkelAdapterBlendShape",
            SettingType.BOOL,
            tooltip="Enable BlendShape. Will be effective on the next stage load.",
        )
