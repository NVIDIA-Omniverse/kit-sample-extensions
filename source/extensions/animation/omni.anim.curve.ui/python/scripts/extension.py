import omni.ext

from .context_menu import AnimContextMenu
from .simplification_menu import SimplificationMenu
from .timesample_conversion_menu import TimesampleConversionMenu

_extension_instance = None


class AnimCurveUIExtension(omni.ext.IExt):
    def on_startup(self):
        global _extension_instance
        _extension_instance = self

        self._context_menu = AnimContextMenu()
        self._simplification_menu = SimplificationMenu()
        self._timesamples_converter = TimesampleConversionMenu()

    def on_shutdown(self):
        global _extension_instance
        _extension_instance = None

        self._context_menu.on_shutdown()
        self._context_menu = None
        if self._simplification_menu:
            self._simplification_menu.destory()
            self._simplification_menu = None
        if self._timesamples_converter:
            self._timesamples_converter.destory()
            self._timesamples_converter = None


def get_instance():
    return _extension_instance
