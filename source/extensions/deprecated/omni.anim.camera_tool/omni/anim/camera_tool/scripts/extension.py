import os

import omni.ext

# from commands import *
from .viewport.viewport_mods import *


class PublicExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        self._viewport_watcher = ViewportWatcher()
        self._viewport_watcher.on_startup()
        return

    def on_shutdown(self):
        self._viewport_watcher.on_shutdown()
        self._viewport_watcher = None
        return
