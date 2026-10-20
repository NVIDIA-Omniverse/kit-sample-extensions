import omni.ext
import omni.kit.app

from ..bindings._omni_scene_visualization_core import *


class PublicExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        self.visualization_interface = acquire_interface()

    def on_shutdown(self):
        release_interface(self.visualization_interface)
