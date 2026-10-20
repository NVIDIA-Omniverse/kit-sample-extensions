import omni.ext

from .scene import IconScene
from .viewport_overlap import ViewportOverlapsManager

_extension = None


# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.
class PrimIconExtension(omni.ext.IExt):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    def on_startup(self, ext_id):
        global _extension
        _extension = self
        self._vp1_manager = ViewportOverlapsManager()
        self._vp2_scene = None
        # Setup for legacy Viewport only
        if not self._vp1_manager.setup("Viewport", vp1_only=True):
            self._vp1_manager.destroy()
            self._vp1_manager = None

        if not self._vp1_manager:
            # Since legacy Viewport failed, register our scene for all new Viewport instances
            try:
                from omni.kit.viewport.registry import RegisterScene

                self._vp2_scene = RegisterScene(IconScene, ext_id)
            except ImportError:  # pragma: no cover
                import carb

                carb.log_error("Could not register Prim Icon for any Viewport backend")

    def on_shutdown(self):  # pragma: no cover
        global _extension
        _extension = None
        self._vp2_scene = None

        if self._vp1_manager:
            self._vp1_manager.destroy()
            self._vp1_manager = None


def get_instance():
    return _extension
