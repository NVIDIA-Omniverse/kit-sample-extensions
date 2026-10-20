import carb.settings
import omni.ext
import omni.ui as ui
from omni.kit.viewport.menubar.core import ViewportMenubar, ViewportMenuItem, ViewportMenuSpacer

from .style import BOTTOMBAR_STYLE

# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.

__all__ = ["Extension", "get_bottombar_name"]

SETTINGS_TOOT = "exts/omni.kit.viewport.menubar.bottom/"


class Extension(omni.ext.IExt):
    BOTTOMBAR_NAME = None

    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    def on_startup(self, ext_id):
        settings = carb.settings.get_settings()
        bar_name = settings.get_as_string(SETTINGS_TOOT + "barName")
        Extension.BOTTOMBAR_NAME = bar_name

        spacing = settings.get_as_int(SETTINGS_TOOT + "spacing")
        self._bottombar = ViewportBottomBar(bar_name, spacing)

        with self._bottombar:
            ViewportMenuSpacer()

    def on_shutdown(self):
        self._bottombar.destroy()
        self._bottombar = None


class ViewportMenuBlank(ViewportMenuItem):
    """A simple spacer with fixed width"""

    def __init__(self, order_setting_path: str):
        super().__init__(order_setting_path=order_setting_path)

    def build_fn(self, factory):
        pass

    @property
    def computed_width(self) -> float:
        return 0


class ViewportBottomBar(ViewportMenubar):
    def __init__(self, name: str, spacing: int = 5):
        self._spacing = spacing
        super().__init__(name, direction=ui.Direction.LEFT_TO_RIGHT, spacing=spacing, style=BOTTOMBAR_STYLE)

        with self:
            # At the right most (order = 1000), put a blank item
            # This is used to ensure that we have a spacing at the right most.
            setting_path = SETTINGS_TOOT + "rightSpacingOrder"
            carb.settings.get_settings().set_int(setting_path, 1000)
            ViewportMenuBlank(order_setting_path=setting_path)

    def build_fn(self, menu_items, factory):
        with ui.VStack(height=ui.Fraction(1.0)):
            ui.Spacer()
            super().build_fn(menu_items, factory, content_clipping=False)
            ui.Spacer(height=self._spacing)


def get_bottombar_name():
    """Get the bottom bar name if there is an instance of bottom bar"""
    return Extension.BOTTOMBAR_NAME
