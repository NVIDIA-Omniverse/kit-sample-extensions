"""Context-visibility controller — persistent multi-select menu."""

from functools import partial
from typing import List, Optional, Sequence, Tuple, Union

import carb.input
import omni.appwindow
import omni.kit.app
import omni.ui
from pxr import Sdf, Usd, UsdShade, UsdUI

from ....api.context_menu import add_node_menu_item, remove_node_menu_item
from ....commands.wrappers.attributes import SetPrimCustomData
from ....config.logging import logger
from ....settings.settings import Settings
from ....utils.context_visibility import get_context_visibility
from ....utils.lifecycle_registry import LifecycleRegistry

# pylint: disable=no-member,protected-access


class ContextVisibilityController:
    """Manages per-context visibility metadata for prims."""

    def __init__(self, widget: object) -> None:
        self._widget = widget
        self._menu = None
        self._menu_callbacks = []
        self._lifecycle = LifecycleRegistry()
        self._active_prim = None
        self._cb_models = {}

    # -- menu registration ---------------------------------------------------

    def setup_menu_items(self) -> None:
        self._menu_callbacks = []
        for node_type in ("NodeGraph", "Backdrop"):

            def _make(nt=node_type):
                def _cb(_ntn, prim_path):
                    self.show_menu(prim_path)

                return _cb

            cb = _make()
            self._menu_callbacks.append((node_type, cb))
            add_node_menu_item("Context Visibility...", cb, node_types=node_type)

    def unregister_menu_items(self) -> None:
        for nt, cb in self._menu_callbacks:
            remove_node_menu_item("Context Visibility...", cb)
        self._menu_callbacks = []

    # -- prim helpers --------------------------------------------------------

    def apply_to_prim(self, prim: object) -> None:
        prim = self._normalize_prim(prim)
        if not prim:
            return
        if prim.IsA(UsdShade.NodeGraph):
            if not Settings.confine_nodegraphs():
                return
        elif prim.IsA(UsdUI.Backdrop):
            if not Settings.confine_backdrops():
                return
        else:
            return
        if not self._widget.current_context:
            return
        self._set_context_visibility(prim, self._widget.current_context)

    # -- popup ---------------------------------------------------------------

    @property
    def is_open(self) -> bool:
        return self._menu is not None

    def close(self) -> None:
        if self._menu:
            self._menu.hide()
            self._menu = None
        self._active_prim = None
        self._cb_models = {}

    def show_menu(self, prim_path: Union[Sdf.Path, str]) -> None:
        if not prim_path or not self._widget.model:
            return
        path = Sdf.Path(str(prim_path)) if not isinstance(prim_path, Sdf.Path) else prim_path
        prim = self._widget.model.stage.GetPrimAtPath(path)
        if not prim:
            return

        self.close()
        self._active_prim = prim

        contexts = self._get_contexts()
        all_contexts = [cn for cn, _ in contexts]
        visibility = self._get_context_visibility(prim)
        visibility = self._normalize_visibility(visibility)
        is_all = visibility is None

        menu = omni.ui.Menu("Context Visibility")
        self._menu = menu
        self._cb_models = {}

        with menu:
            for ctx_name, display_name in contexts:
                active = is_all or (ctx_name in (visibility or []))
                omni.ui.MenuItem(
                    display_name,
                    checkable=True,
                    checked=active,
                    hide_on_click=False,
                    triggered_fn=partial(self._on_toggle, prim, ctx_name, all_contexts),
                )

        async def _show():
            await omni.kit.app.get_app().next_update_async()
            if not self._menu:
                return
            app_window = omni.appwindow.get_default_app_window()
            iface = carb.input.acquire_input_interface()
            if app_window and iface:
                sx, sy = iface.get_mouse_coords_pixel(app_window.get_mouse())
                dpi = omni.ui.Workspace.get_dpi_scale()
                self._menu.show_at(int(sx / dpi), int(sy / dpi))
            else:
                self._menu.show()

        self._lifecycle.add_task(_show())

    def _on_toggle(self, prim, ctx_name, all_contexts):
        """Handle a checkbox toggle."""
        vis = self._get_context_visibility(prim)
        current = self._visibility_set(vis, all_contexts)

        if ctx_name in current:
            if len(current) <= 1:
                return
            current.discard(ctx_name)
        else:
            current.add(ctx_name)

        final = None if current == set(all_contexts) else sorted(current)
        self._set_context_visibility(prim, final)

    # -- data layer ----------------------------------------------------------

    @staticmethod
    def _get_context_visibility(prim):
        return get_context_visibility(prim)

    def _set_context_visibility(self, prim, visibility):
        updated_custom_data = dict(prim.GetCustomData() or {})
        updated_custom_data.pop("omni:ui:contextVisibility", None)
        legacy_ui_data = updated_custom_data.pop("omni:ui", None)
        omni_data = updated_custom_data.get("omni")
        omni_data = dict(omni_data) if isinstance(omni_data, dict) else {}
        ui_data = omni_data.get("ui")
        ui_data = dict(ui_data) if isinstance(ui_data, dict) else {}
        if isinstance(legacy_ui_data, dict):
            ui_data.update(legacy_ui_data)
        if not visibility:
            ui_data.pop("contextVisibility", None)
        else:
            normalized = [visibility] if isinstance(visibility, str) else list(visibility)
            ui_data["contextVisibility"] = normalized
        if ui_data:
            omni_data["ui"] = ui_data
        else:
            omni_data.pop("ui", None)
        if omni_data:
            updated_custom_data["omni"] = omni_data
        else:
            updated_custom_data.pop("omni", None)
        result = SetPrimCustomData(prim, updated_custom_data)
        if not result.success:
            message = result.message or "context visibility update failed"
            logger.warning("context visibility update failed on %s: %s", prim.GetPath(), message)
            if self._widget:
                self._widget.show_error(message, log_message=False)
            return False
        if self._widget:
            self._widget.request_model_refresh()
        return True

    def _toggle_context_visibility(self, prim, context_name, all_contexts):
        self._on_toggle(prim, context_name, all_contexts)

    @staticmethod
    def _normalize_visibility(visibility):
        """Return a normalized visibility list, or None for unrestricted visibility."""
        if visibility is None:
            return None
        if isinstance(visibility, str):
            visibility = [visibility]
        normalized = [str(item) for item in visibility if item]
        return normalized or None

    @classmethod
    def _visibility_set(cls, visibility, all_contexts):
        """Return visibility as a set, treating missing/empty visibility as all contexts."""
        normalized = cls._normalize_visibility(visibility)
        return set(normalized if normalized is not None else all_contexts)

    def _get_contexts(self) -> List[Tuple[str, str]]:
        contexts = []
        manager = self._widget._context_manager if self._widget else None
        if manager:
            for plugin in manager.get_plugins():
                contexts.append((plugin.name, plugin.display_name))
        if self._widget and self._widget.current_context:
            existing = {n for n, _ in contexts}
            if self._widget.current_context not in existing:
                contexts.append((self._widget.current_context, self._widget.current_context))
        return contexts

    @staticmethod
    def _normalize_prim(prim):
        if not prim:
            return None
        if isinstance(prim, bool):
            return None
        if isinstance(prim, (list, tuple)):
            for item in prim:
                r = ContextVisibilityController._normalize_prim(item)
                if r:
                    return r
            return None
        if not isinstance(prim, Usd.Prim):
            return None
        return prim

    def destroy(self):
        self.unregister_menu_items()
        self.close()
        if self._lifecycle:
            self._lifecycle.cleanup()
            self._lifecycle = None
        self._menu = None
        self._menu_callbacks = []
        self._widget = None
