# pylint: disable=no-member,attribute-defined-outside-init
"""Implement material graph extension logic for `ui/sections/graph/widget.py`."""

from typing import Any, Optional

import omni.ui
import omni.usd
from omni.kit.graph.editor.core import GraphEditorCoreWidget
from pxr import (
    Sdf,
    Usd,
    UsdShade,
)

from ....config.logging import log_exception, logger
from ....config.nodes import Nodes
from ....config.paths import Paths
from ....models.catalog.tree import CatalogTreeModel
from ....models.graph.isolation import MaterialGraphIsolationModel
from ....settings.settings import Settings
from ....utils.async_utils import wait_for_updates
from ....utils.file_timestamp_cache import FileTimestampCache
from ....utils.lifecycle_registry import LifecycleRegistry
from ....validation.result import ValidationResult
from ....validation.severity import ValidationSeverity
from ...controllers import (
    CatalogContextMenuController,
    CatalogController,
    ContextModelController,
    ContextSoloController,
    ContextSwitcherController,
    ContextVisibilityController,
    GraphBackgroundDropIndicatorController,
    GraphSettingsController,
    InteractionController,
    NodeCreationController,
    NodeGraphExportController,
    StageLifecycleController,
    StartupController,
    ToolbarController,
)
from ...controllers.core.context_solo import is_solo_supported

# pylint: disable=no-member,attribute-defined-outside-init
from ...delegates import MaterialGraphNodeDelegate
from .breadcrumbs import MaterialGraphBreadcrumbs
from .mixins import (
    GraphWidgetCatalogMixin,
    GraphWidgetDestroyMixin,
    GraphWidgetDragDropMixin,
)
from .splitter import MaterialGraphSplitter

g_ext_manager = omni.kit.app.get_app_interface().get_extension_manager()


class GraphWidget(GraphWidgetCatalogMixin, GraphWidgetDragDropMixin, GraphWidgetDestroyMixin, GraphEditorCoreWidget):
    """Main graph editor widget for material graphs."""

    _BANNER_MIN_HEIGHT = 24
    _BANNER_MAX_HEIGHT = 128
    _BANNER_LINE_HEIGHT = 16
    _BANNER_PADDING = 8
    _BANNER_CLOSE_STYLE = {
        "Button": {"background_color": 0x00000000, "margin": 0, "padding": 0},
        "Button:hovered": {"background_color": 0x18FFFFFF},
        "Button:pressed": {"background_color": 0x28FFFFFF},
        "Button.Label": {"color": 0xCCFFFFFF, "font_size": 16},
    }

    def __init__(
        self, context_manager: object, window_name: str, ext_name: str, show_startup_buttons: bool = True
    ) -> None:
        """Initialize the graph widget and controllers."""
        self._usd_context = omni.usd.get_context()

        self._context_manager = context_manager
        self._current_context = None
        self._current_model = None

        self._catalog_model = CatalogTreeModel()
        self._error_frame = None
        self._error_label = None
        self._error_scroll_frame = None
        self._error_close_button = None
        self._error_message = ""
        self._dismissed_error_message = None
        self._warning_frame = None
        self._warning_label = None
        self._warning_scroll_frame = None
        self._warning_close_button = None
        self._warning_message = ""
        self._dismissed_warning_message = None
        self._warning_overlay = None
        self._last_validation_result = None
        self._last_logged_error_message = None
        self._last_logged_warning_message = None
        self._error_indicator_frame = None
        self._error_badge_frame = None
        self._error_count_label = None
        self._upgrade_menu_frame = None
        self._warning_badge_frame = None
        self._warning_count_label = None
        self._graph_drop_overlay = GraphBackgroundDropIndicatorController(self._set_graph_background_override)
        self._graph_frame = None
        self._breadcrumbs = None
        self._catalog_drop_cache = FileTimestampCache()
        self._graph_background_color = None
        self._open_graph_lifecycle = LifecycleRegistry()
        self._upgrade_refresh_lifecycle = LifecycleRegistry()

        self._graph_delegate = MaterialGraphNodeDelegate()

        self._build_pre_super_controllers(ext_name, window_name)

        self._graph_toolbar_frame = None

        from ...graph_canvas_view import GraphCanvasView

        super().__init__(
            delegate=self._graph_delegate,
            style=self.get_specialized_style(),
            catalog_model=self._catalog_model,
            toolbar_items=[],
            view_type=GraphCanvasView,
            has_catalog=False,
        )

        self._build_post_super_controllers(show_startup_buttons)
        self._toolbar_controller.setup_actions_and_hotkeys()

        self._catalog_controller.apply_visibility()
        self._context_visibility_controller.setup_menu_items()
        self._nodegraph_export_controller.setup_menu_items()

    def _build_pre_super_controllers(self, ext_name: str, window_name: str) -> None:
        """Build controllers needed before super().__init__."""
        self._context_visibility_controller = ContextVisibilityController(self)
        self._nodegraph_export_controller = NodeGraphExportController(self)
        self._context_switcher = ContextSwitcherController(self, self._context_manager)
        self._solo_controller = ContextSoloController(self, self._context_manager)
        self._catalog_context_menu_controller = CatalogContextMenuController(self)
        self._toolbar_controller = ToolbarController(
            self,
            ext_name,
            window_name,
            g_ext_manager,
            self._context_switcher,
        )

    def _build_post_super_controllers(self, show_startup_buttons: bool = True) -> None:
        """Build controllers that require initialized widget state."""
        self._catalog_controller = CatalogController(self)
        self._graph_settings_controller = GraphSettingsController(self)
        self._node_creation_controller = NodeCreationController(
            self,
            self._context_visibility_controller,
            self._catalog_model,
            self._context_manager,
            self._usd_context,
            self._graph_settings_controller,
        )
        self._interaction_controller = InteractionController(
            self,
            self._node_creation_controller,
            self._catalog_model,
        )
        self._stage_lifecycle_controller = StageLifecycleController(self, self._usd_context)
        self._context_model_controller = ContextModelController(
            self,
            self._context_switcher,
            self._context_manager,
            self._usd_context,
            self._catalog_model,
        )
        self._startup_controller = StartupController(self, show_startup_buttons)
        self._stage_lifecycle_controller.set_visible(True)

    def get_specialized_style(self) -> dict:
        """Return the base UI style for this widget."""
        style = self._graph_delegate.get_style()

        color_accept = omni.ui.color(0.15, 0.90, 0.15, 1.0)
        color_reject = omni.ui.color(0.90, 0.15, 0.15, 1.0)

        style.update(
            {
                "Graph": {"background_color": 0xFF23211F},
                "MaterialGraph.ErrorBanner": {"background_color": 0xFF3A2424},
                "MaterialGraph.ErrorText": {"color": 0xFFFFD7D7},
                "MaterialGraph.WarningBanner": {"background_color": 0xFF6A6420},
                "MaterialGraph.WarningText": {"color": 0xFFFFFFE0},
                "Graph.Connection.Reject": {
                    "color": color_reject,
                    "border_width": 3.0,
                },
                "Graph.Connection.Reject:hovered": {
                    "color": color_reject,
                    "border_width": 4.0,
                },
                "Graph.Connection.Accept": {
                    "color": color_accept,
                    "border_width": 3.0,
                },
                "Graph.Connection.Accept:hovered": {
                    "color": color_accept,
                    "border_width": 4.0,
                },
                "Graph.Connection.Warning": {
                    "color": omni.ui.color(0.90, 0.78, 0.15, 1.0),
                    "border_width": 3.0,
                },
                "Graph.Connection.Warning:hovered": {
                    "color": omni.ui.color(1.0, 0.88, 0.25, 1.0),
                    "border_width": 4.0,
                },
                "Graph.Node.Error.Background": {"background_color": Nodes.ERROR_BACKGROUND_COLOR},
                "Graph.Node.Error.Highlight": {"background_color": Nodes.ERROR_HIGHLIGHT_COLOR},
                "Graph.Node.Warning.Background": {"background_color": Nodes.WARNING_BACKGROUND_COLOR},
                "Graph.Node.Warning.Highlight": {"background_color": Nodes.WARNING_HIGHLIGHT_COLOR},
                "Graph.Node.Warning.Label": {"color": Nodes.WARNING_LABEL_COLOR, "font_size": 15},
                "Graph.Node.Expansion.On": {"background_color": Nodes.EXPANSION_ON_COLOR_ABGR},
                "Graph.Node.Expansion.Off": {"background_color": Nodes.EXPANSION_OFF_COLOR_ABGR},
                "ToolBar": {"margin_height": 0},
            }
        )

        return style

    # -- custom toolbar with inline context tabs -------------------------------

    _CTX_ACTIVE_TEXT = 0xF5EEEEEE
    _CTX_INACTIVE_TEXT = 0xB3DDDDDD
    _CTX_HOVER_TEXT = 0xD6FFFFFF
    _CTX_ACCENT = 0xFFADFB47

    _ICON_BTN = {
        "Button": {"background_color": 0x00000000, "margin": 0, "padding": 3},
        "Button:hovered": {"background_color": 0x12FFFFFF},
        "Button:pressed": {"background_color": 0x1FFFFFFF},
    }
    _TEXT_BTN = {
        "Button": {"background_color": 0x00000000, "margin": 0, "padding": 6},
        "Button:hovered": {"background_color": 0x12FFFFFF},
        "Button:pressed": {"background_color": 0x1FFFFFFF},
        "Button.Label": {"color": 0xB8AAAAAA, "font_size": 14},
        "Button.Label:hovered": {"color": 0xEBFFFFFF},
    }
    _MENU_BTN = {
        "Button": {"background_color": 0x00000000, "margin": 0, "padding": 3},
        "Button:hovered": {"background_color": 0x12FFFFFF},
        "Button:pressed": {"background_color": 0x1FFFFFFF},
    }
    _TOGGLE_ACTIVE_BTN = {
        "Button": {"background_color": 0x70606899, "margin": 0, "padding": 3, "border_radius": 3},
        "Button:hovered": {"background_color": 0x886A7284},
        "Button:pressed": {"background_color": 0x885A5E70},
    }
    _ICON_BTN_DISABLED = {
        "Button": {"background_color": 0x00000000, "margin": 0, "padding": 3},
        "Button.Image": {"color": 0x55FFFFFF},
    }

    def _build_graph_toolbar(self) -> None:
        """Build the graph panel toolbar: [+][pen] [ctx tabs] [pause][solo][menu]."""
        has_model = bool(self.model)

        with omni.ui.HStack(height=0, spacing=6):
            omni.ui.Button(
                "",
                image_url=f"{Paths.TOOLBAR_ICON_PATH}/create_graph_dark.svg",
                clicked_fn=self._toolbar_controller.on_toolbar_create_graph_clicked,
                tooltip="Create a new material",
                image_width=16,
                image_height=16,
                width=24,
                height=24,
                style=self._ICON_BTN,
            )
            omni.ui.Button(
                "",
                image_url=f"{Paths.TOOLBAR_ICON_PATH}/edit_graph_dark.svg",
                clicked_fn=self._toolbar_controller.on_toolbar_edit_graph_clicked,
                tooltip="Edit selected material" if has_model else "No material selected",
                enabled=has_model,
                image_width=16,
                image_height=16,
                width=24,
                height=24,
                style=self._ICON_BTN if has_model else self._ICON_BTN_DISABLED,
            )

            self._build_material_title_inline()
            self._build_error_indicator_inline()

            omni.ui.Spacer()

            self._build_context_tabs_inline()

            omni.ui.Spacer()

            if self.model and self.model.pause is not None:
                self._build_pause_buttons_inline()

            self._build_solo_button()

            omni.ui.Button(
                "",
                image_url=f"{Paths.TOOLBAR_ICON_PATH}/hamburger.svg",
                clicked_fn=self._toolbar_controller.on_toolbar_overflow_clicked,
                image_width=16,
                image_height=16,
                width=24,
                height=24,
                style=self._MENU_BTN,
            )
            omni.ui.Spacer(width=8)

        if self._last_validation_result:
            self._apply_error_indicator(self._last_validation_result)

    def _build_material_title_inline(self) -> None:
        """Show current material short name in the toolbar with full-path tooltip."""
        full_path = ""
        short_name = ""
        try:
            cm = self._context_manager
            if cm and hasattr(cm, "_root_prim") and cm._root_prim:
                prim = cm._root_prim
                full_path = str(prim.GetPath())
                short_name = prim.GetName()
        except Exception:
            pass
        if not short_name:
            try:
                if self.model and hasattr(self.model, "prim_path"):
                    full_path = str(self.model.prim_path)
                    short_name = full_path.rsplit("/", 1)[-1] if "/" in full_path else full_path
            except Exception:
                pass
        if short_name:
            omni.ui.Spacer(width=16)
            with omni.ui.VStack(width=1, spacing=0):
                omni.ui.Spacer(height=5)
                omni.ui.Rectangle(
                    height=16,
                    width=1,
                    style={"background_color": 0x20FFFFFF},
                )
                omni.ui.Spacer()
            omni.ui.Spacer(width=10)
            with omni.ui.VStack(width=0, height=0, spacing=0):
                omni.ui.Button(
                    short_name,
                    enabled=False,
                    tooltip=full_path,
                    style={
                        "Button": {
                            "background_color": 0x00000000,
                            "border_radius": 0,
                            "border_width": 0,
                            "margin": 0,
                            "padding": 6,
                        },
                        "Button.Label": {"color": 0xDDDDDDDD, "font_size": 14},
                    },
                    height=26,
                    width=0,
                )
                omni.ui.Spacer(height=2)

    def _build_error_indicator_inline(self) -> None:
        """Show error badge, upgrade affordance, and warning badge in the toolbar."""
        with omni.ui.Frame(visible=False, width=0, tooltip="") as frame:
            self._error_indicator_frame = frame
            with omni.ui.HStack(spacing=0, width=0):
                omni.ui.Spacer(width=10)

                # --- Error badge: red dot + count ---
                with omni.ui.Frame(
                    visible=False,
                    width=0,
                    mouse_pressed_fn=lambda x, y, button, modifiers: self.restore_error(),
                ) as err_frame:
                    self._error_badge_frame = err_frame
                    with omni.ui.HStack(spacing=5, width=0):
                        with omni.ui.VStack(width=0, height=0, spacing=0):
                            omni.ui.Spacer(height=8)
                            omni.ui.Circle(
                                radius=4,
                                style={"background_color": 0xFF4040A0},
                                width=8,
                                height=8,
                            )
                            omni.ui.Spacer()
                        self._error_count_label = omni.ui.Label(
                            "",
                            style={"color": 0xFFDDDDDD, "font_size": 13},
                            width=0,
                            height=26,
                        )

                omni.ui.Spacer(width=16)

                # --- Upgrade affordance: inline icon + label ---
                with omni.ui.Frame(visible=False, width=0) as upgrade_frame:
                    self._upgrade_menu_frame = upgrade_frame
                    with omni.ui.HStack(spacing=4, width=0, height=26):
                        with omni.ui.VStack(width=0, spacing=0):
                            omni.ui.Spacer(height=6)
                            omni.ui.Image(
                                f"{Paths.ICON_PATH}/upgrade_warning.svg",
                                width=14,
                                height=14,
                            )
                            omni.ui.Spacer()
                        self._upgrade_label = omni.ui.Label(
                            "Upgrade",
                            width=0,
                            height=26,
                            mouse_pressed_fn=lambda x, y, b, m: self._show_upgrade_menu(),
                        )

                omni.ui.Spacer(width=16)

                # --- Warning badge: cyan dot + count ---
                with omni.ui.Frame(
                    visible=False,
                    width=0,
                    mouse_pressed_fn=lambda x, y, button, modifiers: self.restore_warning(),
                ) as warn_frame:
                    self._warning_badge_frame = warn_frame
                    with omni.ui.HStack(spacing=5, width=0):
                        with omni.ui.VStack(width=0, height=0, spacing=0):
                            omni.ui.Spacer(height=8)
                            omni.ui.Circle(
                                radius=4,
                                style={"background_color": 0xFF30A8D0},
                                width=8,
                                height=8,
                            )
                            omni.ui.Spacer()
                        self._warning_count_label = omni.ui.Label(
                            "",
                            style={"color": 0xFFDDDDDD, "font_size": 13},
                            width=0,
                            height=26,
                        )

    def _build_context_tabs_inline(self) -> None:
        """Render MDL / MaterialX / Universal context tabs with active underline."""
        from functools import partial as _partial

        if not self._context_switcher:
            return
        plugins_by_name = {p.name: p for p in self._context_manager.get_plugins()}
        ordered = []
        for ctx in Settings.get_render_contexts():
            name = "universal" if ctx == "universalRenderContext" else ctx
            plugin = plugins_by_name.get(name)
            if plugin:
                ordered.append(plugin)
        for _, plugin in plugins_by_name.items():
            if plugin not in ordered:
                ordered.append(plugin)
        if not ordered:
            return

        for plugin in ordered:
            is_active = plugin.name == self.current_context
            text_color = self._CTX_ACTIVE_TEXT if is_active else self._CTX_INACTIVE_TEXT
            hover_color = self._CTX_ACTIVE_TEXT if is_active else self._CTX_HOVER_TEXT

            with omni.ui.VStack(width=0, height=0, spacing=0):
                omni.ui.Button(
                    plugin.display_name,
                    clicked_fn=_partial(self._toolbar_controller.switch_context, plugin.name),
                    style={
                        "Button": {
                            "background_color": 0x00000000,
                            "border_radius": 0,
                            "border_width": 0,
                            "margin": 0,
                            "padding": 6,
                        },
                        "Button:hovered": {"background_color": 0x08FFFFFF},
                        "Button.Label": {"color": text_color, "font_size": 14},
                        "Button.Label:hovered": {"color": hover_color},
                    },
                    height=26,
                    width=0,
                    tooltip=f"Switch to {plugin.display_name} context",
                )
                if is_active:
                    omni.ui.Rectangle(height=2, style={"background_color": self._CTX_ACCENT})
                else:
                    omni.ui.Spacer(height=2)

    def _build_pause_buttons_inline(self) -> None:
        """Render pause/recompile buttons."""
        is_paused = bool(self.model and self.model.pause)
        if is_paused:
            omni.ui.Button(
                "",
                image_url=f"{Paths.TOOLBAR_ICON_PATH}/reload_dark.svg",
                clicked_fn=self._toolbar_controller.unpause_and_pause,
                tooltip="Refresh material, compile then pause\n(CTRL+R)",
                image_width=16,
                image_height=16,
                width=24,
                height=24,
                style=self._ICON_BTN,
            )
        omni.ui.Button(
            "",
            image_url=f"{Paths.TOOLBAR_ICON_PATH}/pause_dark_a.svg",
            clicked_fn=self._toolbar_controller.toggle_material_compilation,
            tooltip="Resume material compilation." if is_paused else "Pause material compilation.",
            image_width=16,
            image_height=16,
            width=24,
            height=24,
            style=self._TOGGLE_ACTIVE_BTN if is_paused else self._ICON_BTN,
        )

    def _build_solo_button(self) -> None:
        """Render the solo toggle button."""
        supported, unsupported_reason = is_solo_supported()
        is_soloed = self._solo_controller and self._solo_controller.soloed_context is not None
        if supported:
            tooltip = (
                "Unsolo (restore all context outputs)"
                if is_soloed
                else "Solo current context (disconnect other contexts' outputs)"
            )
            style = self._TOGGLE_ACTIVE_BTN if is_soloed else self._ICON_BTN
        else:
            tooltip = unsupported_reason or "Solo unavailable: disabled by current Kit settings"
            style = self._ICON_BTN_DISABLED
        omni.ui.Button(
            "",
            image_url=f"{Paths.TOOLBAR_ICON_PATH}/solo_dark.svg",
            clicked_fn=self._on_solo_clicked,
            tooltip=tooltip,
            enabled=supported,
            image_width=16,
            image_height=16,
            width=24,
            height=24,
            style=style,
        )

    def _on_solo_clicked(self) -> None:
        """Toggle solo for the current context."""
        if not self._solo_controller:
            return
        if self._solo_controller.soloed_context is not None:
            self._solo_controller.clear()
        else:
            ctx = self.current_context
            if ctx:
                self._solo_controller.toggle_solo(ctx)

    def rebuild_graph_toolbar(self) -> None:
        """Rebuild the graph toolbar frame to reflect state changes."""
        if self._graph_toolbar_frame:
            self._graph_toolbar_frame.rebuild()

    def ignore_stage_listener_paths(self, paths) -> None:
        """Tell the stage listener to ignore changes to specific attribute paths."""
        if self._isolation_model:
            stage_listener = getattr(self._isolation_model, "_stage_listener", None)
            if stage_listener:
                stage_listener.add_ignored_paths(paths)

    def unignore_stage_listener_paths(self, paths) -> None:
        """Remove attribute paths from the stage listener's ignore set."""
        if self._isolation_model:
            stage_listener = getattr(self._isolation_model, "_stage_listener", None)
            if stage_listener:
                stage_listener.remove_ignored_paths(paths)

    def on_build_graph(self) -> None:
        """Build the graph UI content."""
        with omni.ui.VStack(height=omni.ui.Fraction(1)):

            def _build_catalog_panel() -> None:
                self.on_build_catalog()

            def _build_graph_editor() -> None:
                with omni.ui.VStack(spacing=0):
                    self._graph_toolbar_frame = omni.ui.Frame(height=26, build_fn=self._build_graph_toolbar)
                    self._build_validation_banners()
                    with omni.ui.ZStack(height=omni.ui.Fraction(1)):
                        with omni.ui.Frame(height=omni.ui.Fraction(1)) as graph_frame:
                            self._graph_frame = graph_frame
                            with omni.ui.ZStack(width=omni.ui.Percent(100), height=omni.ui.Percent(100)):
                                super(GraphWidget, self).on_build_graph()
                                if self._graph_view:
                                    self._graph_view.width = omni.ui.Percent(100)
                                    self._graph_view.height = omni.ui.Percent(100)
                                    self._graph_view.set_mouse_hovered_fn(self._on_graph_hovered)
                                    self._graph_view.set_mouse_released_fn(self._on_graph_mouse_released)
                                    if self.model and not self._isolation_model:
                                        self.set_current_compound(None, focus=False)
                                self._graph_drop_overlay.build()
                                with omni.ui.ZStack(width=omni.ui.Percent(100), height=omni.ui.Percent(100)):
                                    with omni.ui.Frame(visible=False) as warning_overlay:
                                        self._warning_overlay = warning_overlay
                                        omni.ui.Rectangle(style={"background_color": 0x557A722A})

            self._splitter_left = MaterialGraphSplitter(
                build_left_fn=_build_catalog_panel,
                build_right_fn=_build_graph_editor,
            )
            self.set_catalog_visible(Settings.show_catalog())
            self._splitter_left.on_build()

    def on_build_breadcrumbs(self) -> None:
        """Push breadcrumb segments to the C++ canvas widget for rendering."""
        if self._breadcrumbs:
            self._breadcrumbs.destroy()
        navigation = []
        if self.model and self._navigation:
            navigation = [self.model[item].name for item in self._navigation]

        self._breadcrumbs = MaterialGraphBreadcrumbs(
            frame=None,
            selected_fn=lambda item: self.set_current_compound(self._navigation[item.id]),
            navigation=navigation,
            canvas_widget=self._graph_view,
        )

    def _update_style(self) -> None:
        """Update widget style based on current context."""
        style = self.get_specialized_style()
        plugin_style = None
        if self.current_context:
            handle = self._context_manager.get_context(self.current_context)
            if handle.plugin:
                plugin_style = handle.plugin.get_style()

        if plugin_style:
            style.update(plugin_style)
        else:
            style.update(
                {
                    "Graph.Node.Icon": {"image_url": f"{Paths.ICON_PATH}/type_function_noBorder_dark.svg"},
                }
            )

        self.style = style

    def on_build_startup(self) -> None:
        """Build startup UI content."""
        self._startup_controller.build_startup()

    def open_graph(
        self,
        prim: Usd.Prim,
        focus_graph_path: Optional[Sdf.Path] = None,
        max_updates: int = 120,
    ) -> None:
        """Schedule an async open_graph task on the widget lifecycle."""
        if self._open_graph_lifecycle:
            self._open_graph_lifecycle.cleanup()
            self._open_graph_lifecycle.add_task(self.open_graph_async(prim, focus_graph_path, max_updates))

    def focus_all_nodes(self, max_updates: int = 8) -> None:
        """Frame the graph view to show all nodes."""

        async def _focus() -> None:
            """Asynchronously execute focus behavior for material graph workflows."""

            if not await self.wait_ready(max_updates):
                return
            for _ in range(max_updates):
                await omni.kit.app.get_app().next_update_async()
            if self._graph_view:
                self._graph_view.focus_on_nodes()

        if self._open_graph_lifecycle:
            self._open_graph_lifecycle.add_task(_focus())

    @property
    def prim(self) -> Optional[Usd.Prim]:
        """Return the current model prim."""
        if self.model:
            return self.model.prim

    def set_current_compound(self, item: object, focus: bool = True, refresh: bool = True) -> None:
        """Set the current compound item and update selection."""
        if item is not None:
            item_name = type(item).__name__
            logger.debug("selection change: %s", item_name)
        self._current_model = item
        graph_model = self.model
        if not self._graph_view or graph_model is None:
            return

        if graph_model[item].nodes is None:
            # This item can't have children
            return

        if self._isolation_model and self._isolation_model._root == item:
            # It happens when double click by input or output node. The model
            # already has this item as a root.
            return

        if item in self._navigation:
            self._navigation = self._navigation[: self._navigation.index(item) + 1]
        elif item is not None:
            self._navigation.append(item)

        self.on_build_breadcrumbs()

        if self._isolation_model:
            self._isolation_model.destroy()
        self._isolation_model = MaterialGraphIsolationModel(graph_model, item)
        self._isolation_changed_subscription = self._isolation_model.subscribe_item_changed(
            self._on_isolation_item_changed
        )

        try:
            self._graph_view.model = self._isolation_model
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_exception(
                logger,
                "compound model switch failed",
                action="set_current_compound",
                exc=exc,
            )

        if focus and item:
            self.focus_on_nodes()

        if self.model:
            self.model.selection = []
        # Root compound (item is None) is selected from GraphEditorCoreWidget.model; the
        # isolation model and graph view are already rebuilt — request_model_refresh
        # only forces a redundant full nodegraph.sync (~seconds on large materials).
        if item is None:
            refresh = False
        if refresh:
            self.request_model_refresh()

    def _on_isolation_item_changed(self, _item: object) -> None:
        """Clear graph when isolation model loses all nodes."""
        if self._isolation_model and self._isolation_model.nodes is None:
            self.clear_all()

    def on_left_mouse_button_double_clicked(self, items: Any) -> Any:
        """Handle double-click interactions for graph items and route to creation/edit actions."""
        return self._interaction_controller.on_left_mouse_button_double_clicked(items)

    def on_right_mouse_button_pressed(self, items: Any, x: Optional[float] = None, y: Optional[float] = None) -> Any:
        """Handle right-click interactions by opening context actions for the hovered item."""
        return self._interaction_controller.on_right_mouse_button_pressed(items, x, y)

    def edit_graph(self, prim: Optional[Usd.Prim] = None) -> None:
        """Edit the graph for a prim."""
        self._context_model_controller.edit_graph(prim)

    def new_graph(self) -> None:
        """Create a new graph in the current context via the context-model controller."""
        self._context_model_controller.new_graph()

    @property
    def current_context(self) -> Optional[str]:
        """Return the current render context name."""
        return self._current_context

    @current_context.setter
    def current_context(self, context_name: Optional[str]) -> None:
        """Set the current render context name."""
        self._current_context = context_name

    def set_context(self, context_name: str) -> bool:
        """Set the current context via the controller."""
        return self._context_model_controller.set_context(context_name)

    def is_mouse_over_node_header(self, item: object) -> bool:
        """Return True if the mouse is over a node header."""
        if self._graph_view and hasattr(self._graph_view, "is_point_over_header"):
            try:
                return self._graph_view.is_point_over_header(item)
            except Exception:
                pass
        return False

    def update_style(self) -> None:
        """Public wrapper to update widget style."""
        return self._update_style()

    @property
    def current_model(self) -> Optional[object]:
        """Return the current graph model."""
        return self._current_model

    @property
    def graph_view(self) -> object:
        """Return the graph view."""
        return self._graph_view

    async def wait_ready(self, max_updates: int = 120) -> bool:
        """Wait for the widget to be ready for graph loading."""
        return await wait_for_updates(
            lambda: bool(self._graph_view),
            max_updates=max_updates,
            timeout_message=f"graph widget readiness timed out after {max_updates} updates: graph view was not created",
        )

    async def open_graph_async(
        self,
        prim: Usd.Prim,
        focus_graph_path: Optional[Sdf.Path] = None,
        max_updates: int = 120,
    ) -> None:
        """Open a graph after the widget is ready."""
        if self._solo_controller:
            self._solo_controller.clear()
        if await self.wait_ready(max_updates):
            # wait a bit longer for the view to initalize
            for _ in range(10):
                await omni.kit.app.get_app().next_update_async()
            self._context_model_controller.open_graph(prim, focus_graph_path)

    @property
    def catalog_model(self) -> Optional[object]:
        """Return the catalog model."""
        return self._catalog_model

    @property
    def isolation_model(self) -> object:
        """Return the isolation model."""
        return self._isolation_model

    def set_toolbar_items(self, items: Any) -> None:
        """No-op — the parent toolbar is disabled; graph toolbar is self-managed."""

    def get_toolbar_items(self, add_pause_button: bool = False) -> Any:
        """Return toolbar items for the current state."""
        return self._toolbar_controller.get_toolbar_items(add_pause_button)

    def reset(self) -> None:
        """Reset the widget state and catalog."""
        had_graph = self.model is not None or self.current_context is not None
        if self._solo_controller:
            self._solo_controller.clear()
        self._current_model = None
        self.model = None
        self._current_context = None
        self.clear_error(reset_dismissal=True)
        self.clear_warning(reset_dismissal=True)
        if self._warning_overlay:
            self._warning_overlay.visible = False
        self._context_manager.clear()
        self.set_toolbar_items(self.get_toolbar_items(False))

        if self._catalog_model:
            self._catalog_model.clear()

        if had_graph:
            startup_frame = getattr(self, "_GraphEditorCoreWidget__startup_frame", None)
            if startup_frame:
                startup_frame.set_build_fn(self.on_build_startup)
                startup_frame.rebuild()
            self.rebuild_graph_toolbar()

    def set_visibility(self, visible: bool) -> None:
        """Update visibility and reset state as needed."""
        if not self._stage_lifecycle_controller:
            return
        if visible:
            needs_reset = not self.model
            if not needs_reset:
                try:
                    needs_reset = not self.model.prim_exists()
                except (
                    RuntimeError,
                    ValueError,
                    TypeError,
                    AttributeError,
                ) as exc:  # pylint: disable=broad-exception-caught
                    logger.warning(
                        "graph visibility check failed for model_path='%s': %s; the graph will be reset",
                        getattr(self.model, "prim_path", "<unknown>"),
                        exc,
                    )
                    needs_reset = True
            if needs_reset:
                self.reset()
        self._stage_lifecycle_controller.set_visible(visible)

    def _build_validation_banners(self) -> None:
        """Build validation banners above the native canvas input region."""
        self._build_error_banner()
        self._build_warning_banner()

    def _build_error_banner(self) -> None:
        """Build the error banner UI."""
        with omni.ui.Frame(
            height=self._BANNER_MIN_HEIGHT,
            visible=False,
            style_type_name_override="MaterialGraph.ErrorBanner",
        ) as frame:
            self._error_frame = frame
            with omni.ui.HStack(height=omni.ui.Percent(100), spacing=4):
                omni.ui.Spacer(width=6)
                with omni.ui.ScrollingFrame(
                    width=omni.ui.Fraction(1),
                    height=omni.ui.Percent(100),
                    horizontal_scrollbar_policy=omni.ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                    vertical_scrollbar_policy=omni.ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                ) as scroll_frame:
                    self._error_scroll_frame = scroll_frame
                    self._error_label = omni.ui.Label(
                        "",
                        width=omni.ui.Percent(100),
                        height=0,
                        word_wrap=True,
                        style_type_name_override="MaterialGraph.ErrorText",
                    )
                self._error_close_button = omni.ui.Button(
                    "×",
                    width=24,
                    height=24,
                    tooltip="Dismiss this error message",
                    clicked_fn=self.dismiss_error,
                    style=self._BANNER_CLOSE_STYLE,
                )
                omni.ui.Spacer(width=2)

    def _build_warning_banner(self) -> None:
        """Build the warning banner UI."""
        with omni.ui.Frame(
            height=self._BANNER_MIN_HEIGHT,
            visible=False,
            style_type_name_override="MaterialGraph.WarningBanner",
        ) as frame:
            self._warning_frame = frame
            with omni.ui.HStack(height=omni.ui.Percent(100), spacing=4):
                omni.ui.Spacer(width=6)
                with omni.ui.ScrollingFrame(
                    width=omni.ui.Fraction(1),
                    height=omni.ui.Percent(100),
                    horizontal_scrollbar_policy=omni.ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                    vertical_scrollbar_policy=omni.ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                ) as scroll_frame:
                    self._warning_scroll_frame = scroll_frame
                    self._warning_label = omni.ui.Label(
                        "",
                        width=omni.ui.Percent(100),
                        height=0,
                        word_wrap=True,
                        style_type_name_override="MaterialGraph.WarningText",
                    )
                self._warning_close_button = omni.ui.Button(
                    "×",
                    width=24,
                    height=24,
                    tooltip="Dismiss this warning message",
                    clicked_fn=self.dismiss_warning,
                    style=self._BANNER_CLOSE_STYLE,
                )
                omni.ui.Spacer(width=2)

    @classmethod
    def _banner_height(cls, message: str) -> int:
        """Return a readable banner height capped to preserve graph space."""
        line_count = max(1, message.count("\n") + 1)
        content_height = line_count * cls._BANNER_LINE_HEIGHT + cls._BANNER_PADDING
        return max(cls._BANNER_MIN_HEIGHT, min(cls._BANNER_MAX_HEIGHT, content_height))

    def show_error(self, message: str, *, log_message: bool = True) -> None:
        """Show an error banner and log only when its visible message changes."""
        if not message:
            return
        # Invalid authored material data is a user-actionable validation
        # condition, not an extension runtime failure.  Keep it visible in the
        # error framework without contaminating ETM's process-error channel.
        if log_message and message != getattr(self, "_last_logged_error_message", None):
            logger.warning("%s", message)
        self._last_logged_error_message = message
        self._error_message = message
        if self._error_label:
            self._error_label.text = message
        if self._error_frame:
            self._error_frame.height = omni.ui.Pixel(self._banner_height(message))
            self._error_frame.visible = message != getattr(self, "_dismissed_error_message", None)

    def dismiss_error(self) -> None:
        """Hide the current error banner until its message changes or the graph resets."""
        self._dismissed_error_message = self._error_message
        if self._error_frame:
            self._error_frame.visible = False
            self._error_frame.height = omni.ui.Pixel(0)

    def restore_error(self) -> None:
        """Restore the current error banner from its toolbar indicator."""
        self._dismissed_error_message = None
        if self._error_message and self._error_frame:
            self._error_frame.height = omni.ui.Pixel(self._banner_height(self._error_message))
            self._error_frame.visible = True

    def clear_error(self, *, reset_dismissal: bool = False) -> None:
        """Clear the error banner."""
        self._last_logged_error_message = None
        self._error_message = ""
        if reset_dismissal:
            self._dismissed_error_message = None
        if self._error_label:
            self._error_label.text = ""
        if self._error_frame:
            self._error_frame.visible = False
            self._error_frame.height = omni.ui.Pixel(0)

    def show_warning(self, message: str, *, log_message: bool = True) -> None:
        """Show a warning banner and log only when its visible message changes."""
        if not message:
            return
        if log_message and message != getattr(self, "_last_logged_warning_message", None):
            logger.warning("%s", message)
        self._last_logged_warning_message = message
        self._warning_message = message
        if self._warning_label:
            self._warning_label.text = message
        if self._warning_frame:
            self._warning_frame.height = omni.ui.Pixel(self._banner_height(message))
            self._warning_frame.visible = message != getattr(self, "_dismissed_warning_message", None)

    def dismiss_warning(self) -> None:
        """Hide the current warning banner until its message changes or the graph resets."""
        self._dismissed_warning_message = self._warning_message
        if self._warning_frame:
            self._warning_frame.visible = False
            self._warning_frame.height = omni.ui.Pixel(0)

    def restore_warning(self) -> None:
        """Restore the current warning banner from its toolbar indicator."""
        self._dismissed_warning_message = None
        if self._warning_message and self._warning_frame:
            self._warning_frame.height = omni.ui.Pixel(self._banner_height(self._warning_message))
            self._warning_frame.visible = True

    def clear_warning(self, *, reset_dismissal: bool = False) -> None:
        """Clear the warning banner."""
        self._last_logged_warning_message = None
        self._warning_message = ""
        if reset_dismissal:
            self._dismissed_warning_message = None
        if self._warning_label:
            self._warning_label.text = ""
        if self._warning_frame:
            self._warning_frame.visible = False
            self._warning_frame.height = omni.ui.Pixel(0)

    def _apply_error_indicator(self, result: ValidationResult) -> None:
        """Update toolbar error/warning indicator from a validation result."""
        _SOURCE_CODES = frozenset({"INVALID_CONNECTION_TYPE_MISMATCH_SOURCE"})
        primary_errors = [
            i for i in result.issues if i.severity == ValidationSeverity.ERROR and i.code not in _SOURCE_CODES
        ]
        primary_warnings = [
            i for i in result.issues if i.severity == ValidationSeverity.WARNING and i.code not in _SOURCE_CODES
        ]
        error_count = len(primary_errors)
        warning_count = len(primary_warnings)
        pending = self._get_pending_upgrade_changes()
        pending_upgrades = len(pending)
        has_any = error_count > 0 or warning_count > 0 or pending_upgrades > 0

        if self._error_indicator_frame:
            self._error_indicator_frame.visible = has_any
            self._error_indicator_frame.tooltip = ""

        if hasattr(self, "_error_badge_frame") and self._error_badge_frame:
            self._error_badge_frame.visible = error_count > 0
            if error_count > 0:
                tip = f"{error_count} Error{'s' if error_count != 1 else ''}\n"
                for issue in primary_errors[:10]:
                    tip += f"\n\n{issue.message}"
                if len(primary_errors) > 10:
                    tip += f"\n\n+{len(primary_errors) - 10} more..."
                tip += "\n\nClick to show the error banner."
                self._error_badge_frame.tooltip = tip
            else:
                self._error_badge_frame.tooltip = ""
        if self._error_count_label:
            self._error_count_label.text = str(error_count) if error_count > 0 else ""

        if hasattr(self, "_warning_badge_frame") and self._warning_badge_frame:
            self._warning_badge_frame.visible = warning_count > 0
            if warning_count > 0:
                tip = f"{warning_count} Warning{'s' if warning_count != 1 else ''}\n"
                for issue in primary_warnings[:10]:
                    tip += f"\n\n{issue.message}"
                if len(primary_warnings) > 10:
                    tip += f"\n\n+{len(primary_warnings) - 10} more..."
                tip += "\n\nClick to show the warning banner."
                self._warning_badge_frame.tooltip = tip
            else:
                self._warning_badge_frame.tooltip = ""
        if hasattr(self, "_warning_count_label") and self._warning_count_label:
            self._warning_count_label.text = str(warning_count) if warning_count > 0 else ""

        # Show upgrade indicator when there are pending upgradeable nodes
        if hasattr(self, "_upgrade_menu_frame") and self._upgrade_menu_frame:
            self._upgrade_menu_frame.visible = pending_upgrades > 0
            if pending_upgrades > 0:
                self._upgrade_menu_frame.tooltip = (
                    f"{pending_upgrades} node{'s' if pending_upgrades != 1 else ''} can be upgraded "
                    f"to current definitions. Click to review and upgrade."
                )
            else:
                self._upgrade_menu_frame.tooltip = ""

    def _get_pending_upgrade_changes(self) -> list:
        """Return pending upgrade changes from the MaterialX plugin, if any."""
        if not self._context_manager:
            return []
        try:
            from ....plugins.impl.materialx.plugin import MaterialXPlugin

            for plugin in self._context_manager.get_plugins():
                if isinstance(plugin, MaterialXPlugin):
                    return list(getattr(plugin, "_pending_upgrade_changes", []))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Discovery is best-effort: never let plugin import/iteration
            # failures break the validation indicator update path. Log so the
            # gap is observable while still returning an empty list.
            logger.warning(
                "MaterialX pending-upgrade discovery failed for material='%s' context='%s': %s; "
                "the upgrade indicator will be hidden",
                getattr(getattr(self, "model", None), "prim_path", "<none>"),
                self.current_context or "<none>",
                exc,
                exc_info=True,
            )
        return []

    def _show_upgrade_menu(self) -> None:
        """Show a popup menu listing upgradeable nodes."""
        pending = self._get_pending_upgrade_changes()
        if not pending:
            return

        if hasattr(self, "_upgrade_menu") and self._upgrade_menu is not None:
            self._upgrade_menu.hide()
        self._upgrade_menu = omni.ui.Menu("Upgrade MaterialX Nodes")

        with self._upgrade_menu:
            for change in pending:
                prim_name = change.prim_path.rsplit("/", 1)[-1] if "/" in change.prim_path else change.prim_path
                label = f"{prim_name}: {change.old_identifier} -> {change.new_identifier}"
                omni.ui.MenuItem(
                    label,
                    triggered_fn=lambda c=change: self._apply_single_upgrade(c),
                )
            if len(pending) > 1:
                omni.ui.Separator()
                omni.ui.MenuItem(
                    f"Upgrade All ({len(pending)} nodes)",
                    triggered_fn=self._apply_all_upgrades,
                )
        self._upgrade_menu.show()

    def _apply_single_upgrade(self, change) -> None:
        """Apply one upgrade from the menu and refresh the graph."""
        if not self._context_manager:
            return
        success = self._context_manager.apply_single_upgrade(change)
        if success:
            self._refresh_after_upgrade()

    def _apply_all_upgrades(self) -> None:
        """Apply all pending upgrades and refresh the graph if any succeeded."""
        pending = self._get_pending_upgrade_changes()
        if not pending or not self._context_manager:
            return
        success_count = 0
        for change in list(pending):
            try:
                if self._context_manager.apply_single_upgrade(change):
                    success_count += 1
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("MaterialX upgrade failed for %s: %s", getattr(change, "prim_path", "<unknown>"), exc)
        if success_count > 0:
            self._refresh_after_upgrade()

    def _refresh_after_upgrade(self) -> None:
        """Defer a full graph reload to the next frame after upgrading."""
        prim = self.model.prim if self.model else None
        if not prim or not prim.IsValid():
            return
        context_name = self.current_context or "mtlx"

        async def _deferred_reload():
            await omni.kit.app.get_app().next_update_async()
            if not self._context_model_controller or not prim.IsValid():
                return
            if self._context_manager:
                self._context_manager.destroy_context(context_name)
            self._context_model_controller.edit_graph(prim)
            await omni.kit.app.get_app().next_update_async()
            if self._context_model_controller and context_name:
                self._context_model_controller.set_context(context_name)

        if self._upgrade_refresh_lifecycle:
            self._upgrade_refresh_lifecycle.cleanup()
            self._upgrade_refresh_lifecycle.add_task(_deferred_reload(), label="refresh graph after upgrade")

    def apply_validation_result(self, result: ValidationResult) -> None:
        """Apply context validation state to banners and graph overlays."""
        _CONN_CODES = frozenset(
            {
                "INVALID_CONNECTION_BROKEN_SOURCE",
                "INVALID_CONNECTION_OUTSIDE_ROOT",
                "INVALID_CONNECTION_OUTSIDE_MATERIAL_ROOT",
                "INVALID_CONNECTION_OUTSIDE_CONTEXT",
                "INVALID_CONNECTION_SOURCE_ATTRIBUTE_MISSING",
                "INVALID_CONNECTION_TYPE_MISMATCH",
                "INVALID_CONNECTION_TYPE_MISMATCH_SOURCE",
            }
        )
        _NODE_CODES = frozenset(
            {
                "INVALID_NODE_DEFINITION_MISSING",
                "INVALID_NODEGRAPH_CHILDREN",
                "MIXED_NETWORK_CONTEXT",
                "CYCLICAL_NODEGRAPHS",
            }
        )
        invalid_node_paths = set()
        invalid_conn_paths = set()
        warning_node_paths = set()
        for issue in result.issues:
            if not issue.prim_path:
                continue
            if issue.severity == ValidationSeverity.ERROR:
                if issue.code in _CONN_CODES:
                    invalid_conn_paths.add(issue.prim_path)
                elif issue.code in _NODE_CODES:
                    invalid_node_paths.add(issue.prim_path)
            elif issue.severity == ValidationSeverity.WARNING:
                if issue.code in _NODE_CODES:
                    warning_node_paths.add(issue.prim_path)

        if self.model:
            self.model.set_validation_state(result.has_errors, result.has_warnings)

        conn_errors_changed = False
        if self._isolation_model:
            old_paths = self._isolation_model._invalid_connection_paths
            self._isolation_model._invalid_connection_paths = invalid_conn_paths
            self._isolation_model._warning_node_paths = warning_node_paths
            conn_errors_changed = old_paths != invalid_conn_paths

        errors_by_path = {}
        for issue in result.issues:
            if issue.severity == ValidationSeverity.ERROR and issue.prim_path:
                errors_by_path.setdefault(issue.prim_path, issue.message)
        if self._graph_view:
            self._graph_view.set_validation_errors(errors_by_path)

        self._last_validation_result = result
        self._apply_error_indicator(result)

        if self._warning_overlay:
            self._warning_overlay.visible = result.has_warnings and not result.has_errors

        error_lines = [issue.message for issue in result.issues if issue.severity == ValidationSeverity.ERROR]
        warning_lines = [issue.message for issue in result.issues if issue.severity == ValidationSeverity.WARNING]

        if error_lines:
            self.show_error("\n".join(error_lines))
        else:
            self.clear_error()

        if warning_lines and not error_lines:
            self.show_warning("\n".join(warning_lines))
        else:
            self.clear_warning()

        if conn_errors_changed and self._graph_view:
            self.request_model_refresh()

    def set_catalog_visible(self, visible: bool) -> None:
        """Set catalog panel visibility."""
        if self._splitter_left:
            self._splitter_left.set_panel_visible(visible)

    def request_model_refresh(self) -> None:
        """Request a model refresh from the graph."""
        if self.model:
            logger.debug("graph model refresh requested")
            self.model.notify_changed()
