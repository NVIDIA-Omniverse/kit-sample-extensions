"""Isolation graph model wrappers for temporary input/output node projection."""

from typing import List, Optional

from omni.kit.widget.graph import IsolationGraphModel
from pxr import Sdf, UsdShade, UsdUI

from ...api.context_menu import get_node_menu_items
from ...config.logging import logger
from ...utils.usd_names import is_internal_nodegraph_interface_connection
from .ports.internal.validation import would_create_cycle as would_create_prim_cycle

_ProxyAttribute = None


def _get_proxy_attribute_cls():
    global _ProxyAttribute
    if _ProxyAttribute is None:
        from .ports.proxy import ProxyAttribute

        _ProxyAttribute = ProxyAttribute
    return _ProxyAttribute


def _resolve_node_class(
    owner_cls: type,
    instance: Optional[object],
    name: str,
) -> Optional[type]:
    """Return the concrete node class for a nested IsolationGraphModel type.

    IsolationGraphModel defines nested classes like InputNode/OutputNode/EmptyPort,
    and exposes these via property descriptors (used by a wrapper
    metaclass). When that happens, `IsolationGraphModel.InputNode` is a property
    object rather than a usable class, and attempting to subclass or instantiate
    it raises "property object is not callable". This helper resolves the actual
    class in a build-agnostic way:
    - If the attribute is a concrete class in the class dict, return it.
    - If the attribute is a property, call its fget on an instance to obtain
      the real class.
    - If resolution fails, return None so the caller can fall back safely.
    """
    base = owner_cls.__dict__.get(name)
    if isinstance(base, type):
        return base
    if isinstance(base, property):
        target = instance if instance is not None else object.__new__(owner_cls)
        try:
            base = base.fget(target)
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
            logger.debug("_resolve_node_class property fget failed: %s", exc)
            return None
    if isinstance(base, type):
        return base
    return None


def _build_input_node_class(base_cls: Optional[type], empty_port_cls: Optional[type]) -> type:
    """Create a material-graph InputNode type with filtered ports.

    Why we build a dedicated class:
    - We must avoid subclassing property-backed InputNode classes, which fail
      at class definition time.
    - The isolation graph expects nodes with a specific interface
      (`__getattr__`, `__hash__`, `get_type_name`, `ports`, `empty_port`).
    - We need to filter out display-group child ports so the UI doesn't render
      duplicates when port groups are expanded.
    This class is intentionally self-contained and does not rely on the base
    """

    class MaterialGraphInputNode(object):
        """Input node that mirrors the IsolationGraphModel InputNode interface."""

        def __init__(self, model: object, source: object) -> None:
            """Initialize the wrapper node around a source prim model."""
            self._model = model
            self._inputs = []
            self.source = source
            if empty_port_cls and getattr(self._model[self.source], "add_empty_input_port", False):
                self.empty_port = empty_port_cls(self)
            else:
                self.empty_port = None

        def __getattr__(self, attr: str) -> object:
            """Delegate attribute access to the underlying source object."""
            return getattr(self.source, attr)

        def __hash__(self) -> int:
            """Hash distinct from the underlying source and OutputNode."""
            return hash((self.source, base_cls.get_type_name()))

        @staticmethod
        def get_type_name() -> str:
            """Return the type name expected by the graph delegate/router."""
            return base_cls.get_type_name()

        @property
        def ports(self) -> Optional[List[object]]:
            """Return only top-level input ports, excluding display-group children."""
            ports = self._model[self.source].ports
            if ports is not None:
                inputs = [(port, self._model[port].inputs) for port in ports]
                self._inputs = [(p, i) for p, i in inputs if i is not None]
                res = [p for p, _ in self._inputs]
                if self.empty_port:
                    res += [self.empty_port]
                return res

    return MaterialGraphInputNode


def _build_output_node_class(base_cls: Optional[type], empty_port_cls: Optional[type]) -> type:
    """Create a material-graph OutputNode type with filtered ports.

    Mirrors the InputNode rationale, but for output ports. We build our own
    class to avoid subclassing property-backed OutputNode definitions and to
    ensure output port grouping does not duplicate child ports in the UI.
    """

    class MaterialGraphOutputNode(object):
        """Output node that mirrors the IsolationGraphModel OutputNode interface."""

        def __init__(self, model: object, source: object) -> None:
            """Initialize the wrapper node around a source prim model."""
            self._model = model
            self._outputs = []
            self.source = source
            if empty_port_cls and getattr(self._model[self.source], "add_empty_output_port", False):
                self.empty_port = empty_port_cls(self)
            else:
                self.empty_port = None

        def __getattr__(self, attr: str) -> object:
            """Delegate attribute access to the underlying source object."""
            return getattr(self.source, attr)

        def __hash__(self) -> int:
            """Hash distinct from the underlying source and InputNode."""
            return hash((self.source, base_cls.get_type_name()))

        @staticmethod
        def get_type_name() -> str:
            """Return the type name expected by the graph delegate/router."""
            return base_cls.get_type_name()

        @property
        def ports(self) -> Optional[List[object]]:
            """Return only top-level output ports, excluding display-group children."""
            ports = self._model[self.source].ports
            if ports is not None:
                outputs = [(port, self._model[port].outputs) for port in ports]
                self._outputs = [(p, o) for p, o in outputs if o is not None]
                res = [p for p, _ in self._outputs]
                if self.empty_port:
                    res += [self.empty_port]
                return res

    return MaterialGraphOutputNode


class MaterialGraphIsolationModel(IsolationGraphModel):
    """Isolation graph model tailored for the material graph.

    This subclass exists to:
    - Provide custom Input/Output node types with port filtering.
    - Work around how IsolationGraphModel exposes node classes
      via properties (which are not subclassable/callable).
    """

    InputNode = None

    _CACHEABLE_ATTRS = frozenset(
        {
            "name",
            "type",
            "ports",
            "expansion_state",
            "stacking_order",
            "description",
            "display_color",
            "size",
            "icon",
            "inputs",
            "outputs",
            "connected_ports",
            "valid",
            "tooltip_text",
            "preview",
            "polymorphic_unresolved",
        }
    )

    class _MaterialGraphIsolationItemProxy(IsolationGraphModel._IsolationItemProxy):
        """Proxy that caches read-only property results on data-descriptor properties."""

        __slots__ = ("_pcache",)

        def __init__(self, model, item, isolation_model):
            super().__init__(model, item, isolation_model)
            object.__setattr__(self, "_pcache", {})

        @property
        def name(self):
            c = object.__getattribute__(self, "_pcache")
            v = c.get("name")
            if v is not None:
                return v[0]
            r = super().name
            c["name"] = (r,)
            return r

        @name.setter
        def name(self, value):
            object.__getattribute__(self, "_pcache").pop("name", None)
            IsolationGraphModel._IsolationItemProxy.name.fset(self, value)

        @property
        def type(self):
            c = object.__getattribute__(self, "_pcache")
            v = c.get("type")
            if v is not None:
                return v[0]
            r = super().type
            c["type"] = (r,)
            return r

        @property
        def expansion_state(self):
            c = object.__getattribute__(self, "_pcache")
            v = c.get("es")
            if v is not None:
                return v[0]
            r = super().expansion_state
            c["es"] = (r,)
            return r

        @expansion_state.setter
        def expansion_state(self, value):
            object.__getattribute__(self, "_pcache").pop("es", None)
            self._model[self._item].expansion_state = value

        @property
        def stacking_order(self):
            c = object.__getattribute__(self, "_pcache")
            v = c.get("so")
            if v is not None:
                return v[0]
            r = super().stacking_order
            c["so"] = (r,)
            return r

        @property
        def display_color(self):
            c = object.__getattribute__(self, "_pcache")
            v = c.get("dc")
            if v is not None:
                return v[0]
            r = super().display_color
            c["dc"] = (r,)
            return r

        @display_color.setter
        def display_color(self, value):
            object.__getattribute__(self, "_pcache").pop("dc", None)
            IsolationGraphModel._IsolationItemProxy.display_color.fset(self, value)

        @property
        def icon(self):
            c = object.__getattribute__(self, "_pcache")
            v = c.get("ic")
            if v is not None:
                return v[0]
            r = super().icon
            c["ic"] = (r,)
            return r

        @property
        def size(self):
            c = object.__getattribute__(self, "_pcache")
            v = c.get("sz")
            if v is not None:
                return v[0]
            r = super().size
            c["sz"] = (r,)
            return r

        @size.setter
        def size(self, value):
            object.__getattribute__(self, "_pcache").pop("sz", None)
            IsolationGraphModel._IsolationItemProxy.size.fset(self, value)

        @property
        def description(self):
            c = object.__getattribute__(self, "_pcache")
            v = c.get("ds")
            if v is not None:
                return v[0]
            r = super().description
            c["ds"] = (r,)
            return r

        @description.setter
        def description(self, value):
            object.__getattribute__(self, "_pcache").pop("ds", None)
            self._model[self._item].description = value

        def _match_type_name(self, item: object, expected: str) -> bool:
            """Return True when item's type-name matches expected node token."""
            try:
                type_name = type(item).get_type_name()
            except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
                logger.debug("_match_type_name get_type_name failed: %s", exc)
                type_name = None
            return type_name == expected

        def is_input_node(self, item: Optional[object] = None) -> bool:
            """Return True for native or wrapped isolation input nodes."""
            if item is None:
                item = self._item
            return super().is_input_node(item) or self._match_type_name(item, "InputNode")

        def is_output_node(self, item: Optional[object] = None) -> bool:
            """Return True for native or wrapped isolation output nodes."""
            if item is None:
                item = self._item
            return super().is_output_node(item) or self._match_type_name(item, "OutputNode")

        def is_empty_port(self, item: Optional[object] = None) -> bool:
            """Return True for native or wrapped isolation empty-port sentinels."""
            if item is None:
                item = self._item
            return super().is_empty_port(item) or self._match_type_name(item, "EmptyPort")

        @property
        def position(self):
            if self.is_input_node() and self._isolation_model._input_position is not None:
                return self._isolation_model._input_position
            if self.is_output_node() and self._isolation_model._output_position is not None:
                return self._isolation_model._output_position
            return IsolationGraphModel._IsolationItemProxy.position.fget(self)

        @position.setter
        def position(self, value):
            IsolationGraphModel._IsolationItemProxy.position.fset(self, value)
            if self.is_input_node():
                self._isolation_model._input_position = value
            elif self.is_output_node():
                self._isolation_model._output_position = value

        def snapshot_node(self):
            """Bulk-extract node attributes in one inner-proxy lookup.

            Returns (name, typ, size_w, pos, color, selected, valid, ports).
            Calling this populates the isolation model's _ports set.
            """
            try:
                inner = self._model[self._item]
                name = str(self.name or "")
                typ = str(inner.type or "")
                sz = inner.size
                size_w = float(sz[0]) if sz and float(sz[0]) > 0 else 200.0
                color = inner.display_color
                selected = bool(getattr(inner, "selected", False))
                valid = bool(getattr(inner, "valid", True))
            except Exception:
                name, typ, size_w, color, selected, valid = "", "", 200.0, None, False, True
            pos = self.position
            ports = self.ports
            return name, typ, size_w, pos, color, selected, valid, ports

        def snapshot_port_meta(self):
            """Bulk-extract port metadata (no connections) in one inner-proxy lookup.

            Returns (name, typ, sub_ports, exp).
            Calling this populates _ports for sub-ports via self.ports.
            """
            if self.is_empty_port():
                return "", "", None, 0
            try:
                inner = self._model[self._item]
                name = str(inner.name or "")
                typ = str(inner.type or "")
                if not typ or "Model" in typ:
                    alt = str(getattr(inner, "type_name", None) or "")
                    if alt:
                        typ = alt
                if not typ or "Model" in typ:
                    alt = str(getattr(inner, "sdf_type", None) or "")
                    if alt:
                        typ = alt
                exp = inner.expansion_state
                if not isinstance(exp, int):
                    try:
                        exp = exp.value
                    except Exception:
                        exp = 0
            except Exception:
                name, typ, exp = "", "", 0
            sub_ports = self.ports
            return name, typ, sub_ports, exp

    def export_snapshot(self, port_grouping: bool, input_node_view_model=None) -> list:
        """Export all node/port data as plain dicts, bypassing isolation proxies.

        For regular nodes, reads attributes directly from the underlying model
        (self._model[item]) — one inner proxy per item, no isolation proxy.
        Manually populates self._ports for connection filtering.
        Input/output nodes (0-2) still use the isolation proxy since they're rare.

        When *input_node_view_model* is provided, InputNode ports are
        classified, grouped, and filtered through the view model instead
        of being emitted as a flat list.
        """
        model = self._model
        nodes_list = self.nodes
        if not nodes_list:
            return []

        snapshot = []
        all_port_entries: list = []
        root_ports_set = set(self._root_ports) if self._root_ports else set()

        for node in nodes_list:
            is_io = hasattr(node, "source")

            is_backdrop = False
            stacking_order = 0
            expansion_state = 0
            description = ""
            size_h = 0.0

            if is_io:
                proxy = self[node]
                try:
                    name, typ, size_w, pos, color, selected, valid, node_ports = proxy.snapshot_node()
                except Exception:
                    name, typ, size_w = "", "", 200.0
                    pos, color, selected, valid = None, None, False, True
                    node_ports = proxy.ports
            else:
                try:
                    inner = model[node]
                    # Snapshot export is a read-only render path. Structural
                    # USD edits must update models before notifying the view;
                    # syncing here would resync every node on simple redraws.
                    name = str(inner.name or "")
                    typ = str(inner.type or "")
                    sz = inner.size
                    size_w = float(sz[0]) if sz and float(sz[0]) > 0 else 200.0
                    color = inner.display_color
                    selected = bool(getattr(inner, "selected", False))
                    valid = bool(getattr(inner, "valid", True))
                    pos = inner.position
                    node_ports = inner.ports
                except Exception:
                    name, typ, size_w = "", "", 200.0
                    pos, color, selected, valid = None, None, False, True
                    node_ports = None
                    inner = None

                if inner is not None:
                    if "Backdrop" in typ:
                        is_backdrop = True
                        try:
                            description = str(inner.description or "")
                        except Exception:
                            pass
                        try:
                            if sz and len(sz) > 1:
                                size_h = float(sz[1])
                        except Exception:
                            pass

                    try:
                        stacking_order = int(inner.stacking_order or 0)
                    except Exception:
                        pass

                    try:
                        exp = inner.expansion_state
                        if not isinstance(exp, int):
                            exp = exp.value
                        expansion_state = int(exp)
                    except Exception:
                        pass

                for p in node_ports or []:
                    self._ports[p] = node
                self._nodes[node] = node_ports

            # Fallback: for invalid nodes with no model ports, discover from USD directly
            if not valid and not is_io and not node_ports:
                try:
                    prim = getattr(node, "prim", None)
                    if prim and prim.IsValid():
                        api = UsdShade.ConnectableAPI(prim)
                        if api:
                            _fallback_ports = []
                            for usd_inp in api.GetInputs():
                                attr = usd_inp.GetAttr()
                                if not attr:
                                    continue
                                _PA = _get_proxy_attribute_cls()
                                pa = _PA(attr.GetName(), False, attribute=attr)
                                pa._fallback_usd_attr = attr
                                pa._fallback_prim = prim
                                _fallback_ports.append(pa)
                            for usd_out in api.GetOutputs():
                                attr = usd_out.GetAttr()
                                if not attr:
                                    continue
                                _PA = _get_proxy_attribute_cls()
                                pa = _PA(attr.GetName(), True, attribute=attr)
                                pa._fallback_usd_attr = attr
                                pa._fallback_prim = prim
                                _fallback_ports.append(pa)
                            if _fallback_ports:
                                node_ports = _fallback_ports
                                for p in node_ports:
                                    self._ports[p] = node
                                self._nodes[node] = node_ports
                except Exception:
                    pass

            # -- IO-node detection (Phase 1 redesign) --
            io_type_name = ""
            if is_io:
                try:
                    io_type_name = type(node).get_type_name()
                except (RuntimeError, ValueError, TypeError, AttributeError):
                    io_type_name = ""
            is_input_node = False
            is_output_node = io_type_name == "OutputNode"
            view_mode = 0
            if is_io and input_node_view_model is not None:
                if io_type_name == "InputNode":
                    is_input_node = True
                    view_mode = input_node_view_model.mode

            ports: list = []
            if node_ports:
                if not is_io and node is getattr(self, "_root", None):
                    node_ports = [
                        port
                        for port in node_ports
                        if not (port in getattr(self, "_root_inputs", {}) and not self._is_material_output_port(port))
                    ]
                if not valid and not is_io and node_ports and isinstance(node_ports[0], _get_proxy_attribute_cls()):
                    self._export_fallback_ports(node_ports, ports, all_port_entries)
                else:
                    self._export_ports(
                        model,
                        node_ports,
                        0,
                        port_grouping,
                        ports,
                        all_port_entries,
                        root_ports_set,
                        is_io,
                        parent_is_output_node=is_output_node,
                    )

            has_menu = bool(get_node_menu_items(typ))
            if not has_menu and not is_io:
                try:
                    prim = getattr(node, "prim", None)
                    if prim and (prim.IsA(UsdShade.NodeGraph) or prim.IsA(UsdShade.Material)):
                        has_menu = bool(get_node_menu_items("NodeGraph"))
                    elif prim and prim.IsA(UsdUI.Backdrop):
                        has_menu = bool(get_node_menu_items("Backdrop"))
                except Exception:
                    pass

            poly_unres = False
            if not is_io and node is not None:
                try:
                    poly_unres = bool(node.polymorphic_unresolved)
                except (AttributeError, TypeError):
                    pass

            ns = {
                "node": node,
                "name": name,
                "type": typ,
                "size_w": size_w,
                "pos": (float(pos[0]), float(pos[1])) if pos else None,
                "color": color,
                "selected": selected,
                "valid": valid,
                "valid_state": self._compute_valid_state(valid, node),
                "ports": ports,
                "is_backdrop": is_backdrop,
                "description": description,
                "stacking_order": stacking_order,
                "expansion_state": expansion_state,
                "size_h": size_h,
                "has_menu": has_menu,
                "polymorphic_unresolved": poly_unres,
            }
            if is_input_node:
                ns["is_input_node"] = True
                ns["view_mode"] = view_mode
            snapshot.append(ns)

        # Phase 2: connections with isolation filtering (_ports is complete)
        _ps = self._ports
        _ri = self._root_inputs
        _ro = self._root_outputs

        # Build USD attribute path → fallback port lookup for cross-referencing
        _PA = _get_proxy_attribute_cls()
        _fallback_by_path = {}
        for port_obj in _ps:
            if isinstance(port_obj, _PA) and hasattr(port_obj, "_fallback_prim"):
                fb_prim = port_obj._fallback_prim
                if fb_prim:
                    key = str(fb_prim.GetPath()) + "." + port_obj.name
                    _fallback_by_path[key] = port_obj

        def _resolve_port(p):
            """Return p if registered, or try matching to a fallback port by USD path."""
            if p in _ps or p in _ri or p in _ro:
                return p
            if not _fallback_by_path:
                return None
            try:
                pa = getattr(p, "proxy_attribute", p)
                attr = getattr(pa, "attribute", None) or getattr(pa, "_usd_attribute", None)
                if attr:
                    key = str(attr.GetPrim().GetPath()) + "." + attr.GetName()
                    fb = _fallback_by_path.get(key)
                    if fb:
                        return fb
            except Exception:
                pass
            return None

        skip_usd_input_recovery = set()
        for port_obj, inner_pp, ps in all_port_entries:
            raw_in, raw_out = self._connection_lists_for_port(port_obj, inner_pp, root_ports_set, _ri, _ro)
            is_graph_sink = bool(ps.get("graph_sink")) or self._is_graph_sink_output_port(port_obj, root_ports_set)
            if is_graph_sink and raw_in is None and raw_out is not None:
                raw_in, raw_out = raw_out, None
            if is_graph_sink and inner_pp is not None and raw_in in (None, []):
                usdshade_port = getattr(port_obj, "usdshade_port", None)
                if usdshade_port is not None and self._has_connected_source(usdshade_port) is False:
                    skip_usd_input_recovery.add(id(port_obj))

            if raw_in is not None:
                ps["inputs"] = [r for i in raw_in if (r := _resolve_port(i)) is not None]
            if raw_out is not None:
                ps["outputs"] = [r for o in raw_out if (r := _resolve_port(o)) is not None]
            if is_graph_sink:
                if ps.get("inputs") is None:
                    ps["inputs"] = []
                ps["outputs"] = None

        # Phase 2b: recover missing connections to fallback ports via USD
        if _fallback_by_path:
            root_prim = getattr(self, "_root", None)
            root_prim_usd = getattr(root_prim, "prim", root_prim) if root_prim else None
            for port_obj, inner_pp, ps in all_port_entries:
                if id(port_obj) in skip_usd_input_recovery:
                    continue
                existing_inputs = ps.get("inputs")
                if existing_inputs:
                    continue
                try:
                    attr = None
                    pa = getattr(port_obj, "proxy_attribute", None)
                    if pa is not None:
                        attr = getattr(pa, "attribute", None) or getattr(pa, "_usd_attribute", None)
                        if not attr:
                            node_ref = _ps.get(port_obj)
                            prim = getattr(node_ref, "prim", None) if node_ref else None
                            if prim:
                                attr = prim.GetAttribute(pa.name)
                    if attr is None and port_obj in root_ports_set and root_prim_usd:
                        port_name = ps.get("name", "")
                        if port_name:
                            for prefix in ("outputs:", "inputs:"):
                                candidate = root_prim_usd.GetAttribute(prefix + port_name)
                                if candidate and candidate.IsValid():
                                    attr = candidate
                                    break
                    if not attr:
                        continue
                    shade_port = (
                        UsdShade.Output(attr)
                        if self._is_material_output_port(port_obj) or self._is_output_port(port_obj)
                        else UsdShade.Input(attr)
                    )
                    if not shade_port or not shade_port.HasConnectedSource():
                        continue
                    sources = shade_port.GetConnectedSources()
                    if isinstance(sources, tuple):
                        sources = sources[0]
                    for src in sources or []:
                        src_api = src.source if hasattr(src, "source") else src
                        if not src_api:
                            continue
                        src_prim = src_api.GetPrim()
                        src_name = src.sourceName if hasattr(src, "sourceName") else ""
                        if not src_prim or not src_prim.IsValid() or not src_name:
                            continue
                        src_type = src.sourceType if hasattr(src, "sourceType") else UsdShade.AttributeType.Output
                        prefix = (
                            UsdShade.Tokens.inputs
                            if src_type == UsdShade.AttributeType.Input
                            else UsdShade.Tokens.outputs
                        )
                        key = str(src_prim.GetPath()) + f".{prefix}{src_name}"
                        fb = _fallback_by_path.get(key)
                        if fb:
                            if ps.get("inputs") is None:
                                ps["inputs"] = []
                            ps["inputs"].append(fb)
                except Exception:
                    pass

        # Build set of all port objects involved in any connection
        connected_port_objs = set()
        for _, _, ps in all_port_entries:
            port_obj = ps.get("port")
            has_conn = False
            for src in ps.get("inputs") or []:
                connected_port_objs.add(id(src))
                has_conn = True
            for tgt in ps.get("outputs") or []:
                connected_port_objs.add(id(tgt))
                has_conn = True
            if has_conn and port_obj is not None:
                connected_port_objs.add(id(port_obj))

        # Phase 3: filter ports by node expansion state
        for ns in snapshot:
            exp = ns.get("expansion_state", 0)
            if exp == 1:  # MINIMIZED — keep only connected ports
                ns["ports"] = [p for p in ns["ports"] if id(p.get("port")) in connected_port_objs or p.get("is_empty")]
            elif exp == 2:  # CLOSED — replace with collapsed port circles
                all_ports = ns["ports"]
                first_in_port = None
                first_out_port = None
                all_inputs = []
                all_outputs = []
                for p in all_ports:
                    port_obj = p.get("port")
                    if port_obj is None:
                        continue
                    # Root material outputs are graph sinks. When collapsed,
                    # they intentionally aggregate through the input-side circle.
                    for src in p.get("inputs") or []:
                        all_inputs.append(src)
                        if first_in_port is None:
                            first_in_port = port_obj
                    if id(port_obj) in connected_port_objs and p.get("outputs") is not None:
                        for tgt in p.get("outputs") or []:
                            all_outputs.append(tgt)
                        if first_out_port is None:
                            first_out_port = port_obj
                collapsed = []
                if first_in_port is not None:
                    collapsed.append(
                        {
                            "port": first_in_port,
                            "name": "",
                            "type": "",
                            "level": 0,
                            "exp": 0,
                            "is_group": False,
                            "sub_count": 0,
                            "inputs": all_inputs,
                            "outputs": None,
                            "is_empty": True,
                        }
                    )
                if first_out_port is not None:
                    collapsed.append(
                        {
                            "port": first_out_port,
                            "name": "",
                            "type": "",
                            "level": 0,
                            "exp": 0,
                            "is_group": False,
                            "sub_count": 0,
                            "inputs": None,
                            "outputs": all_outputs,
                            "is_empty": True,
                        }
                    )
                ns["ports"] = collapsed

        # Phase 3b: tag ports involved in invalid connections
        inv_conn_paths = getattr(self, "_invalid_connection_paths", None) or set()
        if inv_conn_paths:
            for ns in snapshot:
                node_obj = ns.get("node")
                node_prim = getattr(node_obj, "prim", None) if node_obj else None
                if not node_prim:
                    continue
                node_path = str(node_prim.GetPath())
                for ps in ns.get("ports", []):
                    port_obj = ps.get("port")
                    if port_obj is None:
                        continue
                    try:
                        pa = getattr(port_obj, "proxy_attribute", None)
                        if pa is None:
                            continue
                        attr_name = str(pa.name)
                        full_path = node_path + "." + attr_name
                        if full_path in inv_conn_paths:
                            ps["has_error"] = True
                    except Exception:
                        pass

        # Phase 4: InputNode view-model post-processing
        # Uses connected_port_objs (built in Phase 2) as the authoritative
        # source for which ports have connections in the current context.
        if input_node_view_model is not None:
            from .input_node_view import InputNodeViewMode, IoState

            for ns in snapshot:
                if not ns.get("is_input_node"):
                    continue
                vm = input_node_view_model
                mode = vm.mode
                old_ports = ns["ports"]

                # --- Step 1: Classify every leaf port + context membership ---
                # Build a set of attribute names that have USD connections
                # (for cross-context USED_IN_OTHER detection).
                root_prim = None
                input_node_obj = ns.get("node")
                if input_node_obj is not None:
                    src = getattr(input_node_obj, "source", None)
                    if src is not None:
                        root_prim = getattr(src, "prim", None)

                ctx_name = getattr(vm, "_current_context", "")
                ctx_mgr = getattr(vm, "_context_manager_ref", None)
                all_ctx_names = []
                if ctx_mgr:
                    try:
                        # get_context_names() only returns CREATED contexts.
                        # Use get_plugins() to discover ALL available contexts
                        # so we can probe uncreated ones.
                        all_ctx_names = list(ctx_mgr.get_context_names())
                        try:
                            for plugin in ctx_mgr.get_plugins():
                                pn = getattr(plugin, "name", None) or getattr(plugin, "context_name", None)
                                if pn and pn not in all_ctx_names:
                                    all_ctx_names.append(pn)
                        except Exception:
                            pass
                    except Exception:
                        pass

                # Build attribute-name set for current context's connected ports
                # and save it in the cross-context cache.
                current_connected_attrs = set()
                for ps2 in old_ports:
                    po2 = ps2.get("port")
                    if po2 is not None and id(po2) in connected_port_objs:
                        aname = self._port_attr_name(po2)
                        if aname:
                            current_connected_attrs.add(aname)
                if ctx_name:
                    vm._ctx_connected_attrs[ctx_name] = current_connected_attrs

                # Proactively populate cache for uncached contexts by walking
                # their MaterialModel's port tree.  One-time cost per context.
                if ctx_mgr:
                    for cn in all_ctx_names:
                        if cn == ctx_name or cn in vm._ctx_connected_attrs:
                            continue
                        vm._ctx_connected_attrs[cn] = self._probe_context_connections(
                            cn,
                            ctx_mgr,
                        )

                # Build the cross-context lookup: attr names used by OTHER contexts
                other_ctx_attrs: dict = {}  # attr_name -> [ctx_names]
                for cn, attr_set in vm._ctx_connected_attrs.items():
                    if cn == ctx_name:
                        continue
                    for aname in attr_set:
                        other_ctx_attrs.setdefault(aname, []).append(cn)

                for ps in old_ports:
                    port_obj = ps.get("port")
                    if ps.get("is_group"):
                        ps["io_state"] = -1
                        continue
                    if ps.get("is_empty"):
                        ps["io_state"] = -1
                        continue

                    pid = id(port_obj) if port_obj is not None else None

                    # Priority 1: ACTIVE if connected in current context
                    if pid is not None and pid in connected_port_objs:
                        ps["io_state"] = IoState.ACTIVE_IN_CURRENT
                        if pid is not None:
                            vm._port_contexts[pid] = [ctx_name] if ctx_name else []
                        continue

                    # Priority 2: check cross-context cache for USED_IN_OTHER
                    attr_name = self._port_attr_name(port_obj) if port_obj else ""
                    used_by = other_ctx_attrs.get(attr_name, []) if attr_name else []

                    if used_by:
                        ps["io_state"] = IoState.USED_IN_OTHER
                        if pid is not None:
                            vm._port_contexts[pid] = list(used_by)
                    else:
                        ps["io_state"] = IoState.UNUSED
                        if pid is not None:
                            vm._port_contexts[pid] = []
                # --- Step 2: Propagate group state from children ---
                i = 0
                while i < len(old_ports):
                    ps = old_ports[i]
                    if ps.get("is_group") and ps.get("io_state", -1) == -1:
                        gl = ps.get("level", 0)
                        has_active = False
                        has_other = False
                        has_any = False
                        j = i + 1
                        while j < len(old_ports):
                            cp = old_ports[j]
                            if cp.get("level", 0) <= gl:
                                break
                            if not cp.get("is_group") and not cp.get("is_empty"):
                                has_any = True
                                cio = cp.get("io_state", 2)
                                if cio == IoState.ACTIVE_IN_CURRENT:
                                    has_active = True
                                elif cio == IoState.USED_IN_OTHER:
                                    has_other = True
                            j += 1
                        if has_active:
                            ps["io_state"] = IoState.ACTIVE_IN_CURRENT
                        elif has_other:
                            ps["io_state"] = IoState.USED_IN_OTHER
                        else:
                            ps["io_state"] = IoState.UNUSED
                    i += 1

                # --- Step 3: Filter by view mode ---
                other_expanded = getattr(vm, "_other_group_expanded", False)

                if mode == InputNodeViewMode.CURRENT_CONTEXT:
                    ns["ports"] = self._phase4_current_context(old_ports, other_expanded, IoState, vm)
                elif mode == InputNodeViewMode.ALL_USED:
                    ns["ports"] = self._phase4_all_used(old_ports, IoState)
                # ALL_PORTS: keep everything, io_state is already injected

        return snapshot

    # -- Phase 4 view-mode helpers ------------------------------------------

    @staticmethod
    def _walk_group(old_ports, start, level):
        """Collect children of a group at *start* until level drops back."""
        children = []
        j = start + 1
        while j < len(old_ports):
            if old_ports[j].get("level", 0) <= level:
                break
            children.append(old_ports[j])
            j += 1
        return children, j

    def _phase4_current_context(self, old_ports, other_expanded, IoState, vm):
        """CURRENT_CONTEXT: active groups visible, non-active marked hidden
        (zero-height but still provide connection anchors), summary rows
        for Other/Unused, EmptyPort always last."""
        active_entries = []
        other_entries = []
        unused_entries = []
        empty_entries = []

        _COLLAPSE_THRESHOLD = 8

        i = 0
        while i < len(old_ports):
            ps = old_ports[i]
            if ps.get("is_empty"):
                empty_entries.append(ps)
                i += 1
                continue
            if ps.get("is_group"):
                gl = ps.get("level", 0)
                children, j = self._walk_group(old_ports, i, gl)
                gio = ps.get("io_state", 2)
                if gio == IoState.ACTIVE_IN_CURRENT:
                    active_entries.append(ps)
                    active_entries.extend(children)
                elif gio == IoState.USED_IN_OTHER:
                    other_entries.append(ps)
                    other_entries.extend(children)
                else:
                    unused_entries.append(ps)
                    unused_entries.extend(children)
                i = j
            else:
                pio = ps.get("io_state", 2)
                if pio == IoState.ACTIVE_IN_CURRENT:
                    active_entries.append(ps)
                elif pio == IoState.USED_IN_OTHER:
                    other_entries.append(ps)
                else:
                    unused_entries.append(ps)
                i += 1

        # --- Active semantic pages (top level, never wrapped) ---
        filtered = list(active_entries)

        # Apply collapse policy to active groups
        group_indices = [k for k, p in enumerate(filtered) if p.get("is_group")]
        collapse_state = getattr(vm, "_group_collapse_state", {})
        if group_indices:
            for gi in group_indices:
                gp = filtered[gi]
                gname = gp.get("name", "")
                persisted = collapse_state.get(gname)
                if persisted is not None:
                    gp["exp"] = 2 if persisted else 0
                else:
                    children_of_g, _ = self._walk_group(filtered, gi, gp.get("level", 0))
                    if len(children_of_g) > _COLLAPSE_THRESHOLD:
                        gp["exp"] = 2
            if group_indices and all(filtered[gi].get("exp") == 2 for gi in group_indices):
                filtered[group_indices[0]]["exp"] = 0

        # --- "Other context ports" collapsed summary ---
        other_leaf = sum(1 for p in other_entries if not p.get("is_group") and not p.get("is_empty"))
        vm._other_summary_port_index = len(filtered) if other_entries else -1
        if other_entries:
            filtered.append(
                self._make_summary_row(
                    "Other context ports",
                    other_leaf,
                    other_expanded,
                    IoState.USED_IN_OTHER,
                )
            )
            if other_expanded:
                filtered.extend(other_entries)

        # --- "Unused ports" collapsed summary ---
        unused_leaf = sum(1 for p in unused_entries if not p.get("is_group") and not p.get("is_empty"))
        unused_expanded = getattr(vm, "_unused_group_expanded", False)
        if unused_leaf > 0:
            filtered.append(
                self._make_summary_row(
                    "Unused ports",
                    unused_leaf,
                    unused_expanded,
                    IoState.UNUSED,
                )
            )
            if unused_expanded:
                filtered.extend(unused_entries)

        # --- EmptyPort (Add Port) always last ---
        filtered.extend(empty_entries)

        # --- Apply group collapse state to ALL groups ---
        # When a group is collapsed, set exp=2 AND remove its children
        # from the list (since _export_ports already expanded them).
        collapse_state = getattr(vm, "_group_collapse_state", {})
        if collapse_state:
            new_filtered = []
            skip_until_level = -1
            for p in filtered:
                lvl = p.get("level", 0)
                # If we're skipping children of a collapsed group
                if skip_until_level >= 0:
                    if lvl > skip_until_level:
                        continue  # skip this child
                    else:
                        skip_until_level = -1  # done skipping

                if p.get("is_group") and not p.get("is_group_header"):
                    gname = p.get("name", "")
                    persisted = collapse_state.get(gname)
                    if persisted:
                        p["exp"] = 2
                        skip_until_level = lvl  # skip children at deeper levels
                    elif persisted is not None:
                        p["exp"] = 0
                new_filtered.append(p)
            filtered = new_filtered

        # --- Store synthetic row indices for click handling ---
        synth = {}
        for idx, p in enumerate(filtered):
            nm = p.get("name", "")
            if nm == "Other context ports":
                synth["other"] = idx
            elif nm == "Unused ports":
                synth["unused"] = idx
        vm._synthetic_row_indices = synth

        # Map scene index → model port object for ALL ports (groups, leaves, empty)
        port_map = {}
        group_indices = set()
        for idx, p in enumerate(filtered):
            po = p.get("port")
            if po is not None:
                port_map[idx] = po
            if p.get("is_group") or p.get("is_group_header"):
                group_indices.add(idx)
        vm._scene_idx_to_port = port_map
        vm._scene_group_indices = group_indices

        # Debug: log final structure
        return filtered

    @staticmethod
    def _probe_context_connections(ctx_name, ctx_mgr):
        """Build a temporary isolation model for another context and run
        export_snapshot to get the full set of connected port attribute names.

        This is 100% accurate (uses the same connection pass as the renderer)
        and runs once per uncached context on first encounter.
        """
        result = set()
        try:
            handle = ctx_mgr.get_context(ctx_name)
            if not handle.is_valid or not handle.context:
                return result
            model = handle.context.model
            if model is None:
                return result

            # Find the root item for the isolation model.
            # The model itself is the root for top-level materials.
            root = None
            try:
                nodes = model.nodes
                if nodes:
                    root = model
            except Exception:
                pass
            if root is None:
                return result

            # Create a temporary isolation model (no UI state needed)
            temp_iso = MaterialGraphIsolationModel(model, root)
            try:
                snapshot = temp_iso.export_snapshot(True)
                # Extract connected port attribute names from the snapshot
                for ns in snapshot:
                    for ps in ns.get("ports", []):
                        port_obj = ps.get("port")
                        if port_obj is None:
                            continue
                        has_in = bool(ps.get("inputs"))
                        has_out = bool(ps.get("outputs"))
                        if has_in or has_out:
                            aname = ""
                            try:
                                proxy = getattr(port_obj, "proxy_attribute", None)
                                if proxy:
                                    aname = proxy.name
                            except Exception:
                                pass
                            if aname:
                                result.add(aname)
            finally:
                try:
                    temp_iso.destroy()
                except Exception:
                    pass
        except Exception:
            pass
        return result

    @staticmethod
    def _port_attr_name(port_obj):
        """Return the USD attribute name for a port, or empty string."""
        try:
            proxy = getattr(port_obj, "proxy_attribute", None)
            if proxy is not None:
                return proxy.name
        except Exception:
            pass
        try:
            return str(getattr(port_obj, "attribute_name", ""))
        except Exception:
            return ""

    @staticmethod
    def _identify_port_contexts(port_obj, current_ctx, ctx_mgr):
        """Return list of context names that use *port_obj*, excluding current."""
        result = []
        if ctx_mgr is None:
            return result
        try:
            for cn in ctx_mgr.get_context_names():
                if cn == current_ctx:
                    continue
                handle = ctx_mgr.get_context(cn)
                if not handle.is_valid:
                    continue
                model = handle.context.model
                if model is None:
                    continue
                # Check if port's attribute name exists and is connected
                # in this context's model by walking the model's ports.
                try:
                    pp = model[port_obj]
                    cp = pp.connected_ports
                    if cp:
                        result.append(cn)
                        continue
                except Exception:
                    pass
                # Fallback: check inputs/outputs
                try:
                    pp = model[port_obj]
                    ins = pp.inputs
                    outs = pp.outputs
                    if (ins and len(ins) > 0) or (outs and len(outs) > 0):
                        result.append(cn)
                except Exception:
                    pass
        except Exception:
            pass
        return result

    @staticmethod
    def _make_summary_row(name, leaf_count, expanded, io_state):
        """Create a synthetic collapsed/expanded summary group header."""
        return {
            "port": None,
            "_pp": None,
            "name": name,
            "type": "",
            "inputs": None,
            "outputs": None,
            "is_group": True,
            "sub_count": leaf_count,
            "exp": 0 if expanded else 2,
            "level": 0,
            "rel_pos": 0,
            "parent_count": 0,
            "poly_unresolved": False,
            "is_uniform": False,
            "is_interface_only": False,
            "io_state": io_state,
            "is_group_header": True,
            "group_port_count": leaf_count,
            "group_collapsed": not expanded,
        }

    def _phase4_all_used(self, old_ports, IoState):
        """ALL_USED: active groups first, then non-active groups (no unused leaf ports)."""
        result = []
        i = 0
        while i < len(old_ports):
            ps = old_ports[i]
            if ps.get("is_empty"):
                result.append(ps)
                i += 1
                continue
            if ps.get("is_group"):
                gl = ps.get("level", 0)
                children, j = self._walk_group(old_ports, i, gl)
                # Keep the group if it has any non-unused children
                useful = [
                    c
                    for c in children
                    if c.get("io_state", 2) != IoState.UNUSED or c.get("is_group") or c.get("is_empty")
                ]
                if useful or ps.get("io_state", 2) == IoState.ACTIVE_IN_CURRENT:
                    result.append(ps)
                    result.extend(useful if useful else children)
                i = j
            else:
                if ps.get("io_state", 2) != IoState.UNUSED:
                    result.append(ps)
                i += 1
        return result

    def _export_ports(
        self,
        model,
        port_list,
        level,
        pg,
        out,
        all_entries,
        root_ports_set,
        is_io,
        parent_child_count=0,
        parent_is_output_node=False,
    ):
        """Recursively extract port metadata, bypassing isolation proxies."""
        _EmptyPort = IsolationGraphModel.EmptyPort
        real_index = 0
        for port in port_list:
            if isinstance(port, _EmptyPort):
                try:
                    parent_type_name = type(port.parent).get_type_name()
                except (RuntimeError, ValueError, TypeError, AttributeError):
                    parent_type_name = ""
                parent_is_input = parent_type_name == "InputNode" or (
                    not parent_type_name and hasattr(port.parent, "_inputs") and not hasattr(port.parent, "_outputs")
                )
                parent_is_output = parent_type_name == "OutputNode" or (
                    not parent_type_name and hasattr(port.parent, "_outputs") and not hasattr(port.parent, "_inputs")
                )
                ps = {
                    "port": port,
                    "name": "EmptyPort",
                    "type": "",
                    "level": level,
                    "exp": 0,
                    "is_group": False,
                    "sub_count": 0,
                    "inputs": [] if not parent_is_input else None,
                    "outputs": [] if parent_is_input else None,
                    "is_empty": True,
                    "graph_sink": parent_is_output,
                }
                out.append(ps)
                all_entries.append((port, None, ps))
                continue

            if is_io:
                proxy = self[port]
                try:
                    name, typ, sub_ports, exp = proxy.snapshot_port_meta()
                except Exception:
                    name, typ, sub_ports, exp = "", "", None, 0
                try:
                    inner_pp = model[port] if model is not None else None
                except Exception:
                    inner_pp = None
            else:
                try:
                    inner = model[port]
                    name = str(inner.name or "")
                    typ = str(inner.type or "")
                    if not typ or "Model" in typ:
                        alt = str(getattr(inner, "type_name", None) or "")
                        if alt:
                            typ = alt
                    if not typ or "Model" in typ:
                        alt = str(getattr(inner, "sdf_type", None) or "")
                        if alt:
                            typ = alt
                    exp = inner.expansion_state
                    if not isinstance(exp, int):
                        try:
                            exp = exp.value
                        except Exception:
                            exp = 0
                    sub_ports = inner.ports
                    inner_pp = inner
                except Exception:
                    name, typ, exp = "", "", 0
                    sub_ports = None
                    inner_pp = None

                for sp in sub_ports or []:
                    self._ports[sp] = port

            is_group = pg and sub_ports is not None and len(sub_ports) > 0
            sub_count = len(sub_ports) if is_group else 0

            port_poly_unres = False
            port_is_uniform = False
            port_is_ifo = False
            try:
                port_poly_unres = bool(port.proxy_attribute.polymorphic_unresolved)
            except (AttributeError, TypeError):
                pass
            try:
                port_is_uniform = port.proxy_attribute.variability == Sdf.VariabilityUniform
            except (AttributeError, TypeError):
                pass
            try:
                port_is_ifo = port.proxy_attribute.connectability == UsdShade.Tokens.interfaceOnly
            except (AttributeError, TypeError):
                pass

            ps = {
                "port": port,
                "_pp": None,
                "name": name,
                "type": typ,
                "inputs": None,
                "outputs": None,
                "is_group": is_group,
                "sub_count": sub_count,
                "exp": exp,
                "level": level,
                "rel_pos": real_index,
                "parent_count": parent_child_count,
                "poly_unresolved": port_poly_unres,
                "is_uniform": port_is_uniform,
                "is_interface_only": port_is_ifo,
            }
            if self._is_material_output_port(port) or parent_is_output_node:
                # Material outputs are connection targets in the graph UI, even
                # though USD authors them as UsdShade outputs; OutputNode ports
                # use the same left-side graph sink convention.
                ps["inputs"] = []
                ps["outputs"] = None
                ps["graph_sink"] = True
            real_index += 1
            out.append(ps)
            all_entries.append((port, inner_pp, ps))

            if is_group and sub_count > 0 and exp == 0:
                self._export_ports(
                    model,
                    sub_ports,
                    level + 1,
                    pg,
                    out,
                    all_entries,
                    root_ports_set,
                    is_io,
                    parent_child_count=sub_count,
                    parent_is_output_node=parent_is_output_node,
                )

    def _compute_valid_state(self, valid: bool, node) -> int:
        """Return 0=valid, 1=warning, 2=error based on validity and warning paths."""
        if valid:
            return 0
        warning_paths = getattr(self, "_warning_node_paths", None) or set()
        if warning_paths:
            try:
                prim = getattr(node, "prim", None)
                if prim:
                    prim_path = str(prim.GetPath())
                    if prim_path in warning_paths:
                        return 1
            except Exception:
                pass
        return 2

    @staticmethod
    def _is_material_output_port(port: object) -> bool:
        """Return True for root material outputs that render as graph sinks."""
        try:
            prim = getattr(port, "prim", None)
            proxy = getattr(port, "proxy_attribute", None)
            return bool(
                prim
                and prim.IsA(UsdShade.Material)
                and proxy is not None
                and str(getattr(proxy, "name", "")).startswith(UsdShade.Tokens.outputs)
            )
        except (RuntimeError, ValueError, TypeError, AttributeError):
            return False

    @staticmethod
    def _is_output_port(port: object) -> bool:
        """Return True for authored UsdShade output attribute models."""
        try:
            proxy = getattr(port, "proxy_attribute", None)
            return bool(proxy is not None and str(getattr(proxy, "name", "")).startswith(UsdShade.Tokens.outputs))
        except (RuntimeError, ValueError, TypeError, AttributeError):
            return False

    def _is_graph_sink_output_port(self, port: object, root_ports_set: set) -> bool:
        """Return True for USD outputs rendered as input-side graph sinks."""
        return self._is_material_output_port(port) or (port in root_ports_set and self._is_output_port(port))

    @staticmethod
    def _connected_source_paths(usdshade_port: object) -> set:
        """Return connected source attribute paths for a UsdShade input/output port."""
        if usdshade_port is None:
            return set()
        if MaterialGraphIsolationModel._has_connected_source(usdshade_port) is not True:
            return set()
        sources = usdshade_port.GetConnectedSources()
        if isinstance(sources, tuple):
            sources = sources[0]
        paths = set()
        for src in sources or []:
            src_api = src.source if hasattr(src, "source") else src
            if not src_api:
                continue
            src_prim = src_api.GetPrim()
            src_name = src.sourceName if hasattr(src, "sourceName") else ""
            if not src_prim or not src_prim.IsValid() or not src_name:
                continue
            src_type = src.sourceType if hasattr(src, "sourceType") else UsdShade.AttributeType.Output
            prefix = UsdShade.Tokens.inputs if src_type == UsdShade.AttributeType.Input else UsdShade.Tokens.outputs
            paths.add(src_prim.GetPath().AppendProperty(f"{prefix}{src_name}"))
        return paths

    @staticmethod
    def _has_connected_source(usdshade_port: object) -> Optional[bool]:
        """Return whether a UsdShade port has any authored connected source."""
        try:
            return bool(usdshade_port and usdshade_port.HasConnectedSource())
        except (RuntimeError, ValueError, TypeError, AttributeError):
            return None

    def _connection_lists_for_port(self, port_obj, inner_pp, root_ports_set, root_inputs, root_outputs):
        """Return source and target lists for a snapshot port entry.

        Material outputs are USD outputs rendered as graph sinks. Prefer the
        synced port model first so an empty post-disconnect list beats stale
        root-output isolation cache data; use the root cache only when no inner
        port model exists yet.
        """
        if self._is_material_output_port(port_obj):
            if inner_pp is not None:
                raw_in = inner_pp.outputs
                if raw_in:
                    raw_in = self._filter_connected_sources(port_obj, raw_in)
                return raw_in, None
            return root_outputs.get(port_obj) if port_obj in root_ports_set else None, None
        if port_obj in root_ports_set:
            if self._is_output_port(port_obj) and inner_pp is not None:
                return inner_pp.outputs, None
            if self._is_output_port(port_obj):
                raw_in = root_outputs.get(port_obj)
                if raw_in:
                    raw_in = self._filter_connected_sources(port_obj, raw_in)
                return raw_in, None
            return root_outputs.get(port_obj), root_inputs.get(port_obj)
        if inner_pp is not None:
            return inner_pp.inputs, inner_pp.outputs
        return None, None

    def _filter_connected_sources(self, port_obj, sources):
        """Keep only cached source models that still match live USD source paths."""
        try:
            connected_paths = self._connected_source_paths(getattr(port_obj, "usdshade_port", None))
            if not connected_paths:
                return []
            return [source for source in sources if getattr(source, "path", None) in connected_paths]
        except (RuntimeError, ValueError, TypeError, AttributeError):
            return []

    def _export_fallback_ports(self, proxy_attrs, out, all_entries):
        """Export ports from raw ProxyAttribute objects for invalid nodes with no model ports."""
        _ps = self._ports
        for pa in proxy_attrs:
            is_out = pa._is_output
            typ_name = str(pa.type_name or "")
            port_name = pa.name
            if port_name.startswith("inputs:"):
                port_name = port_name[7:]
            elif port_name.startswith("outputs:"):
                port_name = port_name[8:]

            port_is_uniform = False
            port_is_ifo = False
            try:
                port_is_uniform = pa.variability == Sdf.VariabilityUniform
            except (AttributeError, TypeError):
                pass
            try:
                port_is_ifo = pa.connectability == UsdShade.Tokens.interfaceOnly
            except (AttributeError, TypeError):
                pass

            ps = {
                "port": pa,
                "_pp": None,
                "name": port_name,
                "type": typ_name,
                "inputs": [] if not is_out else None,
                "outputs": [] if is_out else None,
                "is_group": False,
                "sub_count": 0,
                "exp": 0,
                "level": 0,
                "rel_pos": 0,
                "parent_count": 0,
                "poly_unresolved": False,
                "is_uniform": port_is_uniform,
                "is_interface_only": port_is_ifo,
            }
            out.append(ps)
            all_entries.append((pa, None, ps))

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialize the isolation model with build-safe node classes.

        The base IsolationGraphModel constructor instantiates InputNode/OutputNode
        directly from the class attributes on IsolationGraphModel. If those
        attributes are properties, the constructor raises at runtime. We
        therefore resolve and install concrete node classes *before* calling
        super().__init__ to guarantee the base class sees callable types.
        """
        self._proxy_cache: dict = {}
        base_input = _resolve_node_class(IsolationGraphModel, self, IsolationGraphModel.InputNode.get_type_name())
        empty_port_cls = _resolve_node_class(IsolationGraphModel, self, IsolationGraphModel.EmptyPort.get_type_name())
        input_node_cls = _build_input_node_class(base_input, empty_port_cls)
        IsolationGraphModel.InputNode = input_node_cls
        self.__class__.InputNode = input_node_cls

        base_output = _resolve_node_class(IsolationGraphModel, self, IsolationGraphModel.OutputNode.get_type_name())
        output_node_cls = _build_output_node_class(base_output, empty_port_cls)
        IsolationGraphModel.OutputNode = output_node_cls
        self.__class__.OutputNode = output_node_cls
        self._invalid_connection_paths: set = set()
        self._warning_node_paths: set = set()
        super().__init__(*args, **kwargs)

    def clear_caches(self) -> None:
        """Clear caches while preserving IO node positions when last port is removed."""
        prev_input_pos = None
        prev_output_pos = None
        try:
            if getattr(self, "_input_nodes", None):
                prev_input_pos = self[self._input_nodes[0]].position
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
            logger.debug("clear_caches prev_input_pos capture failed: %s", exc)
            prev_input_pos = None
        try:
            if getattr(self, "_output_nodes", None):
                prev_output_pos = self[self._output_nodes[0]].position
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
            logger.debug("clear_caches prev_output_pos capture failed: %s", exc)
            prev_output_pos = None

        self._proxy_cache.clear()
        super().clear_caches()

        if prev_input_pos is not None:
            self._input_position = prev_input_pos
        if prev_output_pos is not None:
            self._output_position = prev_output_pos

    @property
    def root(self, item: Optional[object] = None) -> object:
        """Return the isolation root model or the item's root for proxies."""
        return item.root if item else self._root

    def __getitem__(self, item: object) -> object:
        """Return a cached proxy that understands custom input/output nodes."""
        key = id(item)
        proxy = self._proxy_cache.get(key)
        if proxy is None:
            proxy = self._MaterialGraphIsolationItemProxy(self._model, item, self)
            self._proxy_cache[key] = proxy
        return proxy

    def add_input_or_output(self, position: object, is_input: bool = True) -> bool:
        """Add an input/output node only after its root position was authored."""
        if position is None:
            return False
        if self._root.add_input_or_output(position, is_input) is False:
            return False
        result = super().add_input_or_output(position, is_input)
        return result is not False

    def position_begin_edit(self, item: object) -> None:
        """Forward drag-begin edits to the root graph model."""
        if self._root and hasattr(self._root, "position_begin_edit"):
            self._root.position_begin_edit(item)

    def position_end_edit(self, item: Optional[object]) -> None:
        """Forward drag-end edits to the root graph model."""
        if self._root and hasattr(self._root, "position_end_edit"):
            self._root.position_end_edit(item)

    def can_connect(self, source: object, target: object) -> bool:
        """Allow interfaceOnly connections from their InputNode/OutputNode wrapper ports.

        The base IsolationGraphModel.can_connect handles EmptyPort.
        The plugin's can_connect checks interfaceOnly by looking at the
        port's immediate parent for "source", which fails for InputNode
        ports (their parent is AttributeGroupModel, not InputNode).
        We intercept here where we know about IO nodes.
        """
        if isinstance(source, IsolationGraphModel.EmptyPort) or isinstance(target, IsolationGraphModel.EmptyPort):
            return True

        if self._is_nodegraph_output_sink_connection(source, target):
            if self._model.can_connect(source, target):
                return True
            if self._is_internal_nodegraph_interface_connection(source, target):
                return True
            return self._is_polymorphic_nodegraph_output_sink_connection(source, target)

        if self._is_internal_nodegraph_interface_connection(source, target):
            return True

        # Check if either port belongs to an IO node
        src_is_io = self._is_root_port(source)
        tgt_is_io = self._is_root_port(target)

        if src_is_io or tgt_is_io:
            # IO wrapper ports can own interfaceOnly attrs that strict plugin checks reject.
            src_proxy = getattr(source, "proxy_attribute", None)
            tgt_proxy = getattr(target, "proxy_attribute", None)
            src_ifo = getattr(src_proxy, "connectability", None)
            tgt_ifo = getattr(tgt_proxy, "connectability", None)
            ifo_token = UsdShade.Tokens.interfaceOnly
            if (src_ifo == ifo_token and src_is_io) or (tgt_ifo == ifo_token and tgt_is_io):
                if self._would_create_prim_cycle(source, target):
                    return False
                return True

        result = self._model.can_connect(source, target)
        return result

    @staticmethod
    def _would_create_prim_cycle(source: object, target: object) -> bool:
        """Return whether connecting source->target would cycle at prim level."""
        return would_create_prim_cycle(getattr(source, "prim", None), getattr(target, "prim", None))

    @staticmethod
    def _is_internal_nodegraph_interface_connection(source: object, target: object) -> bool:
        """Return True for direct child <-> containing NodeGraph interface wiring."""
        return is_internal_nodegraph_interface_connection(source, target)

    def _is_nodegraph_output_sink_connection(self, source: object, target: object) -> bool:
        """Return True for child output -> current NodeGraph output sink connections."""
        if not self._is_output_port(source) or not self._is_root_port(target) or not self._is_output_port(target):
            return False
        root_model = getattr(self, "_root", None)
        root_prim = getattr(root_model, "prim", root_model)
        target_prim = getattr(target, "prim", None)
        source_prim = getattr(source, "prim", None)
        if not root_prim or not source_prim:
            return False
        try:
            if target_prim and target_prim.GetPath() != root_prim.GetPath():
                return False
            return bool(root_prim.IsA(UsdShade.NodeGraph) and source_prim.GetParent().GetPath() == root_prim.GetPath())
        except (RuntimeError, ValueError, TypeError, AttributeError):
            return False

    @classmethod
    def _is_polymorphic_nodegraph_output_sink_connection(cls, source: object, target: object) -> bool:
        """Return True when strict delegate validation rejected a polymorphic interface wire."""
        source_candidates = cls._candidate_type_names(source)
        target_candidates = cls._candidate_type_names(target)
        source_type = cls._port_type_name(source)
        target_type = cls._port_type_name(target)

        if source_candidates and target_type:
            return target_type in source_candidates
        if target_candidates and source_type:
            return source_type in target_candidates

        # When candidate lists are empty (model not yet re-synced after
        # disconnect), allow the connection tentatively if either endpoint
        # is polymorphic/unresolved -- the resolver will narrow at commit.
        if bool(getattr(getattr(source, "proxy_attribute", None), "polymorphic_unresolved", False)) or bool(
            getattr(getattr(target, "proxy_attribute", None), "polymorphic_unresolved", False)
        ):
            return True

        return False

    @staticmethod
    def _candidate_type_names(port: object) -> set:
        get_candidates = getattr(port, "_get_candidate_port_types", None)
        if not callable(get_candidates):
            return set()
        try:
            return {str(type_name) for type_name in get_candidates() if type_name}
        except (RuntimeError, ValueError, TypeError, AttributeError):
            return set()

    @staticmethod
    def _port_type_name(port: object) -> str:
        proxy = getattr(port, "proxy_attribute", None)
        type_name = str(getattr(proxy, "type_name", "") or "")
        if type_name:
            return type_name
        usdshade_port = getattr(port, "usdshade_port", None)
        try:
            attr = usdshade_port.GetAttr() if usdshade_port else None
            if attr:
                return str(attr.GetTypeName())
        except (RuntimeError, ValueError, TypeError, AttributeError):
            pass
        return ""

    def _is_root_port(self, port: object) -> bool:
        """Return True if the port is a root-prim port (InputNode/OutputNode territory)."""
        rp = self._root_ports
        if rp and port in rp:
            return True
        ri = self._root_inputs
        if ri and port in ri:
            return True
        ro = self._root_outputs
        if ro and port in ro:
            return True
        return False

    def remove_input(self) -> None:
        """Remove input nodes and refresh the graph caches and views."""
        if self._input_nodes:
            self._input_nodes.clear()
            self.clear_caches()
            self._item_changed(None)
            self._root._item_changed(None)

    def remove_output(self) -> None:
        """Remove output nodes and refresh the graph caches and views."""
        if self._output_nodes and not self._output_nodes[0].prim.IsA(UsdShade.Material):
            self._output_nodes.clear()
            self.clear_caches()
            self._item_changed(None)
            self._root._item_changed(None)

    def refresh(self) -> None:
        """Refresh isolation caches and notify both isolation and root models."""
        self.clear_caches()
        self._item_changed(None)
        if self._root:
            # Root listens to isolation changes; ensure both models notify.
            self._root._item_changed(None)
