"""Implement material graph extension logic for `extension.py`."""

import logging
from types import SimpleNamespace
from typing import Dict, List, Optional, Tuple

import carb
import omni.ext
import omni.kit.app
import omni.kit.context_menu
import omni.ui
from omni.kit.menu.utils import MenuHelperExtension
from omni.kit.window.preferences import register_page as add_preferences_page
from omni.kit.window.preferences import unregister_page as remove_preferences_page

from .api.context_menu import clear_background_menu_items, clear_node_menu_items
from .commands.impl.registry import register_all_commands as setup_all_commands
from .commands.impl.registry import unregister_all_commands as teardown_all_commands
from .commands.wrappers.tasks import cleanup_command_tasks
from .config.logging import log_exception, logger
from .config.paths import Paths
from .models.catalog.registries import destroy_catalog_registries
from .preferences import MaterialGraphPreferences
from .settings.settings import Settings
from .ui.window import GraphWindow
from .utils.lifecycle_registry import LifecycleRegistry

__all__ = [
    "add_mdl_catalog_module",
    "get_extension",
    "get_graph_window",
    "remove_mdl_catalog_module",
    "show_materials",
]

# Deprecated: use get_extension() instead of the module global.
extension: Optional["GraphExtension"] = None
_extension_shutdown: bool = True
_extension_started: bool = False
_extension_registry: Dict[str, "GraphExtension"] = {}


class GraphExtension(omni.ext.IExt, MenuHelperExtension):
    """Extension entrypoint that wires startup, UI lifecycle, and API hooks."""

    _WINDOW_NAME = "Material Graph"
    _MENU_GROUP = "Window"

    def __init__(self) -> None:
        """Initialize extension runtime state and lazily-created resources."""
        super().__init__()
        self._ext_name = ""
        self._window: Optional[GraphWindow] = None
        self._stage_context_menu: Optional[object] = None
        self._thumb_context_menu: Optional[object] = None
        self._extension_subscription: Optional[object] = None
        self._preference_page: Optional[object] = None
        self._preferences_builder: Optional[MaterialGraphPreferences] = None
        self._startup_failed = False
        self._destroyed = False
        self._catalog_reload_pending = False
        self._open_graph_lifecycle: Optional[LifecycleRegistry] = None
        self._quicksearch_registration: Optional[object] = None

    def on_startup(self, ext_id: str) -> None:
        """Start the extension and register commands, menus, and preferences."""

        global extension
        global _extension_shutdown
        global _extension_started

        logger.info("startup begin")
        _extension_started = True
        self._startup_failed = False
        self._destroyed = False
        self._catalog_reload_pending = False
        _extension_shutdown = False

        try:
            self._ext_name = omni.ext.get_extension_name(ext_id)
            setup_all_commands()
            self._setup_show_window_hook()
            self._setup_stage_menu_hook()
            self._setup_preferences()
            extension = self
            _extension_registry[ext_id] = self
            logger.info("startup end")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._startup_failed = True
            log_exception(
                logger,
                "startup failed",
                ext_id=ext_id,
                action="startup",
                exc=exc,
            )
            extension = None
            _extension_shutdown = True
            self.on_shutdown()

    def on_shutdown(self) -> None:
        """Shut down extension services and release all registered resources."""
        global extension
        global _extension_shutdown
        logger.info("shutdown begin")
        self._destroyed = True
        if self._open_graph_lifecycle:
            self._run_shutdown_step("open graph lifecycle cleanup", self._open_graph_lifecycle.cleanup)
            self._open_graph_lifecycle = None

        self._run_shutdown_step("extension subscription cleanup", self._cleanup_extension_subscriptions)
        self._run_shutdown_step("quicksearch cleanup", self._unregister_quicksearch)
        self._run_shutdown_step("context menu cleanup", self._shutdown_menus)
        self._run_shutdown_step("window cleanup", self._shutdown_window)

        def _deregister_actions() -> None:
            from omni.kit.actions.core import get_action_registry

            remove_all_actions = get_action_registry().deregister_all_actions_for_extension
            remove_all_actions(Paths.MODULE_ID)

        self._run_shutdown_step("actions deregistration", _deregister_actions)
        self._run_shutdown_step("menu shutdown", self.menu_shutdown)
        self._run_shutdown_step("preferences cleanup", self._shutdown_preferences)
        self._run_shutdown_step("node menu cleanup", clear_node_menu_items)
        self._run_shutdown_step("background menu cleanup", clear_background_menu_items)
        self._run_shutdown_step("catalog registry cleanup", destroy_catalog_registries)
        self._run_shutdown_step("command task cleanup", cleanup_command_tasks)
        self._run_shutdown_step("commands deregistration", teardown_all_commands)
        self._extension_subscription = None
        extension = None
        _extension_shutdown = True
        _extension_registry.clear()
        logger.info("shutdown end")

    def _destroy_window(self) -> None:
        """Destroy the graph window instance and clear its reference."""
        if self._window:
            self._window.destroy()
        self._window = None

    def _setup_show_window_hook(self) -> None:
        """Register workspace callback used to show/hide the graph window."""
        omni.ui.Workspace.set_show_window_fn(self._WINDOW_NAME, self._show_window)
        logger.info("window show hook registered")

    def _setup_stage_menu_hook(self) -> None:
        """Register top-level menu entries and stage-extension enable hooks."""
        self.menu_startup(self._WINDOW_NAME, self._WINDOW_NAME, self._MENU_GROUP)
        logger.info("menu registered")

        app = omni.kit.app.get_app_interface()
        ext_manager = app.get_extension_manager()

        subscriptions = []
        subscriptions.append(
            ext_manager.subscribe_to_extension_enable(
                on_enable_fn=lambda _: self._setup_stage_menu(),
                on_disable_fn=lambda _: self._unregister_stage_menu(),
                ext_name="omni.kit.widget.stage",
                hook_name=self._ext_name,
            )
        )
        subscriptions.append(
            ext_manager.subscribe_to_extension_enable(
                on_enable_fn=lambda ext_id: self._on_quicksearch_extension_changed(True, ext_id),
                on_disable_fn=lambda ext_id: self._on_quicksearch_extension_changed(False, ext_id),
                ext_name="omni.kit.window.quicksearch",
                hook_name=self._ext_name,
            )
        )
        self._extension_subscription = subscriptions

        if ext_manager.is_extension_enabled("omni.kit.widget.stage"):
            self._setup_stage_menu()
        if ext_manager.is_extension_enabled("omni.kit.window.quicksearch"):
            self._register_quicksearch()

    def _setup_preferences(self) -> None:
        """Create and register the preferences page for this extension."""
        Settings.ensure_compound_paths_initialized()
        self._preferences_builder = MaterialGraphPreferences(self._WINDOW_NAME)
        self._preference_page = add_preferences_page(self._preferences_builder)
        logger.info("preferences registered")

    def _shutdown_menus(self) -> None:
        """Release stage-context menu entries."""
        self._unregister_stage_menu()

    def _shutdown_preferences(self) -> None:
        """Unregister and destroy preferences UI resources."""
        if self._preference_page:
            if self._preferences_builder:
                self._preferences_builder.destroy()
                self._preferences_builder = None
            remove_preferences_page(self._preference_page)
            self._preference_page = None

    def _shutdown_window(self) -> None:
        """Destroy the graph window and unregister workspace show hook."""
        self._destroy_window()
        omni.ui.Workspace.set_show_window_fn(self._WINDOW_NAME, None)

    def _show_window(self, visible: bool, show_startup_buttons: bool = True) -> None:
        """Show or hide the graph window, creating it lazily on first open."""
        if self._window:
            self._window.visible = visible

        elif visible:
            self._window = GraphWindow(self._WINDOW_NAME, self._ext_name, show_startup_buttons, width=600, height=800)
            self._window.set_visibility_changed_listener(self._visibility_changed_fn)
            logger.info("window created")

        self.menu_refresh()

    def _visibility_changed_fn(self, visible: bool) -> None:
        """Refresh menu state when window visibility changes."""
        if self._startup_failed:
            logger.debug("visibility change ignored: extension startup failed")
            return
        self.menu_refresh()

    def _setup_stage_menu(self) -> None:
        """Register stage and thumbnail context-menu entries for opening graph."""
        if self._stage_context_menu or self._thumb_context_menu:
            return

        def open_material(objects: dict):
            """Forward stage-context payloads to async graph opening flow."""
            self._open_material_from_context(objects)

        # add context menu to omni.kit.widget.stage
        context_menu = omni.kit.context_menu.get_instance()
        if context_menu:
            name = f"Open in {self._WINDOW_NAME}"
            # Visibility is limited to one selected prim; callback resolves
            # direct material prims and bound materials from non-material prims.
            menu = {
                "name": name,
                "glyph": "menu_material.svg",
                "show_fn": [context_menu.is_prim_selected, context_menu.is_one_prim_selected, context_menu.is_material],
                "onclick_fn": open_material,
                "appear_after": "Select Bound Objects",
            }
            self._stage_context_menu = omni.kit.context_menu.add_menu(menu, "MENU", "omni.kit.widget.stage")
            self._thumb_context_menu = omni.kit.context_menu.add_menu(
                {"name": name, "onclick_fn": open_material}, "MENU_THUMBNAIL", ""
            )
            logger.info("stage context menu registered")

    def _unregister_stage_menu(self) -> None:
        """Unregister and release stage-context menu entries."""
        if self._stage_context_menu:
            try:
                self._stage_context_menu.release()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                self._log_shutdown_exception("stage context menu", exc)
            self._stage_context_menu = None
        if self._thumb_context_menu:
            try:
                self._thumb_context_menu.release()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                self._log_shutdown_exception("thumb context menu", exc)
            self._thumb_context_menu = None

    def _cleanup_extension_subscriptions(self) -> None:
        """Release extension-manager subscriptions tracked during startup."""
        subscription = self._extension_subscription
        if not subscription:
            return
        handles = subscription if isinstance(subscription, (list, tuple)) else (subscription,)
        for handle in handles:
            if not handle:
                continue
            unsubscribe_fn = getattr(handle, "unsubscribe", None)
            if callable(unsubscribe_fn):
                try:
                    unsubscribe_fn()
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    self._log_shutdown_exception("extension subscription", exc)
                continue

            release_fn = getattr(handle, "release", None)
            if callable(release_fn):
                try:
                    release_fn()
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    self._log_shutdown_exception("extension subscription", exc)
                continue

            logger.debug(
                "extension subscription cleanup skipped: unsupported handle type %s",
                type(handle).__name__,
            )
        self._extension_subscription = None

    async def _open_graph_async(self, objects: dict) -> None:
        """Resolve a material from context payload and open it in the graph."""
        from pxr import UsdShade

        self._show_window(True, show_startup_buttons=False)

        if not any(item in objects for item in ["prim", "prim_list"]):
            logger.debug("open_graph_async skipped: payload has neither 'prim' nor 'prim_list'")
            return
        prim_list = [objects["prim"]] if "prim" in objects else objects["prim_list"]
        if not prim_list:
            logger.debug("open_graph_async skipped: resolved prim list is empty")
            return

        # Check if they are material prims, get bound materials if not
        prim_to_load = None
        for prim in prim_list:
            if prim.IsA(UsdShade.Material):
                prim_to_load = prim
                break
            api = UsdShade.MaterialBindingAPI(prim)
            material, _ = api.ComputeBoundMaterial()
            if material:
                prim_to_load = material.GetPrim()
                break

        if prim_to_load:
            self._window.open_graph(prim_to_load)

    def _open_material_from_context(self, objects: dict) -> None:
        """Open the graph for a material from a context menu payload.

        Schedule the async load since this callback may fire off the main thread.
        """

        # Create as separate task to mitigate flickering since this function can
        # run outside the main thread.
        if self._open_graph_lifecycle is None:
            self._open_graph_lifecycle = LifecycleRegistry()
        else:
            try:
                self._open_graph_lifecycle.cleanup()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                log_exception(logger, "open graph lifecycle cleanup failed", action="open_graph", exc=exc)
                self._open_graph_lifecycle = LifecycleRegistry()

        try:
            self._open_graph_lifecycle.add_task(self._open_graph_async(objects))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_exception(logger, "open graph task scheduling failed", action="open_graph", exc=exc)

    @staticmethod
    def show_materials(prim_list: List[object] = None) -> None:
        """Open the first item in prim_list in the editor."""
        instance = get_extension()
        if not instance:
            logger.debug("show_materials ignored: extension instance is unavailable")
            return

        data = {"prim_list": prim_list}
        instance._open_material_from_context(data)

    @staticmethod
    def add_node(mime_data: str) -> None:
        """Add a node to the active graph using drag/drop payload data."""
        instance = get_extension()
        if not instance or not instance._window or not instance._window.graph_widget:
            return
        x, y = GraphExtension._cursor_anchor_position()
        instance._window.graph_widget.on_drop(SimpleNamespace(mime_data=mime_data, x=x, y=y))

    @staticmethod
    def _cursor_anchor_position() -> Tuple[Optional[float], Optional[float]]:
        """Return cursor position in screen pixels."""
        try:
            import carb.input
            import omni.appwindow
        except (RuntimeError, ValueError, TypeError, AttributeError, ImportError):
            return None, None

        app_window = omni.appwindow.get_default_app_window()
        if not app_window:
            return None, None
        mouse = app_window.get_mouse() if hasattr(app_window, "get_mouse") else None
        if mouse is None:
            return None, None
        input_iface = carb.input.acquire_input_interface()
        if not input_iface:
            return None, None
        try:
            x, y = input_iface.get_mouse_coords_pixel(mouse)
            return float(x), float(y)
        except (RuntimeError, ValueError, TypeError, AttributeError):
            return None, None

    def _reload_catalog(self) -> None:
        """Reload catalog model immediately or mark reload as pending."""
        if not (self._window and self._window.graph_widget):
            self._catalog_reload_pending = True
            logger.info("catalog reload queued (no window)")
            return
        try:
            catalog_model = self._window.graph_widget.catalog_model
        except AttributeError:
            # GraphWidget is an external UI boundary in tests and startup paths.
            self._catalog_reload_pending = True
            logger.info("catalog reload queued (no catalog)")
            return
        if not catalog_model:
            self._catalog_reload_pending = True
            logger.info("catalog reload queued (no catalog)")
            return
        catalog_model.reload()
        self._catalog_reload_pending = False

    def _add_mdl_catalog_module(self, path: str) -> None:
        """Add a module path to settings and refresh catalog data."""
        Settings.add_mdl_catalog_module(path)
        self._reload_catalog()

    def _remove_mdl_catalog_module(self, path: str) -> None:
        """Remove a module path from settings and refresh catalog data."""
        Settings.remove_mdl_catalog_module(path)
        self._reload_catalog()

    @staticmethod
    def _log_shutdown_exception(context: str, exc: Exception) -> None:
        """Log shutdown failures with test-aware verbosity."""
        level = logging.WARNING
        try:
            settings = carb.settings.get_settings()
            if settings and settings.get("/app/isTestRun"):
                level = logging.INFO
        except Exception:  # pylint: disable=broad-exception-caught
            # Logging cleanup must remain safe even if settings are unavailable.
            pass
        log_exception(logger, "shutdown step failed", level=level, action=context, exc=exc)

    def _run_shutdown_step(self, context: str, callback) -> None:
        """Run one shutdown callback without preventing later cleanup steps."""
        try:
            callback()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._log_shutdown_exception(context, exc)

    def _graph_window(self) -> Optional[GraphWindow]:
        """Return the active graph window instance, if created."""
        return self._window

    def _is_window_focused(self) -> bool:
        """Return True if the material graph window exists and is focused."""
        return bool(self._window and self._window.focused)

    def _on_quicksearch_extension_changed(self, loaded: bool, _ext_id: str) -> None:
        """Handle quicksearch extension load/unload notifications."""
        if loaded:
            self._register_quicksearch()
            return
        self._unregister_quicksearch()

    def _register_quicksearch(self) -> None:
        """Register material graph quicksearch model."""
        if self._quicksearch_registration is not None:
            return
        try:
            from omni.kit.window.quicksearch import QuickSearchRegistry

            from .models.catalog import MaterialGraphQuickSearchModel
            from .ui.sections.catalog.quicksearch_delegate import MaterialGraphQuickSearchDelegate
        except (RuntimeError, ValueError, TypeError, AttributeError, ImportError) as exc:
            logger.debug("quicksearch unavailable: %s", exc)
            return
        self._quicksearch_registration = QuickSearchRegistry().register_quick_search_model(
            "Material Graph Nodes",
            MaterialGraphQuickSearchModel,
            MaterialGraphQuickSearchDelegate,
            accept_fn=self._is_window_focused,
            exclusive_fn=lambda: True,
            priority=0,
            flat_search=False,
        )

    def _unregister_quicksearch(self) -> None:
        """Unregister material graph quicksearch model."""
        if self._quicksearch_registration is None:
            return
        del self._quicksearch_registration
        self._quicksearch_registration = None


def get_graph_window() -> Optional[GraphWindow]:
    """Return the current graph window instance when the extension is active."""
    instance = get_extension()
    return instance._graph_window() if instance else None


def add_mdl_catalog_module(path: str) -> None:
    """Add an MDL module path to the catalog and trigger a reload."""
    instance = get_extension()
    if instance:
        instance._add_mdl_catalog_module(path)


def remove_mdl_catalog_module(path: str) -> None:
    """Remove an MDL module path from the catalog and trigger a reload."""
    instance = get_extension()
    if instance:
        instance._remove_mdl_catalog_module(path)


def show_materials(prim_list: List[object] = None) -> None:
    """Open the first item in prim_list in the editor."""
    instance = get_extension()
    if instance:
        instance.show_materials(prim_list)


def get_extension() -> Optional[GraphExtension]:
    """Return the current extension instance if available."""
    global extension
    if extension and not extension._destroyed:
        return extension
    if _extension_shutdown:
        if _extension_started:
            logger.warning("Material Graph extension request ignored because extension shutdown has completed")
        return None
    try:
        manager = omni.kit.app.get_app().get_extension_manager()
        ext_id = manager.get_extension_id_by_module(Paths.MODULE_ID)
    except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
        logger.debug("failed to resolve extension id for %s: %s", Paths.MODULE_ID, exc)
        ext_id = None
    if ext_id:
        instance = _extension_registry.get(ext_id)
        if instance and not instance._destroyed:
            return instance
    return None
