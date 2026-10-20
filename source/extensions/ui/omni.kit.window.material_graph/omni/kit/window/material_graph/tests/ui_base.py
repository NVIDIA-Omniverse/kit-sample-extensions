import omni.ext
import omni.ui
from omni.ui.tests.test_base import OmniUiTest

from ..scripts.extension import GraphExtension, get_graph_window
from ..scripts.ui.window import GraphWindow
from .test_mixin import MaterialGraphTestMixin


class MaterialGraphUiTestBase(MaterialGraphTestMixin, OmniUiTest):
    """Base UI test class with a fresh stage and material graph window."""

    async def setUp(self) -> None:
        """Initialize the UI test window and stage."""
        await super().setUp()
        await self._setup_common(create_stage=True)

        ext_manager = self._app.get_extension_manager()
        self.assertIsNotNone(ext_manager)
        self.assertTrue(ext_manager.is_extension_enabled(self.MODULE_ID))

        self._created_graph_window = False
        self._initial_window_visible = None
        self._initial_window_handle = None

        self._graph_window = get_graph_window()
        if self._graph_window is None:
            ext_id = ext_manager.get_extension_id_by_module(self.MODULE_ID)
            self.assertIsNotNone(ext_id)
            ext_name = omni.ext.get_extension_name(ext_id)
            self.assertIsNotNone(ext_name)
            self._graph_window = GraphWindow(GraphExtension._WINDOW_NAME, ext_name)
            self._created_graph_window = True

        await self.show_window(True)
        self._window_handle = self.get_window_handle()
        if self._initial_window_handle is None:
            self._initial_window_handle = self._window_handle
            self._initial_window_visible = self._window_handle.visible

        self.assertIsNotNone(self._window_handle)
        self.assertIsNotNone(self._graph_window)
        self.assertIsNotNone(self._graph_window.graph_widget)

    async def tearDown(self) -> None:
        """Destroy any created window and clean up resources."""
        try:
            await self.show_window(False)
            if self._created_graph_window and self._graph_window:
                self._graph_window.destroy()
            self._window_handle = None
            self._graph_window = None
            self._initial_window_visible = None
            self._initial_window_handle = None
            self._created_graph_window = False
        finally:
            await self._teardown_common()
            await super().tearDown()

    async def show_window(self, visible: bool = True) -> None:
        """Show or hide a window and wait for UI updates."""
        if self._initial_window_handle is None:
            self._initial_window_handle = omni.ui.Workspace.get_window(GraphExtension._WINDOW_NAME)
            if self._initial_window_handle:
                self._initial_window_visible = self._initial_window_handle.visible
        omni.ui.Workspace.show_window(GraphExtension._WINDOW_NAME, visible)
        await self.wait_n_updates(2)

    def get_window_handle(self) -> omni.ui.Window:
        """Return the current window handle."""
        window_handle = omni.ui.Workspace.get_window(GraphExtension._WINDOW_NAME)
        self.assertIsNotNone(window_handle)
        return window_handle
