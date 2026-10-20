"""Controller that coordinates stage-open/close lifecycle with graph widget state."""

from typing import Any, Iterable, Optional  # _event, _notice, _sender: carb/Tf/Usd types without stubs

import carb.eventdispatcher
import omni.kit.app
import omni.usd
from pxr import Sdf, Tf, Usd, UsdShade

from ....config.logging import logger
from ....utils.lifecycle_registry import LifecycleRegistry

# pylint: disable=no-member


class StageLifecycleController:
    """Manage stage lifecycle and selection sync for the widget."""

    MAX_PARENT_DEPTH = 200

    def __init__(self, widget: object, usd_context: object) -> None:
        """Initialize controller-owned state, callback wiring, and runtime dependencies."""
        self._widget = widget
        self._usd_context = usd_context
        self._event_opening = None
        self._event_opened = None
        self._listener = None
        self._lifecycle = LifecycleRegistry()
        self._deferred_lifecycle = LifecycleRegistry()
        self._pending_rename_reopen = False
        self._rename_reopen_generation = 0

    def set_visible(self, visible: bool) -> None:
        """Enable or disable stage listeners."""
        if visible:
            self._cancel_deferred_tasks(reset_widget=True)
            self._lifecycle.cleanup()
            context = self._usd_context or omni.usd.get_context()
            self._event_opening = carb.eventdispatcher.get_eventdispatcher().observe_event(
                event_name=context.stage_event_name(omni.usd.StageEventType.OPENING),
                on_event=self._on_stage_opening,
                observer_name=f"{__name__} {omni.usd.StageEventType.OPENING.name}",
            )
            self._lifecycle.add_unsubscribe(self._event_opening)
            self._event_opened = carb.eventdispatcher.get_eventdispatcher().observe_event(
                event_name=context.stage_event_name(omni.usd.StageEventType.OPENED),
                on_event=self._on_stage_opened,
                observer_name=f"{__name__} {omni.usd.StageEventType.OPENED.name}",
            )
            self._lifecycle.add_unsubscribe(self._event_opened)
            self._lifecycle.add_cleanup(self._revoke_listener)
            self._refresh_objects_listener()
        else:
            self._clear_listeners()

    def _on_stage_opening(self, _event: Any) -> None:
        """Reset widget state while a new stage is opening."""
        self._cancel_deferred_tasks()
        self._debug_reset_widget("stage_opening")
        self._revoke_listener()

    def _on_stage_opened(self, _event: Any) -> None:
        """Reset widget state after a new stage is opened."""
        self._cancel_deferred_tasks()
        self._debug_reset_widget("stage_opened")
        self._refresh_objects_listener()

    def _debug_reset_widget(self, event_name: str) -> None:
        """Reset the widget while preserving stage-event debug checkpoints."""
        if not self._widget:
            return
        self._widget.reset()

    def _on_objects_changed(self, notice: Any, _sender: Any) -> None:
        """Handle USD object change notices."""
        self._handle_objects_changed(notice)

    def _handle_objects_changed(self, notice: Optional[Any] = None) -> None:
        """Handle model selection when prims are deleted."""
        if not self._widget:
            logger.debug("objects changed ignored: widget reference is unavailable")
            return
        model = self._widget.model
        model_exists = self._model_prim_exists(model, "model")
        current_model = self._widget.current_model
        if model and not model_exists:
            if self._try_open_renamed_material(model, notice):
                return
            self._widget.reset()
            logger.debug("objects changed forced reset: current model prim no longer exists")
            return

        if not current_model:
            return

        if self._model_prim_exists(current_model, "current model"):
            return

        parent = current_model.parent
        seen = set()
        depth = 0
        while parent and depth < self.MAX_PARENT_DEPTH:
            if id(parent) in seen:
                logger.warning(
                    "selection recovery stopped: parent chain contains a cycle at model_path=%s depth=%s; "
                    "the graph will be reset",
                    getattr(parent, "prim_path", "<unknown>"),
                    depth,
                )
                break
            seen.add(id(parent))
            if self._model_prim_exists(parent, "parent model"):
                self._widget.set_current_compound(parent)
                return
            parent = parent.parent
            depth += 1
        if parent and depth >= self.MAX_PARENT_DEPTH:
            logger.warning(
                "selection recovery stopped: parent chain exceeded max_depth=%s from model_path=%s; "
                "the graph will be reset",
                self.MAX_PARENT_DEPTH,
                getattr(current_model, "prim_path", "<unknown>"),
            )

        self._widget.reset()

    @staticmethod
    def _model_prim_exists(model: object, label: str) -> bool:
        """Return whether a graph model's prim exists, treating failures as missing."""
        if not model:
            return False
        try:
            return model.prim_exists()
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
            logger.warning("objects changed %s prim_exists check failed: %s", label, exc)
            return False

    def _try_open_renamed_material(self, model: object, notice: Optional[Any]) -> bool:
        """Reload the editor when the open material was renamed in the stage."""
        old_path = self._normalize_to_sdf_path(getattr(model, "prim_path", None))
        resynced_paths = self._get_resynced_paths(notice)
        if not old_path or old_path not in resynced_paths:
            return False

        candidate = self._get_renamed_material_candidate(old_path, resynced_paths)
        if not candidate:
            return False

        logger.debug("objects changed reloaded renamed material: %s -> %s", old_path, candidate.GetPath())
        self._schedule_edit_graph(candidate)
        return True

    def _schedule_edit_graph(self, prim: Usd.Prim) -> None:
        """Open the renamed material after the current USD notice finishes dispatching."""
        if not self._deferred_lifecycle:
            return

        self._cancel_deferred_tasks()
        self._pending_rename_reopen = True
        self._rename_reopen_generation += 1
        generation = self._rename_reopen_generation

        async def _deferred_edit_graph() -> None:
            """Run graph reopening on the next app update to avoid Tf notice reentrancy."""
            try:
                await omni.kit.app.get_app().next_update_async()
                if generation != self._rename_reopen_generation:
                    return
                if not self._widget:
                    return
                if not prim or not prim.IsValid():
                    self._widget.reset()
                    return
                edit_graph = getattr(self._widget, "edit_graph", None)
                if not callable(edit_graph):
                    self._widget.reset()
                    return
                try:
                    edit_graph(prim)
                except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
                    logger.warning(
                        "deferred material rename reopen failed for prim '%s': %s; the graph will be reset",
                        prim.GetPath() if prim else "<invalid>",
                        exc,
                    )
                    self._widget.reset()
            finally:
                if generation == self._rename_reopen_generation:
                    self._pending_rename_reopen = False

        self._deferred_lifecycle.add_task(_deferred_edit_graph(), label="material rename edit graph")

    def _get_resynced_paths(self, notice: Optional[Any]) -> set:
        """Return normalized resynced paths from a USD change notice."""
        if not notice:
            return set()
        try:
            return {
                normalized_path
                for path in notice.GetResyncedPaths()
                if (normalized_path := self._normalize_to_sdf_path(path))
            }
        except (RuntimeError, ValueError, TypeError, AttributeError):
            logger.debug("rename recovery skipped: unavailable resynced paths")
            return set()

    def _get_renamed_material_candidate(self, old_path: Sdf.Path, resynced_paths: set) -> Optional[Usd.Prim]:
        """Find a selected material sibling that replaced the old path in this resync."""
        stage = self._usd_context.get_stage() if self._usd_context else None
        if not stage:
            return None

        normalized_selected_paths = set()
        for path in self._get_selected_prim_paths():
            normalized_path = self._normalize_to_sdf_path(path)
            if normalized_path:
                normalized_selected_paths.add(normalized_path)
        selected_resynced_paths = normalized_selected_paths & resynced_paths
        candidates = self._material_sibling_prims(stage, old_path, selected_resynced_paths)
        if len(candidates) == 1:
            return candidates[0]

        sibling_candidates = self._material_sibling_prims(stage, old_path, resynced_paths)
        return sibling_candidates[0] if len(sibling_candidates) == 1 else None

    def _get_selected_prim_paths(self) -> list:
        """Return selected prim paths from the current USD context."""
        if not self._usd_context:
            return []
        get_selection = getattr(self._usd_context, "get_selection", None)
        if not callable(get_selection):
            return []
        selection = get_selection()
        get_paths = getattr(selection, "get_selected_prim_paths", None) if selection else None
        if not callable(get_paths):
            return []
        return get_paths() or []

    @staticmethod
    def _normalize_to_sdf_path(path: Any) -> Optional[Sdf.Path]:
        """Return an Sdf.Path for path-like values, or None when unavailable."""
        if not path:
            return None
        if isinstance(path, Sdf.Path):
            return path
        try:
            return Sdf.Path(str(path))
        except (RuntimeError, ValueError, TypeError, AttributeError):
            return None

    def _material_sibling_prims(self, stage: Usd.Stage, old_path: Sdf.Path, paths: Iterable[Sdf.Path]) -> list:
        """Return material prims from the old material's parent, excluding the old path."""
        material_prims = []
        old_parent = old_path.GetParentPath()
        for path in paths:
            if path == old_path or path.GetParentPath() != old_parent:
                continue
            prim = stage.GetPrimAtPath(path)
            if prim and prim.IsA(UsdShade.Material):
                material_prims.append(prim)
        return material_prims

    def destroy(self) -> None:
        """Release subscriptions, callbacks, and cached references owned by this controller."""
        self._clear_listeners()
        self._cancel_deferred_tasks()
        self._deferred_lifecycle = None
        self._lifecycle = None
        self._usd_context = None
        self._widget = None

    def _clear_listeners(self) -> None:
        """Clear event listeners and subscriptions."""
        self._lifecycle.cleanup()
        self._cancel_deferred_tasks(reset_widget=True)
        self._event_opening = None
        self._event_opened = None
        self._listener = None

    def _cancel_deferred_tasks(self, reset_widget: bool = False) -> None:
        """Cancel pending deferred UI work."""
        had_pending_reopen = self._pending_rename_reopen
        if self._deferred_lifecycle:
            self._deferred_lifecycle.cleanup()
        if had_pending_reopen:
            self._rename_reopen_generation += 1
        self._pending_rename_reopen = False
        if reset_widget and had_pending_reopen and self._widget:
            self._widget.reset()

    def _revoke_listener(self) -> None:
        """Revoke the Tf notice listener."""
        if self._listener:
            self._listener.Revoke()
        self._listener = None

    def _refresh_objects_listener(self) -> None:
        """Rebind the objects-changed listener to the active stage."""
        self._revoke_listener()
        stage = self._usd_context.get_stage() if self._usd_context else None
        if not stage:
            logger.debug("objects listener not bound: USD stage is unavailable")
            return
        self._listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._on_objects_changed, stage)
