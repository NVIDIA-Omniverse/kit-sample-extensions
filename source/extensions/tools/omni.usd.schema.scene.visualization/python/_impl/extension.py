import os

import omni.ext
from pxr import Plug

# five levels -- usd/schema/scene/visualization/_impl
pluginsRoot = os.path.normpath(os.path.join(os.path.dirname(__file__), "../../../../../generated"))

Plug.Registry().RegisterPlugins(pluginsRoot)


class PublicExtension(omni.ext.IExt):
    def __init__(self):
        super().__init__()

    def on_startup(self, ext_id):
        pass

    def on_shutdown(self):
        pass
