import omni.ext

from ..bindings._omni_anim_timeline import *


class Extension(omni.ext.IExt):
    def on_startup(self, ext_id):
        self._ext = acquire_interface()

    def on_shutdown(self):
        release_interface(self._ext)
