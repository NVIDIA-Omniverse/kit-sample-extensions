import omni.ext

from ..bindings._omni_genproc_core import *


class PublicExtension(omni.ext.IExt):
    def __init__(self):
        super().__init__()
        omni.graph.ui.ComputeNodeWidget.get_instance().add_template_path(__file__)

    def on_startup(self, ext_id):
        self._interface = acquire_interface()

    def on_shutdown(self):
        release_interface(self._interface)
