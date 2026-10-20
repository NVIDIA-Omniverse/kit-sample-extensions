"""Implement material graph extension logic for `models/graph/nodes/nodegraph/model.py`."""

from typing import Any, Callable, List, Optional, Sequence, Tuple, Union

import omni.kit.app
import omni.kit.undo
from omni.kit.widget.graph import GraphModelBatchPositionHelper
from pxr import Sdf, Usd, UsdShade, UsdUI

from .....config.logging import logger
from .....utils.lifecycle_registry import LifecycleRegistry
from .....utils.sdr_wrappers import mdl_type_polymorphic_constraint_score
from .....utils.usd_names import strip_usd_namespace
from ...ports import (
    AttributeGroupModel,
    AttributeModel,
    InputAttributeGroupModel,
    InputAttributeModel,
    OutputAttributeGroupModel,
    OutputAttributeModel,
)
from ..backdrop import BackdropModel
from ..prim.model import PrimModel
from ..prim.position_mixin import PositionMixin
from ..shader import ShaderModel
from .backdrop_stacking import BackdropStackingCalculator
from .child_resolver import NodeGraphChildResolver
from .position.resolver import PositionItemResolver
from .position.transaction import PositionMoveTransaction
from .selection_adapter import SelectionAdapter
from .selection_moving_getter import SelectionMovingGetter
from .stage_listener.manager import StageListenerManager

# pylint: disable=no-member,protected-access,unused-argument


class NodeGraphModel(PositionMixin, PrimModel, GraphModelBatchPositionHelper):
    """Prim model for nodegraphs and material contexts."""

    INPUT = "input"
    OUTPUT = "output"

    def __init__(
        self,
        prim: Usd.Prim,
        context_name: str,
        usd_context: Any,
        plugin: Any,
        parent: Any,
        schema_type: Any = UsdShade.NodeGraph,
        sync: bool = True,
    ) -> None:
        """Initialize child/cache/listener state for a nodegraph or material-root model."""
        self._children = {}
        self._is_active = False
        self._selection_adapter = SelectionAdapter(usd_context)
        self._input_output_position = [None, None]
        self._backdrop_stacking_cache = {}
        self._backdrop_stacking_signature = None
        self._lifecycle = LifecycleRegistry()
        self._stage_listener_manager = StageListenerManager(self, self._lifecycle)
        self._backdrop_calculator = BackdropStackingCalculator()
        self._child_resolver = NodeGraphChildResolver(self)
        self._is_context_root = schema_type == UsdShade.Material
        self._position_txn = PositionMoveTransaction()
        self._position_item_resolver = PositionItemResolver(self)
        self._selected_items: List[Any] = []
        self._suppress_next_none_item_changed = False
        self._suppress_next_selection_run_select = False
        self._child_ports_dirty = False
        self._position_only_sync_skip_items = {}
        self._position_only_view_items = {}
        self._position_only_validation_items = {}
        self._connection_only_sync_skip_items = {}
        self._connection_visual_sync_cb: Optional[Callable[[Any], None]] = None
        self._skip_next_activation_sync = False
        self._synced_once = False
        self._cached_child_resolver_paths: Optional[Tuple[Sdf.Path, ...]] = None

        super().__init__(prim, context_name, usd_context, plugin, parent, schema_type, sync)
        self._selection_getter_sub = self.add_get_moving_items_fn(SelectionMovingGetter(self))

    def destroy(self) -> None:
        """Destroy children and release listeners."""
        self._connection_visual_sync_cb = None
        self._force_commit_staged_positions()
        self._clear_stage_listeners()
        if self._lifecycle:
            self._lifecycle.cleanup()
            self._lifecycle = None
        self._selection_adapter = None
        self._cached_child_resolver_paths = None
        self._child_resolver = None
        self._backdrop_calculator = None
        self._selection_getter_sub = None
        self._selected_items = []
        self._position_only_sync_skip_items.clear()
        self._position_only_view_items.clear()
        self._position_only_validation_items.clear()
        if self._children:
            for model in self._children.values():
                model.destroy()
            self._children.clear()
        super().destroy()

    def get_prim_model(self, item: Any) -> Optional[Any]:
        """Resolve a cached child model by prim path key."""
        child = self._children.get(item, None)
        if child:
            return child

    def clear(self) -> None:
        """Destroy child models and reset selection/backdrop caches to empty state."""
        self._synced_once = False
        self._skip_next_activation_sync = False
        self._cached_child_resolver_paths = None
        if self._children:
            for model in self._children.values():
                model.destroy()
        self._children.clear()
        self._position_only_sync_skip_items.clear()
        self._position_only_view_items.clear()
        self._position_only_validation_items.clear()
        self._clear_backdrop_cache()
        if self._selection_adapter:
            self._selection_adapter.clear()
        super().clear()

    @PrimModel.inputs.setter
    def inputs(self, value: Any, item: Optional[Any] = None) -> None:
        """Create nodegraph output ports mirroring upstream output attribute models."""

        self.set_inputs(value, item)

    def set_inputs(self, value: Any, item: Optional[Any] = None) -> bool:
        """Mirror an upstream output and report whether its connection succeeded."""
        if item:
            setter = getattr(item, "set_inputs", None)
            if callable(setter):
                return setter(value) is not False
            item.inputs = value
            return True
        for v in value:
            if isinstance(v, OutputAttributeModel):
                port_model = self.create_output_port(v.path.name, v.type)
                if port_model:
                    return port_model.set_inputs([v])
                logger.warning("nodegraph output port creation failed for %s", v.path)
                return False
            break
        return False

    def set_valid(self) -> None:
        """Recompute validity from this graph prim without hiding invalid children.

        A NodeGraph remains a valid graph container when one of its shader
        definitions cannot be resolved.  Invalid descendants are rendered by
        the graph's fallback-node path and reported independently by the
        validation framework.
        """
        self._valid = self.prim_exists()

    def has_invalid_connected_children(self) -> bool:
        """Return whether the graph's output network contains an invalid node."""

        for prim in self._outputs.get_connected_prims(False):
            if prim == self.prim:
                continue
            model = self.get_item_model(prim.GetPath())
            if not model:
                continue
            if isinstance(model, NodeGraphModel):
                if model.has_invalid_connected_children():
                    return True
            elif not model.valid:
                return True
        return False

    def get_input_attributes(self, input_proxy_attributes: List[Any]) -> None:
        """Collect nodegraph inputs and mirror unresolved internal interface state."""
        super().get_input_attributes(input_proxy_attributes)
        self._apply_interface_proxy_state(input_proxy_attributes, True)

    def get_output_attributes(self, output_proxy_attributes: List[Any]) -> None:
        """Collect nodegraph outputs and mirror unresolved internal interface state."""
        super().get_output_attributes(output_proxy_attributes)
        self._apply_interface_proxy_state(output_proxy_attributes, False)

    def sync_position(self) -> None:
        """Refresh node position plus context-specific input/output IO node positions."""
        for idx, suffix in enumerate([self.INPUT, self.OUTPUT]):
            key = self._get_context_position_key(suffix)
            if self.prim.HasAuthoredCustomDataKey(key):
                self._input_output_position[idx] = self.prim.GetCustomDataByKey(key)
        super().sync_position()

    def sync(self, *args: Any, **kwargs: Any) -> None:
        """Synchronize children and port state."""
        logger.debug("sync nodegraph start %s (%s)", self._prim_path, self._context_name)
        if not self.prim_exists():
            logger.warning("sync nodegraph failed: missing prim %s", self._prim_path)
            self.clear()
            return
        super().sync()
        self._sync_children()
        if self._child_ports_dirty:
            self._sync_child_ports()
            self._child_ports_dirty = False
        else:
            # Child sync already refreshed ports above; this only requests the extra
            # child-port flush needed by later item lookups after parent/interface changes.
            self._child_ports_dirty = True
        self._compute_backdrop_stacking_cache()
        self.set_valid()
        self._sync_interface_polymorphic_flags()
        self.sync_ports()
        logger.debug("sync nodegraph end %s children=%s", self._prim_path, len(self._children))
        self._synced_once = True

    def _apply_interface_proxy_state(self, proxy_attributes: List[Any], is_input: bool) -> None:
        """Update proxy attributes for nodegraph interface ports linked to polymorphic children."""
        for proxy in proxy_attributes:
            self._update_interface_proxy(proxy, is_input)

    def _sync_interface_polymorphic_flags(self) -> None:
        """Refresh existing interface port model flags after child models sync."""
        for group, is_input in ((self._inputs, True), (self._outputs, False)):
            if not group:
                continue
            for port_model in self._iter_attribute_ports(group):
                proxy = getattr(port_model, "proxy_attribute", None)
                if proxy is None:
                    continue
                self._update_interface_proxy(proxy, is_input, port_model)
                port_model.update_proxy_attribute(proxy)

    def _update_interface_proxy(self, proxy: Any, is_input: bool, port_model: Optional[Any] = None) -> None:
        """Apply unresolved/concrete type state to one interface proxy."""
        port_name = strip_usd_namespace(getattr(proxy, "name", ""))
        unresolved, candidate_types = self._get_interface_polymorphic_state(port_name, is_input)
        proxy.polymorphic_unresolved = unresolved
        if len(candidate_types) == 1:
            proxy.type_name = candidate_types[0]
        elif port_model is not None and getattr(port_model, "usdshade_port", None):
            proxy.type_name = port_model.usdshade_port.GetAttr().GetTypeName()

    def _iter_attribute_ports(self, group: Any) -> List[Any]:
        """Return flat attribute ports from a possibly grouped port container."""
        ports = []
        for port in group.ports:
            if isinstance(port, AttributeGroupModel):
                ports.extend(self._iter_attribute_ports(port))
            else:
                ports.append(port)
        return ports

    def _get_interface_polymorphic_state(self, port_name: str, is_input: bool) -> tuple[bool, List[str]]:
        """Return unresolved state and candidate types for one nodegraph interface port."""
        linked_ports = self._get_interface_linked_port_models(port_name, is_input)
        candidate_types = self._get_candidate_port_types(port_name, is_input)
        constrained_types = self._get_externally_constrained_candidate_types(port_name, is_input, candidate_types)
        if constrained_types:
            return len(constrained_types) != 1, constrained_types
        unresolved = any(
            bool(getattr(getattr(port, "proxy_attribute", None), "polymorphic_unresolved", False))
            for port in linked_ports
        )
        return unresolved, candidate_types

    def _get_externally_constrained_candidate_types(
        self,
        port_name: str,
        is_input: bool,
        candidate_types: List[str],
    ) -> List[str]:
        """Narrow interface candidate types by an external nodegraph connection."""
        if not candidate_types:
            return []
        external_type = self._get_external_interface_connection_type(port_name, is_input)
        if not external_type:
            return []
        if is_input:
            scored = [
                (score, candidate_type)
                for candidate_type in candidate_types
                if (score := mdl_type_polymorphic_constraint_score(candidate_type, external_type, True)) is not None
            ]
        else:
            scored = [
                (score, candidate_type)
                for candidate_type in candidate_types
                if (score := mdl_type_polymorphic_constraint_score(external_type, candidate_type, True)) is not None
            ]
        if not scored:
            return []
        best_score = min(score for score, _candidate_type in scored)
        narrowed = [candidate_type for score, candidate_type in scored if score == best_score]
        return list(dict.fromkeys(narrowed))

    def _get_external_interface_connection_type(self, port_name: str, is_input: bool) -> Optional[str]:
        """Return the external source type connected to a nodegraph interface port."""
        if not is_input:
            return None
        nodegraph = UsdShade.NodeGraph(self.prim)
        interface_port = nodegraph.GetInput(port_name) if nodegraph else None
        if not (interface_port and interface_port.HasConnectedSource()):
            return None
        try:
            source, source_name, _ = interface_port.GetConnectedSource()
        except (RuntimeError, ValueError, TypeError, AttributeError):
            return None
        if not (source and source_name):
            try:
                source_paths = interface_port.GetRawConnectedSourcePaths() or []
            except (RuntimeError, ValueError, TypeError, AttributeError):
                source_paths = []
            for source_path in source_paths:
                source_attr = self.stage.GetAttributeAtPath(source_path) if self.stage else None
                if source_attr:
                    return str(source_attr.GetTypeName())
            return None
        source_port = source.GetOutput(source_name) or source.GetInput(source_name)
        return str(source_port.GetTypeName()) if source_port else None

    def _get_candidate_port_types(self, port_name: str, is_input: bool) -> List[str]:
        """Return candidate concrete types for an interface port from linked child ports."""
        candidates: List[str] = []
        for port in self._get_interface_linked_port_models(port_name, is_input):
            proxy = getattr(port, "proxy_attribute", None)
            if proxy is not None and getattr(proxy, "polymorphic_unresolved", False):
                get_types = getattr(port, "_get_candidate_port_types", None)
                if callable(get_types):
                    port_candidates = [str(type_name) for type_name in get_types() if type_name]
                    if port_candidates:
                        candidates.extend(port_candidates)
                        continue
            port_type = getattr(port, "type", None)
            if port_type:
                candidates.append(str(port_type))

        return list(dict.fromkeys(candidates))

    def _get_interface_linked_port_models(self, port_name: str, is_input: bool) -> List[Any]:
        """Resolve child ports that are connected through a nodegraph interface port."""
        if is_input:
            return self._get_input_interface_consumers(port_name)
        return self._get_output_interface_sources(port_name)

    def _get_input_interface_consumers(self, port_name: str) -> List[Any]:
        """Return child input models consuming the named nodegraph input."""
        linked = []
        interface_attr_name = f"{UsdShade.Tokens.inputs}{port_name}"
        for child_model in self._children.values():
            prim = getattr(child_model, "prim", None)
            api = UsdShade.ConnectableAPI(prim) if prim else None
            if not api:
                continue
            for child_input in api.GetInputs():
                for source_path in child_input.GetRawConnectedSourcePaths():
                    if source_path.GetPrimPath() != self._prim_path:
                        continue
                    if str(source_path.name) != interface_attr_name:
                        continue
                    port_model = self.get_item_model(child_input.GetAttr().GetPath())
                    if port_model:
                        linked.append(port_model)
                    break
        return linked

    def _get_output_interface_sources(self, port_name: str) -> List[Any]:
        """Return child source models driving the named nodegraph output."""
        nodegraph = UsdShade.NodeGraph(self.prim)
        ng_output = nodegraph.GetOutput(port_name) if nodegraph else None
        if not ng_output:
            return []
        linked = []
        sources_result = ng_output.GetConnectedSources()
        sources = sources_result[0] if isinstance(sources_result, tuple) else sources_result
        for source_info in sources or []:
            prefix = (
                UsdShade.Tokens.inputs
                if source_info.sourceType == UsdShade.AttributeType.Input
                else UsdShade.Tokens.outputs
            )
            prop_path = source_info.source.GetPath().AppendProperty(f"{prefix}{source_info.sourceName}")
            port_model = self.get_item_model(prop_path)
            if port_model:
                linked.append(port_model)
        return linked

    def get_backdrop_stacking_order(self, backdrop_model: BackdropModel) -> int:
        """Return cached/calculated backdrop stacking order for rendering precedence."""
        return self._backdrop_calculator.get_order(backdrop_model, self._backdrop_stacking_cache)

    def _compute_backdrop_stacking_cache(self) -> None:
        """Compute stacking order for backdrops based on overlaps."""
        self._backdrop_stacking_cache, self._backdrop_stacking_signature = self._backdrop_calculator.compute(
            self._children.values(),
            self._backdrop_stacking_cache,
            self._backdrop_stacking_signature,
        )

    def _clear_backdrop_cache(self) -> None:
        """Reset cached backdrop stacking map/signature after structural graph changes."""
        self._backdrop_stacking_cache = {}
        self._backdrop_stacking_signature = None

    def _sync_children(self) -> None:
        """Synchronize child models with current prim children."""
        self._cached_child_resolver_paths = None
        existing = set(self._children.keys())
        child_prims = self.get_child_prims()
        self._cache_polymorphic_graph_connection_index()
        for index, child_prim in enumerate(child_prims):
            key = child_prim.GetPath()
            if key in existing:
                self._children[key].sync()
                existing.discard(key)
                continue
            self.create_child(child_prim)
        self._remove_stale_children(existing)

    def _remove_stale_children(self, paths) -> None:
        """Destroy child models that no longer exist."""
        for key in paths:
            child = self._children.pop(key, None)
            if child:
                child.destroy()

    def _sync_child_ports(self) -> None:
        """Synchronize ports on child models."""
        for child_model in self._children.values():
            child_model.sync_ports()

    def _ensure_child_ports_synced(self) -> None:
        """Flush deferred child port sync if pending."""
        if self._child_ports_dirty:
            self._child_ports_dirty = False
            self._sync_child_ports()

    def get_item_model(self, item: Any) -> Optional[Any]:
        """Resolve a model from a prim or property path."""
        self._ensure_child_ports_synced()
        res = super().get_item_model(item)
        if res:
            return res
        for ancestor_path in item.GetPrimPath().GetAncestorsRange():
            if (ancestor_path.GetParentPath() == self._prim_path) and (ancestor_path in self._children):
                child_model = self._children[ancestor_path]
                return child_model.get_item_model(item)

    def get_child_prims(self) -> List[Usd.Prim]:
        """Return visible child prims for the active context and graph filtering rules."""
        resolver = self._child_resolver
        if not resolver:
            return []
        cached_paths = self._cached_child_resolver_paths
        if cached_paths is not None:
            stage = self._get_stage()
            if stage and set(cached_paths) == set(self._children.keys()):
                out: List[Usd.Prim] = []
                for path in cached_paths:
                    prim = stage.GetPrimAtPath(path)
                    if not prim or not prim.IsValid() or not resolver.is_visible_child_prim(prim):
                        self._cached_child_resolver_paths = None
                        break
                    out.append(prim)
                else:
                    return out
        fresh = resolver.get_child_prims()
        self._cached_child_resolver_paths = tuple(p.GetPath() for p in fresh)
        return fresh

    def create_child(self, prim: Usd.Prim) -> bool:
        """Instantiate and register the correct model type for a discovered child prim."""
        child_path = prim.GetPath()
        child_cls = None
        if prim.IsA(UsdShade.NodeGraph):
            child_cls = NodeGraphModel
        elif prim.IsA(UsdShade.Shader):
            child_cls = ShaderModel
        elif prim.IsA(UsdUI.Backdrop):
            child_cls = BackdropModel
        else:
            logger.warning("unsupported child prim: %s", child_path)
            return False

        self._children[child_path] = child_cls(
            prim, self._context_name, self._usd_context, self._plugin, self, sync=False
        )
        self._children[child_path].sync()
        return True

    def _cache_polymorphic_graph_connection_index(self) -> None:
        """Let plugins precompute graph-level connection state before child sync."""
        self._call_plugin_hook("cache_polymorphic_graph_connection_index", self._prim)

    def _invalidate_polymorphic_runtime_cache(self) -> None:
        """Invalidate plugin polymorphic caches after relevant graph edits."""
        self._call_plugin_hook("invalidate_polymorphic_runtime_cache")

    def _call_plugin_hook(self, name: str, *args: Any) -> None:
        """Call an optional plugin hook, tolerating lightweight test doubles."""
        hook = getattr(getattr(self, "_plugin", None), name, None)
        if callable(hook):
            hook(*args)

    def remove_child(self, prim_path: Any) -> None:
        """Remove and destroy a child model cached under the provided prim path."""
        child = self._children.pop(prim_path, None)
        if child:
            child.destroy()

    def remove_input(self) -> bool:
        """Clear cached/input-node position metadata and remove persisted USD position."""
        result = self.remove_position_cmd(self.INPUT)
        if not result.success:
            return False
        self._input_output_position[0] = None
        return True

    def remove_output(self) -> bool:
        """Clear cached/output-node position metadata and remove persisted USD position."""
        result = self.remove_position_cmd(self.OUTPUT)
        if not result.success:
            return False
        self._input_output_position[1] = None
        return True

    @property
    def position(self, item: Optional[Any] = None) -> Any:
        """Resolve position for prims, IO wrappers, and staged batch-move proxies."""
        if getattr(self, "_position_txn", None) and self._position_txn.is_staging:
            if item is None:
                return self._ui_state.position
            helper_item = self._normalize_moving_item(item) or item
            return self._position_txn.get_position(helper_item)

        if self._is_input_output_node_item(item):
            idx = 0 if type(item).get_type_name() == "InputNode" else 1
            return self._input_output_position[idx]

        # Grouped IO items may be used by view callbacks for drag/refresh. Route
        # those reads to the concrete IO node position cache.
        if isinstance(item, InputAttributeGroupModel) and item.prim_path == self._prim_path:
            return self._input_output_position[0]
        if isinstance(item, OutputAttributeGroupModel) and item.prim_path == self._prim_path:
            return self._input_output_position[1]

        prim_model = getattr(item, "prim_model", None) if item else self
        if prim_model is None:
            return None
        if prim_model != self:
            model_cls = type(prim_model)
            return model_cls.position.fget(prim_model, item)
        elif isinstance(item, PrimModel):
            return self._ui_state.position
        elif isinstance(item, AttributeModel):
            if isinstance(item, InputAttributeModel):
                return self._input_output_position[0]
            elif isinstance(item, OutputAttributeModel):
                return self._input_output_position[1]

    @position.setter
    def position(self, value: Any, item: Optional[Any] = None) -> None:
        """Route position edits through staging/commit flow for prim and IO items."""
        if self._position_txn.is_committing:
            return
        # Grouped IO drags emit occasional non-staging position sets through
        # Input/Output attribute-group proxies. Those values can be stale and
        # visually snap the IO node back right after a successful commit.
        if (
            not self._position_txn.is_staging
            and isinstance(item, AttributeGroupModel)
            and item.prim_path == self._prim_path
        ):
            return
        if self._is_input_output_node_item(item):
            if self._position_txn.is_staging:
                self._position_txn.set_position(item, value)
                # IO staged move notifications are intentionally suppressed.
                # The corresponding callback path would immediately skip these
                # events anyway, so emitting them only adds queue pressure.
                return
            self._persist_concrete_position(item, value)
            return
        if self._position_txn.is_staging:
            if not self._position_txn.has_any_io_entries():
                self.batch_set_position(value, item)
        if self._position_txn.is_staging:
            helper_item = self._normalize_moving_item(item) or item
            self._position_txn.set_position(helper_item, value)
            is_io_staging_item = self._is_input_output_node_item(item) or (
                isinstance(
                    item,
                    (
                        InputAttributeModel,
                        OutputAttributeModel,
                        InputAttributeGroupModel,
                        OutputAttributeGroupModel,
                    ),
                )
                and item.prim_path == self._prim_path
            )
            if is_io_staging_item:
                # IO staged move notifications are intentionally suppressed.
                # The corresponding callback path would immediately skip these
                # events anyway, so emitting them only adds queue pressure.
                pass
            else:
                self.model_root.notify_position_changed(item)
            return

        prim_model = item.prim_model if item else self
        if prim_model is None:
            return
        if prim_model != self:
            model_cls = type(prim_model)
            model_cls.position.fset(prim_model, value, item)
        elif isinstance(item, PrimModel):
            self._persist_concrete_position(self, value)
        elif isinstance(item, AttributeModel):
            self._persist_concrete_position(item, value)

    def position_begin_edit(self, item: Any) -> None:
        """Record the initial position for edit operations."""
        if self._position_txn.is_staging:
            self._force_commit_staged_positions()
        drive_item = self._normalize_moving_item(item)
        moving_items = self._get_selected_moving_items(drive_item)
        if drive_item and drive_item not in moving_items:
            moving_items.append(drive_item)
        self._position_txn.begin(moving_items)
        # Always open the batch move lifecycle so GraphView interaction state
        # transitions consistently across shader and IO drags.
        self.batch_position_begin_edit(drive_item)

    def position_end_edit(self, item: Optional[Any]) -> None:
        """Finalize position edits by committing staged moves and ending batch operations."""
        drive_item = self._normalize_moving_item(item) if item else item
        if self._position_txn.is_staging:
            self.batch_position_end_edit(drive_item)
            self._commit_staged_positions()
            if self._is_input_output_node_item(drive_item):
                # IO wrappers can leave stale model-side selection entries after
                # drag-end; let the next stage-driven selection update repopulate.
                self._selected_items = []
            return
        self.batch_position_end_edit(drive_item)

    def _commit_staged_positions(self) -> None:
        """Commit all staged positions into one undoable transaction."""
        with omni.kit.undo.group():
            self._position_txn.commit(self._apply_staged_position)

    def _force_commit_staged_positions(self) -> None:
        """Best-effort commit for pending staged positions."""
        if not self._position_txn.force_commit(self._apply_staged_position):
            return

    @property
    def nodes(self, item: Optional[Any] = None) -> Optional[List[Any]]:
        """Return top-level nodes or nested child nodes for a specific nodegraph item."""
        if item is None:
            return [self] + list(self._children.values())
        elif isinstance(item, NodeGraphModel):
            return list(item._children.values())

    @property
    def active(self, item: Optional[Any] = None) -> bool:
        """Report whether this model is active and listening to stage/selection updates."""
        return item.active if item else self._is_active

    @active.setter
    def active(self, value: bool) -> None:
        """Activate or deactivate the model and listeners."""
        if self._is_active == value:
            return
        if self._selection_adapter:
            self._selection_adapter.clear()
        self._is_active = value

        if self._is_active:
            if self._skip_next_activation_sync and self._synced_once:
                self._skip_next_activation_sync = False
            else:
                self.sync(reason="activate")
            self.set_valid()
            self._stage_listener_manager.activate()
        else:
            self._skip_next_activation_sync = False
            self._force_commit_staged_positions()
            self._clear_stage_listeners()

    def _clear_stage_listeners(self) -> None:
        """Detach stage-notice subscriptions managed by the stage listener manager."""
        if self._stage_listener_manager:
            self._stage_listener_manager.clear()

    def suppress_stage_listener_property_paths_for_frames(
        self, paths: Sequence[Union[Sdf.Path, str]], *, frames: int = 2
    ) -> None:
        """Drop matching paths from ObjectsChanged handling briefly.

        Connection commands emit USD notices after ``notify_connection_changed`` already
        refreshed the port; ignoring avoids a second deferred pass and duplicate canvas rebuilds.
        """
        listener = getattr(self._stage_listener_manager, "_stage_listener", None)
        if not listener or not paths or not self._lifecycle:
            return
        normalized = [p if isinstance(p, Sdf.Path) else Sdf.Path(str(p)) for p in paths]
        listener.add_ignored_paths(normalized)

        async def _restore_ignored() -> None:
            for _ in range(max(1, frames)):
                await omni.kit.app.get_app().next_update_async()
            try:
                listener.remove_ignored_paths(normalized)
            except (RuntimeError, ValueError, TypeError, AttributeError):
                pass

        self._lifecycle.add_task(_restore_ignored(), label="restore stage listener ignore paths")

    def _on_item_changed_cb(self, item: Optional[Any] = None) -> None:
        """Route item-changed callbacks, skipping staged IO self-sync churn."""
        if self._consume_item_marker(self._position_only_sync_skip_items, item):
            return
        if self._consume_item_marker(self._connection_only_sync_skip_items, item):
            return
        if item is None and self._suppress_next_none_item_changed:
            self._suppress_next_none_item_changed = False
            return
        if (
            self._position_txn.is_staging
            and isinstance(
                item,
                (
                    InputAttributeModel,
                    OutputAttributeModel,
                    InputAttributeGroupModel,
                    OutputAttributeGroupModel,
                ),
            )
            and item.prim_path == self._prim_path
        ):
            # IO drag move updates are staged; syncing the whole nodegraph on each
            # move event is unnecessary and causes visible drag lag.
            return
        if item is None:
            self._invalidate_polymorphic_runtime_cache()
        super()._on_item_changed_cb(item)

    def notify_position_changed(self, item: Any) -> None:
        """Notify position-only observers without routing through full item sync."""
        if item is not None:
            self._position_only_sync_skip_items[id(item)] = item
            self._position_only_view_items[id(item)] = item
            self._position_only_validation_items[id(item)] = item
        self._item_changed(item)

    def set_connection_visual_sync_callback(self, cb: Optional[Callable[[Any], None]]) -> None:
        """Register a canvas hook invoked synchronously before ``_item_changed`` on connection edits."""
        self._connection_visual_sync_cb = cb

    def notify_connection_changed(self, item: Any) -> None:
        """Notify connection observers after syncing either the item or full graph."""
        self._invalidate_polymorphic_runtime_cache()
        if item is None:
            self.sync(sync_reason="connection_changed")
            self._suppress_next_none_item_changed = True
        else:
            self._sync_connection_changed_item(item)
        if item is not None:
            self._connection_only_sync_skip_items[id(item)] = item
        cb = getattr(self, "_connection_visual_sync_cb", None)
        if cb is not None:
            try:
                cb(item)
            except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
                logger.debug("connection visual sync callback failed: %s", exc)
        self._item_changed(item)

    def _sync_connection_changed_item(self, item: Any) -> None:
        """Refresh the owning prim before a lightweight rebuild."""
        if item is None:
            return
        try:
            try:
                prim_model = getattr(item, "prim_model", None)
                if prim_model is self:
                    item_sync = getattr(item, "sync", None)
                    if callable(item_sync):
                        item_sync()
                    else:
                        self.sync_ports()
                else:
                    prim_sync = getattr(prim_model, "sync", None)
                    if callable(prim_sync):
                        prim_sync()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.debug("connection changed item sync skipped: %s", exc)
            self._sync_interface_polymorphic_flags()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.debug("connection changed interface polymorphic sync skipped: %s", exc)

    def skip_next_activation_sync(self) -> None:
        """Skip one activation sync when the model was just fully synchronized."""
        self._skip_next_activation_sync = True

    def consume_position_only_changed(self, item: Any) -> bool:
        """Return True once for an item emitted through notify_position_changed."""
        return self._consume_item_marker(self._position_only_view_items, item)

    def consume_position_only_validation_changed(self, item: Any) -> bool:
        """Return True once when validation should ignore a position-only notification."""
        return self._consume_item_marker(self._position_only_validation_items, item)

    @staticmethod
    def _consume_item_marker(markers: dict, item: Any) -> bool:
        """Consume a marker without invoking item hashing/equality."""
        if item is None:
            return False
        marker_id = id(item)
        if markers.get(marker_id) is not item:
            return False
        del markers[marker_id]
        return True

    def set_pause(self, enabled: bool) -> None:
        """Propagate pause state to children."""
        if enabled:
            self._force_commit_staged_positions()
        for model in self._children.values():
            model.set_pause(enabled)
        super().set_pause(enabled)

    @staticmethod
    def _is_input_output_node_item(item: Any) -> bool:
        """Return whether an item is an isolation input/output wrapper node object."""
        return PositionItemResolver.is_input_output_node_item(item)

    def _normalize_moving_item(self, item: Any) -> Any:
        """Normalize wrappers/proxies to the concrete item used by batch move helpers."""
        return self._position_item_resolver.normalize_moving_item(item)

    def _get_selected_moving_items(self, drive_item: Optional[Any] = None) -> List[Any]:
        """Return de-duplicated selected items normalized for movement transactions."""
        selected = self._selection_adapter.get_selected_nodes(
            self._stage,
            self._prim_path,
            self.get_item_model,
        )
        include_transient_selection = not selected
        for item in self._selected_items:
            # Keep only non-prim transient selections (for example IO wrappers).
            # Prim selections are sourced from USD selection via SelectionAdapter.
            if isinstance(item, PrimModel):
                continue
            if not include_transient_selection:
                continue
            if item not in selected:
                selected.append(item)
        normalized = []
        for item in selected:
            concrete = self._normalize_moving_item(item)
            if concrete is not None and concrete not in normalized:
                normalized.append(concrete)
        return normalized

    def _apply_staged_position(self, item: Any, value: Any) -> None:
        """Apply a staged position without batch delta propagation."""
        concrete_item = self._resolve_concrete_position_item(item)
        if concrete_item is None:
            return
        notify_root = not (
            self._is_input_output_node_item(concrete_item)
            or isinstance(concrete_item, (InputAttributeModel, OutputAttributeModel))
        )
        self._persist_concrete_position(concrete_item, value, notify_root=notify_root)

    def _resolve_concrete_position_item(self, item: Any) -> Optional[Any]:
        """Resolve wrappers/proxies to a concrete PrimModel/AttributeModel item."""
        return self._position_item_resolver.resolve_concrete_position_item(item)

    def _persist_concrete_position(self, item: Any, value: Any, notify_root: bool = False) -> bool:
        """Persist a concrete position without committing optimistic cache state."""
        if isinstance(item, PrimModel):
            return item.set_position(value)

        if self._is_input_output_node_item(item):
            idx = 0 if type(item).get_type_name() == "InputNode" else 1
            current_value = self._input_output_position[idx]
            if not self._positions_close(current_value, value):
                suffix = [self.INPUT, self.OUTPUT][idx]
                if value is None:
                    result = self.remove_position_cmd(suffix)
                else:
                    result = self.set_position_cmd(value, suffix)
                if not getattr(result, "success", False):
                    logger.warning("set input/output node position failed for %s", self._prim_path)
                    return False
                self._input_output_position[idx] = value
                # IO position commits can emit a follow-up item-changed(None) from
                # command plumbing; skipping one immediate None-driven sync avoids
                # a costly full graph refresh right after drag release.
                self._suppress_next_none_item_changed = True
                self._suppress_next_selection_run_select = True
                if notify_root and self.model_root:
                    self.model_root._item_changed(self)
            return True

        if isinstance(item, AttributeModel):
            idx = int(isinstance(item, OutputAttributeModel))
            current_value = self._input_output_position[idx]
            if not self._positions_close(current_value, value):
                suffix = [self.INPUT, self.OUTPUT][idx]
                if value is None:
                    result = self.remove_position_cmd(suffix)
                else:
                    result = self.set_position_cmd(value, suffix)
                if not getattr(result, "success", False):
                    logger.warning("set input/output port position failed for %s", self._prim_path)
                    return False
                self._input_output_position[idx] = value
                self._suppress_next_none_item_changed = True
                self._suppress_next_selection_run_select = True
                if notify_root and self.model_root:
                    self.model_root._item_changed(self)
            return True
        return False

    def _get_selected_nodes(self, drive_item: Optional[Any] = None, *args: Any, **kwargs: Any) -> List[Any]:
        """Backward-compatible selected-node getter for UI selection rendering."""
        selected = self._selection_adapter.get_selected_nodes(
            self._stage,
            self._prim_path,
            self.get_item_model,
        )
        include_transient_selection = not selected
        for item in self._selected_items:
            # Avoid re-introducing stale prim-node selections that are no longer in USD selection.
            if isinstance(item, PrimModel):
                continue
            if not include_transient_selection:
                continue
            if item not in selected:
                selected.append(item)
        return selected

    @property
    def selection(self, item: Optional[Any] = None) -> List[Any]:
        """Return current graph selection as model items synchronized with stage selection."""
        if item:
            return item.selection
        return self._get_selected_nodes()

    @selection.setter
    def selection(self, value: List[Any]) -> None:
        """Store model selection and mirror it to USD stage selection through adapter."""
        self._selected_items = list(value or [])

        def _on_changed(kit_selection, selection, run_select):
            """Execute on changed behavior for material graph workflows."""

            if run_select and self._suppress_next_selection_run_select:
                self._suppress_next_selection_run_select = False
                self._selection_changed()
                return
            if run_select:
                if not SelectionAdapter.apply_selection(kit_selection, selection, run_select):
                    self._selection_adapter.clear()
                    self._selection_changed()
            else:
                self._selection_changed()

        prim_items = [item for item in (value or []) if isinstance(item, PrimModel)]
        self._selection_adapter.sync_selection(prim_items, _on_changed)

    def add_input_or_output(self, position: Any, is_input: bool) -> bool:
        """Persist an input/output node position and cache it only after success."""
        idx = 0 if is_input else 1
        if position is None:
            return False
        if self._positions_close(self._input_output_position[idx], position):
            return True
        suffix = [self.INPUT, self.OUTPUT][idx]
        result = self.set_position_cmd(position, suffix)
        if not getattr(result, "success", False):
            logger.warning("add input/output node failed for %s", self._prim_path)
            return False
        self._input_output_position[idx] = position
        return True
