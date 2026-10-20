__all__ = ["get_prim_icon_interface", "IconScene", "PrimIcon"]

from .extension import *
from .scene import IconScene, PrimIcon


# Cached interface instance pointer
def get_prim_icon_interface():
    """Returns cached :class:`omni.kit.prim.icon IPrimIcon` interface"""
    if not hasattr(get_prim_icon_interface, "primicon_scene"):
        get_prim_icon_interface.primicon_scene = PrimIcon.get_instance()
    return get_prim_icon_interface.primicon_scene
