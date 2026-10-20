from .render_settings import *


# Cached interface instance pointer
def get_render_settings_instance() -> RenderSettingWindow:
    """Returns cached :class:`omni.kit.usd_explorer.render.preset.RenderPreset` interface"""

    if not hasattr(get_render_settings_instance, "render_preset"):
        get_render_settings_instance.render_preset = RenderSettingWindow()
    return get_render_settings_instance.render_preset
