"""Module implementing the StageMenusExtension that manages the startup and shutdown of ContentBrowserOptions for stage menu customization in Omni UI."""

import omni.ext

from .content_browser_options import ContentBrowserOptions


class StageMenusExtension(omni.ext.IExt):

    def __init__(self):
        super().__init__()
        self._content_browser_options = None

    def on_startup(self, ext_id):
        self._content_browser_options = ContentBrowserOptions()
        self._content_browser_options.startup()

    def on_shutdown(self):
        self._content_browser_options.shutdown()
        self._content_browser_options = None
