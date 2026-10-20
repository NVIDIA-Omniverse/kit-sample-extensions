import carb.settings

PERSISTENT_SETTINGS_PREFIX = "/persistent"

DEFAULT_TANGENT_TYPE_SETTING = f"{PERSISTENT_SETTINGS_PREFIX}/exts/omni.anim.curve.core/defaultTangentType"
DEFAULT_TANGENT_WEIGHTED_SETTING = f"{PERSISTENT_SETTINGS_PREFIX}/exts/omni.anim.curve.core/defaultTangentWeighted"
DEFAULT_TANGENT_BROKEN_SETTING = f"{PERSISTENT_SETTINGS_PREFIX}/exts/omni.anim.curve.core/defaultTangentBroken"
DEFAULT_TANGENT_PRE_INFINITY_TYPE_SETTING = (
    f"{PERSISTENT_SETTINGS_PREFIX}/exts/omni.anim.curve.core/defaultTangentPreInfinity"
)
DEFAULT_TANGENT_POST_INFINITY_TYPE_SETTING = (
    f"{PERSISTENT_SETTINGS_PREFIX}/exts/omni.anim.curve.core/defaultTangentPostInfinity"
)

DefaultTangentTypeSettingTokens = ["auto", "smooth", "flat", "linear", "step"]  # intentionally no "fixed"
DefaultInfinityTypeSettingTokens = ["constant", "cycle", "cycleRelative", "linear", "oscillate"]

_g_settings = carb.settings.get_settings()


def get_default_tangent_type() -> str:
    tangent_type = _g_settings.get_as_string(DEFAULT_TANGENT_TYPE_SETTING)
    if tangent_type in DefaultTangentTypeSettingTokens:
        return tangent_type
    else:
        # carb.log_warn(f"Saved Default Tangent Type setting invalid: {tangent_type}")
        return DefaultTangentTypeSettingTokens[0]


def get_default_tangent_weighted() -> bool:
    weighted = _g_settings.get_as_bool(DEFAULT_TANGENT_WEIGHTED_SETTING)
    return weighted


def get_default_tangent_broken() -> bool:
    broken = _g_settings.get_as_bool(DEFAULT_TANGENT_BROKEN_SETTING)
    return broken


def get_default_pre_infinity_type() -> str:
    pre_infinity_type = _g_settings.get_as_string(DEFAULT_TANGENT_PRE_INFINITY_TYPE_SETTING)
    if pre_infinity_type in DefaultInfinityTypeSettingTokens:
        return pre_infinity_type
    else:
        # carb.log_warn(f"Saved Default Pre-Infinity Type setting invalid: {pre_infinity_type}")
        return DefaultInfinityTypeSettingTokens[0]


def get_default_post_infinity_type() -> str:
    post_infinity_type = _g_settings.get_as_string(DEFAULT_TANGENT_POST_INFINITY_TYPE_SETTING)
    if post_infinity_type in DefaultInfinityTypeSettingTokens:
        return post_infinity_type
    else:
        # carb.log_warn(f"Saved Default Post-Infinity Type setting invalid: {post_infinity_type}")
        return DefaultInfinityTypeSettingTokens[0]
