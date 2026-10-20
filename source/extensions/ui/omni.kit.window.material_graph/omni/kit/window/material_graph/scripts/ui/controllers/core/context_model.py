"""Controller that manages context selection and graph model switching lifecycle."""

import inspect
import logging
from typing import Optional, Union

import omni.kit.app
from pxr import Sdf, Usd, UsdShade

from ....commands.wrappers.material import CreateMaterial
from ....config.logging import log_exception, logger
from ....settings.settings import Settings
from ....utils.lifecycle_registry import LifecycleRegistry

# pylint: disable=no-member,broad-exception-caught


class ContextModelController:
    """Controls loading and switching of graph contexts."""

    def __init__(
        self,
        widget: object,
        context_switcher: object,
        context_manager: object,
        usd_context: object,
        catalog_model: object,
    ) -> None:
        """Initialize context model controller dependencies."""
        self._widget = widget
        self._context_switcher = context_switcher
        self._context_manager = context_manager
        self._usd_context = usd_context
        self._catalog_model = catalog_model
        self._default_context = Settings.get_render_context()
        self._lifecycle = LifecycleRegistry()
        self._model_changed_subscription = None
        self._validation_task = None
        self._set_current_compound_supports_refresh = None

    def open_graph(self, prim: Optional[Usd.Prim], _focus_graph_path: Optional[Sdf.Path] = None) -> None:
        """Open a graph for a prim or create a new graph."""
        if prim is None:
            self.new_graph()
            logger.debug("open_graph called without prim; creating a new graph instead")
            return
        self.edit_graph(prim)

    def new_graph(self) -> None:
        """Create a new material and open it."""
        if self._widget and hasattr(self._widget, "_solo_controller") and self._widget._solo_controller:
            self._widget._solo_controller.clear()
        result = CreateMaterial()
        if result.success and result.payload:
            self.edit_graph(result.payload)
        else:
            self.edit_graph()
        if self._widget:
            self._widget.focus_all_nodes()

    def edit_graph(self, prim: Optional[Usd.Prim] = None) -> None:
        """Edit the graph for a prim or current selection."""
        if self._widget and hasattr(self._widget, "_solo_controller") and self._widget._solo_controller:
            self._widget._solo_controller.clear()
        target_path = self._resolve_edit_target_path(prim)

        if target_path:
            if self._widget.model and self._widget.model.prim_path == target_path:
                logger.debug("edit_graph no-op: target already loaded path=%s", target_path)
                return
            if self._load_graph_for_path(target_path):
                if self.set_context(self._default_context):
                    return

        self._context_manager.clear()

    def _resolve_edit_target_path(self, prim: Optional[Usd.Prim] = None) -> Optional[Sdf.Path]:
        """Resolve edit target to a material prim path, if available."""
        stage = None
        if self._usd_context:
            get_stage = getattr(self._usd_context, "get_stage", None)
            if callable(get_stage):
                stage = get_stage()
        if prim is None:
            selection = []
            if self._usd_context:
                get_selection = getattr(self._usd_context, "get_selection", None)
                if callable(get_selection):
                    selection_obj = get_selection()
                    if selection_obj:
                        get_paths = getattr(selection_obj, "get_selected_prim_paths", None)
                        if callable(get_paths):
                            selection = get_paths() or []
            if not selection:
                return None
            selected_path = selection[0]
            if stage:
                prim = stage.GetPrimAtPath(selected_path)
            else:
                return Sdf.Path(str(selected_path))

        if not prim or not prim.IsValid():
            return None
        if prim.IsA(UsdShade.Material):
            return prim.GetPath()

        bound_prim = None
        try:
            material, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
            if material:
                bound_prim = material.GetPrim()
        except (RuntimeError, ValueError, TypeError, AttributeError):
            bound_prim = None

        if bound_prim and bound_prim.IsValid():
            return bound_prim.GetPath()

        logger.debug("edit_graph ignored: non-material selection path=%s", prim.GetPath())
        return None

    def _load_graph_for_path(self, target_path: Union[Sdf.Path, str]) -> bool:
        """Load graph data for a USD path."""
        if self._context_manager.load(Sdf.Path(str(target_path))):
            return True
        get_last_error = getattr(self._context_manager, "get_last_error", None)
        detail = get_last_error() if callable(get_last_error) else None
        suffix = f": {detail}" if detail else ""
        message = f"context load failed for {target_path}{suffix}"
        self._widget.show_error(message, log_message=False)
        return False

    def set_context(self, context_name: str, *, log_errors: bool = True) -> bool:
        """Activate a context and update widget state."""
        previous_context = self._widget.current_context
        previous_model = self._widget.model
        previous_active = previous_model.active if previous_model else None
        previous_isolation = previous_model.isolation_model if previous_model else None
        if previous_context != context_name:
            logger.debug(
                "context switch: %s -> %s",
                previous_context or "<none>",
                context_name,
            )

        check_upgrade = getattr(self._context_manager, "check_materialx_upgrade", None)
        if callable(check_upgrade):
            try:
                check_upgrade(context_name)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                # Upgrade discovery is a best-effort pre-step; never let it
                # short-circuit the context switch (we still need the normal
                # switch/restore error handling below to run).
                logger.warning("MaterialX upgrade check failed for '%s': %s", context_name, exc)

        handle = self._context_manager.get_context(context_name)
        if not handle.is_valid:
            detail = handle.error or "context was not created"
            message = f"context '{context_name}' unavailable: {detail}"
            self._widget.show_error(message)
            return False

        if self._widget.current_context == context_name and self._widget.model is handle.context.model:
            self._widget.request_model_refresh()
            self._schedule_validation(context_name)
            return True

        try:
            if previous_model:
                previous_model.isolation_model = None
                previous_model.active = False
            self._widget.model = handle.context.model
            self._widget.model.active = True
            self._set_current_compound_without_refresh(handle.context.model)

            self._widget.current_context = context_name
            # Wire InputNode view model context info (Phase 1)
            gv = getattr(self._widget, "_graph_view", None) or getattr(self._widget, "graph_view", None)
            if gv and hasattr(gv, "set_input_node_context"):
                gv.set_input_node_context(self._context_manager, context_name)
            if hasattr(self._catalog_model, "set_current_context"):
                self._catalog_model.set_current_context(context_name)
            self._catalog_model.set_discovery_plugin(handle.plugin)
            self._widget.update_style()
            self._widget.set_toolbar_items(self._widget.get_toolbar_items(bool(self._widget.model)))
            self._context_switcher.refresh_tabs()
            self._bind_model_listener(self._widget.model)
            self._schedule_validation(context_name)
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:  # pylint: disable=broad-exception-caught
            if log_errors:
                log_exception(
                    logger,
                    "failed to apply context",
                    level=logging.ERROR,
                    context_name=context_name,
                    exc=exc,
                )
            else:
                logger.warning("context apply failed; details suppressed context_name=%s", context_name)
            self._widget.show_error(
                f"context '{context_name}' could not be applied; see the preceding log entry for details",
                log_message=False,
            )
            self._restore_context(previous_context, previous_model, previous_isolation, previous_active)
            self._bind_model_listener(previous_model)
            self._widget.request_model_refresh()
            return False
        logger.debug("context switch applied: %s", context_name)
        return True

    def _set_current_compound_without_refresh(self, model: object) -> None:
        """Set the current compound without forcing a redundant full refresh when supported."""
        setter = self._widget.set_current_compound
        if self._set_current_compound_supports_refresh is None:
            try:
                signature = inspect.signature(setter)
            except (TypeError, ValueError):
                signature = None
            self._set_current_compound_supports_refresh = bool(
                signature
                and (
                    "refresh" in signature.parameters
                    or any(
                        parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values()
                    )
                )
            )
        if self._set_current_compound_supports_refresh:
            setter(model, True, refresh=False)
        else:
            self._widget.set_current_compound(model, True)

    def _unsubscribe_model_listener(self) -> None:
        """Detach active model change listener if present."""
        subscription = self._model_changed_subscription
        if not subscription:
            return
        self._model_changed_subscription = None
        try:
            subscription.unsubscribe()
        except AttributeError:
            try:
                subscription.release()
            except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
                logger.debug("model listener cleanup skipped: %s", exc)
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
            logger.debug("model listener cleanup skipped: %s", exc)

    def _bind_model_listener(self, model: Optional[object]) -> None:
        """Bind to model changes so validation can run after edits."""
        self._unsubscribe_model_listener()
        if not model:
            return
        try:
            self._model_changed_subscription = model.subscribe_item_changed(self._on_model_item_changed)
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
            logger.warning(
                "failed to bind graph-model change listener for context='%s' root='%s': %s; "
                "automatic validation after edits is unavailable",
                getattr(self._widget, "current_context", None) or "<none>",
                getattr(model, "prim_path", "<unknown>"),
                exc,
            )
            self._model_changed_subscription = None

    def _on_model_item_changed(self, item: Optional[object] = None) -> None:
        """Schedule validation after edits mutate the active graph."""
        if not self._widget:
            return
        model = self._widget.model
        consume_position_change = getattr(model, "consume_position_only_validation_changed", None)
        if callable(consume_position_change) and consume_position_change(item):
            return
        if not self._widget.current_context:
            return
        self._schedule_validation(self._widget.current_context)

    def _schedule_validation(self, context_name: str) -> None:
        """Coalesce context validation onto the next update tick."""

        async def _run_validation() -> None:
            """Run per-context validation and apply the result to UI state."""
            await omni.kit.app.get_app().next_update_async()
            if not self._widget or self._widget.current_context != context_name:
                return
            result = self._context_manager.validate_context(context_name)
            self._widget.apply_validation_result(result)

        if self._validation_task and not self._validation_task.done():
            self._validation_task.cancel()
        if self._lifecycle:
            self._validation_task = self._lifecycle.add_task(
                _run_validation(),
                label=f"context validation: {context_name}",
            )

    def _restore_context(
        self,
        previous_context: Optional[str],
        previous_model: Optional[object],
        previous_isolation: Optional[object],
        previous_active: Optional[bool],
    ) -> None:
        """Restore widget state after a failed context switch."""
        self._widget.model = previous_model
        self._widget.current_context = previous_context
        if previous_model:
            previous_model.isolation_model = previous_isolation
            if previous_active is not None:
                previous_model.active = previous_active

    def destroy(self) -> None:
        """Release internal references so the controller can be garbage collected safely."""
        self._unsubscribe_model_listener()
        if self._lifecycle:
            self._lifecycle.cleanup()
        self._lifecycle = None
        self._validation_task = None
        self._catalog_model = None
        self._context_switcher = None
        self._context_manager = None
        self._usd_context = None
        self._widget = None
