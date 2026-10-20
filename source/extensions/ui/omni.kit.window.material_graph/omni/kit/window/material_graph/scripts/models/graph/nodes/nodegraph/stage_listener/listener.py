"""USD stage listener that batches dirty-notice updates into graph model syncs."""

import asyncio
import time
from typing import Any, Dict, Optional, Set

import omni.kit.app
from pxr import Sdf, Tf, Usd, UsdShade, UsdUI

from ......config.logging import logger
from ......utils.lifecycle_registry import LifecycleRegistry


class StageListener:
    """Listens to USD stage changes and updates the graph model."""

    MAX_DIRTY_PATHS = 2000
    INFO_PROP_SYNC_UPDATES = 5
    CONNECTION_ONLY_DEDUPE_WINDOW_SEC = 0.15

    def __init__(self, model: Any, stage: Usd.Stage, info_sync_updates: Optional[int] = None) -> None:
        """Initialize listener state, dirty-path queues, and Tf notice registration."""
        self._model = model
        self._stage = stage
        self._lifecycle = LifecycleRegistry()

        self._prim_path = self._model.prim_path
        self._dirty_prim_paths = set()
        self._dirty_prop_paths = set()
        self._task = None
        self._info_sync_updates = info_sync_updates or self.INFO_PROP_SYNC_UPDATES

        self._ignored_paths: set = set()
        self._recent_connection_only_props: dict[str, float] = {}
        self._recent_connection_signatures: dict[str, tuple] = {}
        self._diag_notice_perf: Optional[float] = None
        self._force_full_refresh = False
        self._listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._on_objects_changed, self._stage)
        self._lifecycle.add_cleanup(self._unregister_listener)

    def destroy(self) -> None:
        """Release lifecycle resources, cancel pending tasks, and clear references."""
        self._lifecycle.cleanup()
        self._model = None
        self._task = None
        self._listener = None
        self._ignored_paths = set()
        self._recent_connection_only_props = {}
        self._recent_connection_signatures = {}
        self._force_full_refresh = False

    def _revoke_listener(self) -> None:
        """Revoke the active Tf.Notice listener handle when present."""
        if self._listener:
            self._listener.Revoke()

    def _unregister_listener(self) -> None:
        """Unregister listener callback from Tf.Notice."""
        self._revoke_listener()

    def add_ignored_paths(self, paths) -> None:
        """Add attribute paths that the listener should ignore (e.g. session layer solo edits)."""
        self._ignored_paths.update(Sdf.Path(p) if not isinstance(p, Sdf.Path) else p for p in paths)

    def remove_ignored_paths(self, paths) -> None:
        """Remove attribute paths from the ignore set."""
        for p in paths:
            self._ignored_paths.discard(Sdf.Path(p) if not isinstance(p, Sdf.Path) else p)

    def _on_objects_changed(self, notice: Usd.Notice.ObjectsChanged, sender: Usd.Stage) -> None:
        """Collect changed prim/property paths and schedule deferred model updates."""
        prims_changed, props_changed = self._collect_changed_paths(notice)
        if self._ignored_paths:
            props_changed = {p for p in props_changed if p not in self._ignored_paths}

        if not prims_changed and not props_changed:
            return

        if any(prop.name.startswith("info:") for prop in props_changed):
            prims_changed.add(self._prim_path)
        self._diag_notice_perf = time.perf_counter()
        self._record_dirty_paths(prims_changed, props_changed)
        self._ensure_delayed_task()

    def _collect_changed_paths(self, notice: Usd.Notice.ObjectsChanged) -> tuple[Set[Sdf.Path], Set[Sdf.Path]]:
        """Collect prim/property paths from resync and info-only notice sets."""
        prims_changed: Set[Sdf.Path] = set()
        props_changed: Set[Sdf.Path] = set()
        resynced_paths = set(notice.GetResyncedPaths())
        for path in resynced_paths:
            if path.IsAbsoluteRootOrPrimPath():
                prims_changed.add(path)
            if path.IsPropertyPath():
                props_changed.add(path)
        changed_paths = set(notice.GetChangedInfoOnlyPaths())
        for path in changed_paths:
            if path.IsAbsoluteRootOrPrimPath():
                prims_changed.add(path)
                changed_fields = notice.GetChangedFields(path) or []
                if any(str(field).startswith("customData") for field in changed_fields):
                    props_changed.add(path.AppendProperty("customData"))
            if path.IsPropertyPath():
                props_changed.add(path)
        return prims_changed, props_changed

    def _record_dirty_paths(self, prims_changed: Set[Sdf.Path], props_changed: Set[Sdf.Path]) -> None:
        """Merge dirty paths into listener state with overflow guard."""
        self._dirty_prim_paths = self._dirty_prim_paths.union(prims_changed)
        self._dirty_prop_paths = self._dirty_prop_paths.union(props_changed)
        if len(self._dirty_prim_paths) > self.MAX_DIRTY_PATHS:
            self._force_full_refresh = True
            self._dirty_prim_paths = {self._prim_path}
        if len(self._dirty_prop_paths) > self.MAX_DIRTY_PATHS:
            self._force_full_refresh = True
            self._dirty_prop_paths.clear()

    def _ensure_delayed_task(self) -> None:
        """Ensure there is one active delayed processing task."""
        if self._task is None or self._task.done():
            self._task = self._lifecycle.add_task(
                self._delayed_prim_changed(), label=f"stage listener {self._prim_path}"
            )

    async def _delayed_prim_changed(self) -> None:
        """Process queued dirty paths on subsequent frame ticks to batch updates."""
        try:
            await omni.kit.app.get_app().next_update_async()
            if not self._model:
                logger.debug("delayed prim change skipped: model was destroyed before deferred update")
                return

            prim_paths = set(self._dirty_prim_paths)
            self._dirty_prim_paths.clear()
            prop_paths = set(self._dirty_prop_paths)
            self._dirty_prop_paths.clear()
            force_full_refresh = self._force_full_refresh
            self._force_full_refresh = False

            if any(path.name.startswith("info:") for path in prop_paths):
                for _ in range(self._info_sync_updates):
                    await omni.kit.app.get_app().next_update_async()

            self._update_dirty(prim_paths, prop_paths, force_full_refresh=force_full_refresh)
        finally:
            self._task = None
            if self._model and (self._dirty_prim_paths or self._dirty_prop_paths or self._force_full_refresh):
                self._ensure_delayed_task()

    def _update_dirty(
        self,
        prim_paths: Set[Sdf.Path],
        prop_paths: Set[Sdf.Path],
        *,
        force_full_refresh: bool = False,
    ) -> None:
        """Update the model for dirty prim and property paths."""
        if not self._model:
            logger.debug("update_dirty skipped: model is unavailable")
            return
        if force_full_refresh:
            self._notify_changed(None, reason="dirty_overflow")
            return
        rebuild_prim_paths = set()
        if self._process_prim_changes(prim_paths):
            return
        if self._collect_rebuild_paths(prop_paths, rebuild_prim_paths):
            return

        for prim_path in rebuild_prim_paths:
            item = self._model.get_item_model(prim_path)
            if item:
                self._notify_changed(item, reason="node_rebuild")
                try:
                    self._model._rebuild_node(item)
                except KeyError as exc:
                    logger.debug("rebuild skipped: missing node for %s (%s)", prim_path, exc)

    def _notify_changed(self, item=None, reason: str = "unspecified") -> None:
        """Notify the root model that an item changed.

        The isolation model (if any) receives the notification
        automatically via its subscription to the root model's
        item-changed event.
        """
        self._model._item_changed(item)

    def _is_in_model_hierarchy(self, path: Sdf.Path) -> bool:
        """Return True when path belongs to current model hierarchy."""
        return path == self._prim_path or self._prim_path in path.GetPrefixes()

    def _process_prim_changes(self, prim_paths: Set[Sdf.Path]) -> bool:
        """Process dirty prim paths. Return True when caller should stop."""
        for prim_path in prim_paths:
            prim = self._stage.GetPrimAtPath(prim_path)
            if not self._is_in_model_hierarchy(prim_path):
                if self._prim_path.HasPrefix(prim_path) and not prim:
                    self._notify_changed(None, reason="ancestor_removed")
                    return True
                continue
            if prim:
                if self._ensure_child_model_for_prim(prim_path, prim):
                    return True
            else:
                if self._remove_child_model_for_prim(prim_path):
                    return True
        return False

    def _ensure_child_model_for_prim(self, prim_path: Sdf.Path, prim: Usd.Prim) -> bool:
        """Ensure item model exists for prim. Return True when full refresh is required."""
        if self._model.get_item_model(prim_path):
            return False
        parent_path = prim_path.GetParentPath()
        parent_model = self._model.get_item_model(parent_path)
        if parent_model and parent_model.create_child(prim):
            self._notify_changed(None, reason="child_created")
            return True
        if not parent_model:
            logger.warning("stage listener skipped create_child: missing parent model for %s", prim_path)
        return False

    def _remove_child_model_for_prim(self, prim_path: Sdf.Path) -> bool:
        """Remove child model for deleted prim and request refresh."""
        parent_path = prim_path.GetParentPath()
        parent_model = self._model.get_item_model(parent_path)
        if parent_model:
            parent_model.remove_child(prim_path)
        self._notify_changed(None, reason="child_removed")
        return True

    def _collect_rebuild_paths(self, prop_paths: Set[Sdf.Path], rebuild_prim_paths: Set[Sdf.Path]) -> bool:
        """Collect prims requiring rebuild. Return True when caller should stop."""
        rebuild_property_names = {
            UsdUI.Tokens.uiNodegraphNodeDisplayColor,
            UsdUI.Tokens.uiDescription,
            UsdUI.Tokens.uiNodegraphNodeSize,
        }
        for prop_path in prop_paths:
            prim_path = prop_path.GetParentPath()
            if not self._is_in_model_hierarchy(prim_path):
                continue
            if prop_path.name == UsdUI.Tokens.uiNodegraphNodePos:
                self._update_position_only(prim_path)
                continue
            if prop_path.name in rebuild_property_names:
                rebuild_prim_paths.add(prim_path)
                continue
            if prop_path.name == UsdUI.Tokens.uiNodegraphNodeStackingOrder or prop_path.name.startswith("info:"):
                self._notify_changed(None, reason="ui_stack_or_info")
                return True
            if prop_path.name == "customData" and prim_path == self._prim_path:
                # Root customData updates (e.g. per-context IO position writes)
                # are already applied directly by position commands and do not
                # require an additional model-wide refresh.
                continue
            if prop_path.name == "paused":
                continue
            attribute = self._stage.GetAttributeAtPath(prop_path)
            if not attribute:
                self._notify_changed(None, reason="missing_attribute")
                return True
            if UsdShade.Input.IsInput(attribute) or UsdShade.Output.IsOutput(attribute):
                if not attribute.GetConnections() and self._has_authored_connection_paths(prop_path):
                    # A weaker layer still has sources that composition has not
                    # caught up with (typical immediately after undo). A stage
                    # listener is read-only: defer to a full refresh and never
                    # author an explicit empty list from inside a notice.
                    self._notify_changed(None, reason="stale_connection_composition")
                    return True
                if self._is_duplicate_connection_only_prop(prop_path, attribute):
                    continue
                self._update_connection_only(prop_path)
                continue
        return False

    def _has_authored_connection_paths(self, prop_path: Sdf.Path) -> bool:
        """Return whether any layer in the stage stack authors positive sources."""
        try:
            layers = self._stage.GetLayerStack(includeSessionLayers=True)
        except TypeError:
            layers = self._stage.GetLayerStack()
        for layer in layers:
            spec = layer.GetAttributeAtPath(prop_path)
            if not spec:
                continue
            connection_paths = spec.connectionPathList
            for accessor in ("GetAddedOrExplicitItems", "GetPrependedItems", "GetAppendedItems"):
                get_items = getattr(connection_paths, accessor, None)
                if callable(get_items) and get_items():
                    return True
        return False

    @staticmethod
    def _connection_signature(attribute: Usd.Attribute) -> Optional[tuple]:
        """Return a stable signature of current authored connections for dedupe."""
        get_connections = getattr(attribute, "GetConnections", None)
        if not callable(get_connections):
            return None
        try:
            connections = get_connections() or []
        except (RuntimeError, ValueError, TypeError, AttributeError):
            return None
        return tuple(sorted(str(path) for path in connections))

    def _is_duplicate_connection_only_prop(self, prop_path: Sdf.Path, attribute: Usd.Attribute) -> bool:
        """Return True when a connection-only prop was already handled recently."""
        now = time.perf_counter()
        cutoff = now - self.CONNECTION_ONLY_DEDUPE_WINDOW_SEC
        if self._recent_connection_only_props:
            stale = [path for path, ts in self._recent_connection_only_props.items() if ts < cutoff]
            for path in stale:
                del self._recent_connection_only_props[path]
                self._recent_connection_signatures.pop(path, None)
        prop_key = str(prop_path)
        signature = self._connection_signature(attribute)
        prev = self._recent_connection_only_props.get(prop_key)
        prev_sig = self._recent_connection_signatures.get(prop_key)
        self._recent_connection_only_props[prop_key] = now
        if signature is not None:
            self._recent_connection_signatures[prop_key] = signature
        is_dup = prev is not None and prev >= cutoff and signature is not None and prev_sig == signature
        return is_dup

    def _update_position_only(self, prim_path: Sdf.Path) -> None:
        """Refresh cached node position and emit a lightweight position-only notification."""
        item = self._model.get_item_model(prim_path)
        if not item:
            return
        sync_position = getattr(item, "sync_position", None)
        if callable(sync_position):
            sync_position()
        notifier = getattr(self._model, "notify_position_changed", None)
        if callable(notifier):
            notifier(item)
        else:
            self._notify_changed(item, reason="position_only_fallback")

    def _update_connection_only(self, prop_path: Sdf.Path) -> None:
        """Refresh one port's connection cache and emit a lightweight notification."""
        item = self._model.get_item_model(prop_path)
        if not item:
            notifier = getattr(self._model, "notify_connection_changed", None)
            if callable(notifier):
                notifier(None)
            else:
                self._notify_changed(None, reason="connection_missing_item")
            return
        sync = getattr(item, "sync", None)
        if callable(sync):
            sync()
        notifier = getattr(self._model, "notify_connection_changed", None)
        if callable(notifier):
            notifier(item)
        else:
            self._notify_changed(item, reason="connection_only_fallback")
