from typing import Optional

import carb.settings
from omni import ui
from omni.kit.browser.material import MaterialBrowserModel, MaterialDetailDelegate, MaterialOptionsMenu

from .models import MaterialPrimDetailItem, StageMaterialModel
from .widgets import MaterialBrowserWidget, MaterialPrimDelegate, MaterialStageOptionsMenu

SETTING_ROOT = "/exts/omni.kit.window.material/"
SETTING_MIN_THUMBNAIL_SIZE = SETTING_ROOT + "min_thumbnail_size"
SETTING_MAX_THUMBNAIL_SIZE = SETTING_ROOT + "max_thumbnail_size"
SETTING_LOAD_AFTER_STARTUP = SETTING_ROOT + "load_after_startup"
SETTING_DATA_TIMEOUT = SETTING_ROOT + "data/timeout"


class MaterialWindow(ui.Window):
    """
    Represent a window to show and edit materials.
    """

    WINDOW_TITLE = "Materials"

    def __init__(self, visible=True):
        super().__init__(
            self.WINDOW_TITLE,
            visible=visible,  # This window will user renderer output, so turn of 'rasterization' which would
            # currently try to cache an uncacheable texture-handle
            raster_policy=ui.RasterPolicy.NEVER,
        )

        self._widget: Optional[MaterialBrowserWidget] = None

        self.frame.set_build_fn(self._build_ui)
        # Dock it to the same space where Stage is docked.
        self.deferred_dock_in("Content")

    def destroy(self) -> None:
        self.visible = False
        if self._widget is not None:
            self._widget.destroy()

        super().destroy()

    @property
    def browser_widget(self) -> Optional[MaterialBrowserWidget]:
        return self._widget

    @property
    def browser_model(self) -> Optional[MaterialBrowserModel]:
        return self.browser_widget._browser_model if self.browser_widget else None

    def _build_ui(self):
        with self.frame:
            self._widget = MaterialBrowserWidget()
