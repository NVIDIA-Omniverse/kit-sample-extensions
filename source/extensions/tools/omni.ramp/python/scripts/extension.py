import carb
import omni.ext

from ..bindings._omni_ramp import *
from .commands import *
from .ramp import *


class PublicExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        self._interface = acquire_interface()
        # example use of the ramp widgets
        # self._ramp = Window2(self._interface)

    def on_shutdown(self):
        # example use of the ramp widgets
        # self._ramp.on_shutdown()
        # self._ramp = None
        release_interface(self._interface)
