import omni.ui as ui
from omni.kit.menu.utils import MenuHelperWindow

from .model_registry_panel import ModelRegistryPanel


class ModelRegistryWindow(MenuHelperWindow):
    """UI window for browsing and configuring the Model Registry."""

    def __init__(self):
        super().__init__(
            title="Model Registry",
            width=500,
            height=800,
            dockPreference=ui.DockPreference.RIGHT,
        )
        # Build out the scene
        self.frame.set_build_fn(self._build_ui)

    def destroy(self) -> None:
        # clean the ui panel cache
        self._model_registry_panel = None
        super().destroy()

    def _build_ui(self):
        self.deferred_dock_in("Stage", ui.DockPolicy.CURRENT_WINDOW_IS_ACTIVE)
        self.dock_order = 4
        with self.frame:
            with ui.ScrollingFrame():
                with ui.VStack(spacing=0):
                    self._model_registry_panel = ModelRegistryPanel()
                    # refresh the UI panel
                    self._model_registry_panel.build_ui_frame()