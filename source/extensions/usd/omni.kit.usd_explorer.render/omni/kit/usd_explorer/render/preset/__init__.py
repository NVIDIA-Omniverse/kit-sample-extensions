from .render_preset import *


# Cached interface instance pointer
def get_render_preset_instance() -> RenderPreset:
    """Returns cached :class:`omni.kit.usd_explorer.render.preset.RenderPreset` interface"""

    if not hasattr(get_render_preset_instance, "render_preset"):
        get_render_preset_instance.render_preset = RenderPreset()
    return get_render_preset_instance.render_preset
