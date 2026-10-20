"""Grouped input/output port model used by graph node prim models."""

from collections import OrderedDict
from typing import Any, Dict, List, Optional, Sequence, Tuple, Type

from omni.kit.widget.graph import GraphModel
from pxr import Sdf, Usd, UsdShade

from .....config.logging import logger
from ...core.base import GraphModelBase


class AttributeGroupModel(GraphModelBase):
    """Container model for grouped input/output attributes."""

    def __init__(
        self,
        name: str,
        parent: Any,
        prim: Any,
        context_name: str,
        usd_context: Any,
        plugin: Any,
        pause: bool,
        child_cls: Type[Any],
        child_group_cls: Type[Any],
        property_prefix: str,
    ) -> None:
        """Initialize instance state for this material graph component."""

        type_name = self.__class__.__name__
        super().__init__(name, type_name, prim.GetPath(), parent, prim, context_name, usd_context, plugin, pause)
        self._expansion_state = GraphModel.ExpansionState.CLOSED
        self._children = OrderedDict()
        self._child_cls = child_cls
        self._child_group_cls = child_group_cls
        self._has_incoming_connections = False
        self._incoming_dirty = True
        self._children_version = 0
        self._child_keys = ()
        self._cached_child_paths = []
        self._cached_child_paths_version = -1
        self._incoming_cache_key = None
        self._incoming_cache_value = False
        self._display_group = ""
        self._child_ports = []
        self._property_prefix = property_prefix
        self._refresh_display_group()

    def __eq__(self, other: Any) -> bool:
        """Execute eq behavior for material graph workflows."""

        return isinstance(other, AttributeGroupModel) and (
            self._name,
            self._display_group,
            self._prim_path,
            self._children,
        ) == (
            other._name,
            other._display_group,
            other._prim_path,
            other._children,
        )

    __hash__ = object.__hash__

    def __setitem__(self, key: Any, value: Any) -> None:
        """Execute setitem behavior for material graph workflows."""

        self._children[key] = value

    def __getitem__(self, key: Any) -> Optional[Any]:
        """Execute getitem behavior for material graph workflows."""

        if key in self._children:
            return self._children[key]
        return None

    def _update_child_cache(self, new_children: Dict[Any, Any]) -> None:
        """Execute update child cache behavior for material graph workflows."""

        new_keys = tuple(new_children.keys())
        if new_keys != self._child_keys:
            self._child_keys = new_keys
            self._children_version += 1
            self._invalidate_child_paths_cache()
            self._invalidate_incoming_cache()
            self._refresh_display_group()

    def _invalidate_child_paths_cache(self) -> None:
        """Execute invalidate child paths cache behavior for material graph workflows."""

        self._cached_child_paths = []
        self._cached_child_paths_version = -1

    @property
    def child_ports(self, item: Optional[Any] = None) -> List[Any]:
        """Execute child ports behavior for material graph workflows."""

        return item.child_ports if item else self._child_ports

    @property
    def prim_model(self, item: Optional[Any] = None) -> Any:
        """Execute prim model behavior for material graph workflows."""

        if item:
            return item.prim_model
        if self.parent:
            return self.parent.prim_model
        return None

    @property
    def style(self, item: Optional[Any] = None) -> Dict[str, Any]:
        """Execute style behavior for material graph workflows."""

        return item.style if item else {}

    def set_pause(self, enabled: bool) -> None:
        """Execute set pause behavior for material graph workflows."""

        super().set_pause(enabled)
        for model in self._children.values():
            model.pause = enabled

    @property
    def inputs(self, item: Optional[Any] = None) -> List[Any]:
        """Execute inputs behavior for material graph workflows."""

        if item:
            return item.inputs
        return []

    @inputs.setter
    def inputs(self, value: Optional[Sequence[Any]], item: Optional[Any] = None) -> None:
        """Execute inputs behavior for material graph workflows."""

        if item:
            item.inputs = value

    @property
    def outputs(self, item: Optional[Any] = None) -> Optional[List[Any]]:
        """Execute outputs behavior for material graph workflows."""

        if item:
            return item.outputs
        return None

    @outputs.setter
    def outputs(self, value: Optional[Sequence[Any]], item: Optional[Any] = None) -> None:
        """Execute outputs behavior for material graph workflows."""

        if item:
            item.outputs = value

    @property
    def ports(self, item: Optional[Any] = None) -> List[Any]:
        """Execute ports behavior for material graph workflows."""

        if item:
            return item.ports
        return list(self._children.values())

    @property
    def expansion_state(self, item: Optional[Any] = None) -> GraphModel.ExpansionState:
        """Execute expansion state behavior for material graph workflows."""

        if item:
            return item.expansion_state
        if self._has_connected_sources():
            return GraphModel.ExpansionState.OPEN
        if self._incoming_dirty:
            self._has_incoming_connections = self._has_incoming_connections_from_stage(
                self._collect_child_attribute_paths()
            )
            self._incoming_dirty = False
        if self._has_incoming_connections:
            return GraphModel.ExpansionState.OPEN
        return self._expansion_state

    @expansion_state.setter
    def expansion_state(self, value: GraphModel.ExpansionState, item: Optional[Any] = None) -> None:
        """Execute expansion state behavior for material graph workflows."""

        if item:
            item.expansion_state = value
            return
        if self._expansion_state != value:
            self._expansion_state = value
            if self.model_root:
                self.model_root._item_changed(None)

    @property
    def connected_ports(self, item: Optional[Any] = None) -> List[Any]:
        """Execute connected ports behavior for material graph workflows."""

        if item:
            return item.connected_ports
        connected = []
        for port in self._children.values():
            if "connected_ports" in dir(port) and port.connected_ports:
                if isinstance(port, type(self)):
                    connected.extend(port.connected_ports)
                else:
                    connected.extend(port.connected_ports)
        return connected

    def _port_has_connection(self, port: Any) -> bool:
        """Execute port has connection behavior for material graph workflows."""

        usd_port = port.usdshade_port if "usdshade_port" in dir(port) else None
        if usd_port:
            try:
                # USD 25.02 (Kit 109) can report ``HasConnectedSource`` for an
                # authored-empty connection list.  Inspect the composed paths
                # directly so a disconnect opinion does not pin the group open.
                attr = usd_port.GetAttr()
                if attr and attr.GetConnections():
                    return True
            except (RuntimeError, TypeError, AttributeError) as exc:
                # A stale wrapper can disappear during notice processing.  The
                # cached model and stage-path checks below remain safe fallbacks.
                logger.debug(
                    "group connection query failed for group='%s' prim='%s': %s",
                    self._name,
                    self._prim_path,
                    exc,
                )
        connected = port.connected_ports if "connected_ports" in dir(port) else None
        if connected:
            return True
        path = port.path if "path" in dir(port) else None
        if path and self.stage:
            attr = self.stage.GetAttributeAtPath(path)
            # DisconnectSource deliberately authors an empty connection list so
            # weaker-layer connections stay blocked.  That is an authored
            # opinion, but it is not a live connection and must not force the
            # containing parameter group to remain open.
            if attr and attr.GetConnections():
                return True
        return False

    def _has_connected_sources(self) -> bool:
        """Execute has connected sources behavior for material graph workflows."""

        for port in self._children.values():
            if isinstance(port, AttributeGroupModel):
                if port._has_connected_sources():
                    return True
                continue
            if self._port_has_connection(port):
                return True
        return False

    def _collect_child_attribute_paths(self) -> List[Any]:
        """Execute collect child attribute paths behavior for material graph workflows."""

        if self._cached_child_paths_version == self._children_version:
            return list(self._cached_child_paths)

        paths = []
        for port in self._children.values():
            if isinstance(port, AttributeGroupModel):
                paths.extend(port._collect_child_attribute_paths())
            else:
                path = getattr(port, "path", None)
                if path:
                    paths.append(path)
        self._cached_child_paths = paths
        self._cached_child_paths_version = self._children_version
        return paths

    def _has_incoming_connections_from_stage(self, target_paths: Sequence[Any]) -> bool:
        """Execute has incoming connections from stage behavior for material graph workflows."""

        if not target_paths or not self.stage or not self.prim:
            return False

        stage_version = None
        stage_id = id(self.stage)
        root_layer = self.stage.GetRootLayer() if self.stage else None
        if root_layer and "GetVersion" in dir(root_layer):
            stage_version = root_layer.GetVersion()
        cache_key = (self._prim_path, frozenset(target_paths), stage_id, stage_version)
        if cache_key == self._incoming_cache_key:
            return self._incoming_cache_value

        target_set = set(target_paths)
        for prim in Usd.PrimRange(self.prim):
            for attr in prim.GetAttributes():
                connections = attr.GetConnections()
                if not connections:
                    continue
                for connected_path in connections:
                    if connected_path in target_set:
                        self._incoming_cache_key = cache_key
                        self._incoming_cache_value = True
                        return True
        self._incoming_cache_key = cache_key
        self._incoming_cache_value = False
        return False

    def _invalidate_incoming_cache(self) -> None:
        """Execute invalidate incoming cache behavior for material graph workflows."""

        self._incoming_cache_key = None
        self._incoming_cache_value = False
        self._incoming_dirty = True

    def _refresh_display_group(self) -> None:
        """Execute refresh display group behavior for material graph workflows."""

        display_group = ""
        if isinstance(self.parent, AttributeGroupModel):
            parent_display_group = self.parent.display_group
            if parent_display_group:
                prefix = f"{parent_display_group}{Sdf.Path.namespaceDelimiter}"
                display_group = f"{prefix}{self._name}"
        self._display_group = display_group

    @property
    def display_group(self, item: Optional[Any] = None) -> str:
        """Execute display group behavior for material graph workflows."""

        return item.display_group if item else self._display_group

    @property
    def tooltip_text(self, item: Optional[Any] = None) -> str:
        """Execute tooltip text behavior for material graph workflows."""

        return item.tooltip_text if item else self._name

    def filter_proxy_attributes(self, proxy_attributes: Optional[Sequence[Any]]) -> List[Tuple[Any, str]]:
        """Execute filter proxy attributes behavior for material graph workflows."""

        if not proxy_attributes:
            return []
        filtered = []

        for entry in proxy_attributes:
            if isinstance(entry, tuple) and len(entry) == 2:
                proxy_attribute, display_group = entry
            else:
                proxy_attribute = entry
                if not proxy_attribute.name.startswith(self._property_prefix):
                    continue
                if proxy_attribute.hidden:
                    continue

                parts = proxy_attribute.display_group.split(Sdf.Path.namespaceDelimiter)
                if parts[0] != self._name:
                    continue
                display_group = Sdf.Path.namespaceDelimiter.join(parts[1:])
            filtered.append((proxy_attribute, display_group))
        return filtered

    def sync_ports(self) -> None:
        """Execute sync ports behavior for material graph workflows."""

        for child in self._children.values():
            if isinstance(child, AttributeGroupModel):
                child.sync_ports()
            else:
                child.sync()
        self._invalidate_incoming_cache()
        self._incoming_dirty = True

    def sync(self, proxy_attributes: Optional[Sequence[Any]] = None, *args: Any, **kwargs: Any) -> None:
        """Execute sync behavior for material graph workflows."""
        self._refresh_display_group()
        filtered = self.filter_proxy_attributes(proxy_attributes)
        grouped_proxy_attributes, ordered_children, flat_proxy_attributes = self._partition_filtered_attributes(
            filtered
        )
        new_children = self._build_new_children(grouped_proxy_attributes, ordered_children, flat_proxy_attributes)
        old_children = self._children
        self._children = new_children
        self._update_child_cache(new_children)
        self._sync_group_children(grouped_proxy_attributes, ordered_children)
        self._destroy_removed_children(old_children)

    def _partition_filtered_attributes(
        self, filtered: Sequence[Tuple[Any, str]]
    ) -> tuple[Dict[str, list[Tuple[Any, str]]], list[str], Dict[str, Any]]:
        """Partition filtered proxy attributes into grouped and flat maps."""
        self._child_ports.clear()
        grouped_proxy_attributes: Dict[str, list[Tuple[Any, str]]] = {}
        ordered_children: list[str] = []
        flat_proxy_attributes: Dict[str, Any] = {}
        for proxy_attribute, display_group in filtered:
            if not display_group:
                child_name = proxy_attribute.name
                flat_proxy_attributes.setdefault(child_name, proxy_attribute)
                if child_name not in ordered_children:
                    ordered_children.append(child_name)
                if child_name not in self._child_ports:
                    self._child_ports.append(child_name)
                continue
            parts = display_group.split(Sdf.Path.namespaceDelimiter)
            child_name = parts[0]
            child_display_group = Sdf.Path.namespaceDelimiter.join(parts[1:])
            grouped_proxy_attributes.setdefault(child_name, []).append((proxy_attribute, child_display_group))
            if child_name not in ordered_children:
                ordered_children.append(child_name)
        return grouped_proxy_attributes, ordered_children, flat_proxy_attributes

    def _build_new_children(
        self,
        grouped_proxy_attributes: Dict[str, list[Tuple[Any, str]]],
        ordered_children: Sequence[str],
        flat_proxy_attributes: Dict[str, Any],
    ) -> OrderedDict:
        """Build updated ordered child model map."""
        new_children = OrderedDict()
        for child_name in ordered_children:
            if child_name in grouped_proxy_attributes:
                child_model = self._children.get(child_name, None)
                if not isinstance(child_model, AttributeGroupModel):
                    child_model = self._child_group_cls(
                        self, self.prim, self.context_name, self.usd_context, self.plugin, self.pause, child_name
                    )
                new_children[child_name] = child_model
            else:
                new_children[child_name] = self._resolve_flat_child_model(child_name, flat_proxy_attributes)
        return new_children

    def _resolve_flat_child_model(self, child_name: str, flat_proxy_attributes: Dict[str, Any]) -> Any:
        """Resolve/create child model for a non-grouped proxy attribute."""
        child_model = self._children.get(child_name, None)
        proxy_attribute = flat_proxy_attributes.get(child_name)
        if not isinstance(child_model, self._child_cls):
            return self._child_cls(
                self,
                self.prim,
                self.context_name,
                self.usd_context,
                self.plugin,
                self.pause,
                proxy_attribute,
            )
        if proxy_attribute and "update_proxy_attribute" in dir(child_model):
            child_model.update_proxy_attribute(proxy_attribute)
        return child_model

    def _sync_group_children(
        self, grouped_proxy_attributes: Dict[str, list[Tuple[Any, str]]], ordered_children: Sequence[str]
    ) -> None:
        """Sync grouped child models and collect child port names."""
        for child_name in ordered_children:
            if child_name not in grouped_proxy_attributes:
                continue
            child_model = self._children.get(child_name, None)
            if isinstance(child_model, AttributeGroupModel):
                child_model.sync(grouped_proxy_attributes[child_name])
                self._child_ports.extend(child_model.child_ports)

    def _destroy_removed_children(self, old_children: OrderedDict) -> None:
        """Destroy old children that were removed from model."""
        for child_name, child_model in old_children.items():
            if child_name not in self._children and "destroy" in dir(child_model):
                child_model.destroy()

    def create_port(
        self,
        name: str,
        value_type_name: Any,
        unique_name: bool = True,
        variability: Optional[Any] = None,
    ) -> Optional[Any]:
        """Execute create port behavior for material graph workflows."""

        attr_name = name
        if unique_name and attr_name in self._children:
            counter = 1
            while True:
                attr_name = f"{name}{counter:02d}"
                if attr_name not in self._children:
                    break
                counter += 1

        model = self._children.get(attr_name, None)
        if not model:
            model = self._child_cls.create(
                self,
                self.prim,
                self.context_name,
                self.usd_context,
                self.plugin,
                self.pause,
                attr_name,
                value_type_name,
                variability=variability,
            )
            if model:
                self._children[attr_name] = model
                self._update_child_cache(self._children)
        return model

    def destroy(self) -> None:
        """Execute destroy behavior for material graph workflows."""

        for child in self._children.values():
            if "destroy" in dir(child):
                child.destroy()
        self._children = OrderedDict()
        self._child_ports = []
        self._invalidate_child_paths_cache()
        self._invalidate_incoming_cache()
        super().destroy()

    def get_child_by_path(self, path: Any) -> Optional[Any]:
        """Execute get child by path behavior for material graph workflows."""

        if not (isinstance(path, Sdf.Path) and path.IsPrimPropertyPath()):
            return None
        for child in self._children.values():
            if isinstance(child, self._child_cls):
                if child.path == path:
                    return child
            else:
                res = child.get_child_by_path(path)
                if res:
                    return res

    def get_connected_prims(self, recurse_nodegraphs: bool = True) -> List[Any]:
        """Execute get connected prims behavior for material graph workflows."""

        connected = []
        for port in self.ports:
            connected.extend(port.get_connected_prims(recurse_nodegraphs))
        return list(set(connected))
