"""InputNode view model.

Provides port classification by context state, internal port grouping,
view mode filtering, and context membership tracking.  Only affects
InputNode rendering; normal compute nodes are unchanged.
"""

from typing import Any, Dict, List, Optional, Tuple

from pxr import Sdf, UsdShade

from ...config.logging import get_logger

logger = get_logger()


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class IoState:
    """Port usage classification relative to the active graph context."""

    ACTIVE_IN_CURRENT = 0
    USED_IN_OTHER = 1
    UNUSED = 2


class InputNodeViewMode:
    """Local per-InputNode view mode."""

    CURRENT_CONTEXT = 0
    ALL_USED = 1
    ALL_PORTS = 2


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

_MAX_FLAT_PORTS = 16
_GROUP_COLLAPSE_THRESHOLD = 8


# ---------------------------------------------------------------------------
# Synthetic group-header marker
# ---------------------------------------------------------------------------


class _SyntheticGroupHeader:
    """Lightweight stand-in injected into port lists for group headers.

    ``_export_ports`` detects this via ``is_synthetic_group_header`` and
    emits a snapshot dict instead of querying the model.
    """

    is_synthetic_group_header = True

    def __init__(
        self,
        name: str,
        port_count: int,
        collapsed: bool,
        io_state_summary: int = -1,
    ) -> None:
        self.name = name
        self.port_count = port_count
        self.collapsed = collapsed
        self.io_state_summary = io_state_summary


# ---------------------------------------------------------------------------
# Internal port group
# ---------------------------------------------------------------------------


class _PortGroup:
    """Accumulator for ports that share a semantic or fallback group."""

    __slots__ = ("name", "ports", "collapsed")

    def __init__(self, name: str) -> None:
        self.name: str = name
        self.ports: List[Tuple[Any, int]] = []  # (port_obj, io_state)
        self.collapsed: bool = False

    @property
    def count(self) -> int:
        return len(self.ports)

    def has_active(self) -> bool:
        return any(s == IoState.ACTIVE_IN_CURRENT for _, s in self.ports)

    def has_used(self) -> bool:
        return any(s != IoState.UNUSED for _, s in self.ports)

    def sort_ports(self) -> None:
        """Sort by io_state bucket (active → other → unused), stable order."""
        buckets: Dict[int, List[Tuple[Any, int]]] = {0: [], 1: [], 2: []}
        for p, s in self.ports:
            buckets.setdefault(s, []).append((p, s))
        self.ports = buckets[0] + buckets[1] + buckets[2]


# ---------------------------------------------------------------------------
# InputNodeViewModel
# ---------------------------------------------------------------------------


class InputNodeViewModel:
    """Classifies, groups, and filters InputNode ports.

    Instantiated once per ``GraphCanvasView`` and rebuilt whenever the
    context tab changes, the graph rebuilds, or topology changes.
    """

    def __init__(self) -> None:
        self._mode: int = InputNodeViewMode.CURRENT_CONTEXT
        self._io_states: Dict[int, int] = {}
        self._port_contexts: Dict[int, List[str]] = {}
        self._display_groups: Dict[int, str] = {}
        self._groups: List[_PortGroup] = []
        self._all_ports: List[Any] = []
        self._empty_port: Any = None
        self._built: bool = False
        self._current_context: str = ""
        self._group_collapse_overrides: Dict[str, bool] = {}
        self._other_group_expanded: bool = False
        self._unused_group_expanded: bool = False
        self._group_collapse_state: Dict[str, bool] = {}
        # Cross-context cache: ctx_name -> set of port attribute names connected
        self._ctx_connected_attrs: Dict[str, set] = {}

    # -- properties ---------------------------------------------------------

    @property
    def mode(self) -> int:
        return self._mode

    @mode.setter
    def mode(self, value: int) -> None:
        self._mode = value

    def cycle_mode(self) -> int:
        self._mode = (self._mode + 1) % 3
        return self._mode

    @property
    def empty_port(self) -> Any:
        return self._empty_port

    @property
    def has_active_ports(self) -> bool:
        return any(v == IoState.ACTIVE_IN_CURRENT for v in self._io_states.values())

    @property
    def total_port_count(self) -> int:
        return len(self._all_ports)

    # -- public API ---------------------------------------------------------

    def rebuild(
        self,
        input_node: Any,
        isolation_model: Any,
        current_context_name: str,
        context_manager: Any,
    ) -> None:
        """Reclassify every port and rebuild group structure (standalone)."""
        source = input_node.source
        try:
            from omni.kit.widget.graph import IsolationGraphModel

            _EmptyPort = IsolationGraphModel.EmptyPort
        except Exception:
            _EmptyPort = None
        # Use the InputNode's own port list — it knows which ports are valid
        raw_ports = input_node.ports or []
        self.rebuild_from_ports(input_node, raw_ports, isolation_model, current_context_name, context_manager)

    def rebuild_from_ports(
        self,
        input_node: Any,
        node_ports: list,
        isolation_model: Any,
        current_context_name: str,
        context_manager: Any,
    ) -> None:
        """Classify and group using an already-computed port list.

        Called from inside ``export_snapshot`` where the isolation model's
        connection state is fully populated and *node_ports* is the
        authoritative list from ``snapshot_node()``.
        """
        self._io_states.clear()
        self._port_contexts.clear()
        self._display_groups.clear()
        self._groups.clear()
        self._all_ports.clear()
        self._empty_port = None
        self._built = False
        self._current_context = current_context_name

        try:
            from omni.kit.widget.graph import IsolationGraphModel

            _EmptyPort = IsolationGraphModel.EmptyPort
        except Exception:
            _EmptyPort = None

        real_ports: List[Any] = []
        for port in node_ports or []:
            if _EmptyPort is not None and isinstance(port, _EmptyPort):
                self._empty_port = port
            else:
                real_ports.append(port)

        if self._empty_port is None and input_node.empty_port is not None:
            self._empty_port = input_node.empty_port

        self._all_ports = real_ports

        root_prim = getattr(input_node.source, "prim", None)

        self._classify_all(real_ports, isolation_model, root_prim, current_context_name, context_manager)

        self._extract_display_groups(real_ports, isolation_model)
        self._build_groups(real_ports)

        self._built = True

    def get_io_state(self, port: Any) -> int:
        return self._io_states.get(id(port), IoState.UNUSED)

    def get_port_contexts(self, port: Any) -> List[str]:
        return self._port_contexts.get(id(port), [])

    def toggle_group_collapsed(self, group_name: str) -> None:
        """Toggle persistent collapse override for a named group."""
        cur = self._group_collapse_overrides.get(group_name)
        if cur is None:
            for g in self._groups:
                if g.name == group_name:
                    self._group_collapse_overrides[group_name] = not g.collapsed
                    return
        else:
            self._group_collapse_overrides[group_name] = not cur

    def get_ordered_port_entries(self) -> list:
        """Return the flat entry list for the active mode.

        Entries are either ``_SyntheticGroupHeader`` instances or
        ``(port, io_state)`` tuples.  The EmptyPort is always appended
        at the very end.
        """
        if not self._built:
            return []

        mode = self._mode

        total_visible = sum(len(self._visible_in_group(g, mode)) for g in self._groups)
        need_grouping = total_visible > _MAX_FLAT_PORTS or len(self._groups) > 1

        if mode == InputNodeViewMode.CURRENT_CONTEXT:
            entries = self._entries_current_context(need_grouping)
        elif mode == InputNodeViewMode.ALL_USED:
            entries = self._entries_all_used(need_grouping)
        else:
            entries = self._entries_all_ports(need_grouping)

        # CRITICAL: EmptyPort (Add Input) is always last and never hidden
        if self._empty_port is not None:
            entries.append((self._empty_port, -1))

        return entries

    # -- classification -----------------------------------------------------

    def _classify_all(
        self,
        ports: List[Any],
        iso_model: Any,
        root_prim: Any,
        ctx_name: str,
        ctx_mgr: Any,
    ) -> None:
        for port in ports:
            pid = id(port)
            pname = "?"
            try:
                pname = str(iso_model[port].name)
            except Exception:
                pass

            active = self._is_active_in_current(port, iso_model, pname)
            if active:
                self._io_states[pid] = IoState.ACTIVE_IN_CURRENT
                self._port_contexts[pid] = [ctx_name]
                continue

            has_usd = self._has_usd_connections(port, root_prim, iso_model, pname)
            if has_usd:
                self._io_states[pid] = IoState.USED_IN_OTHER
                self._port_contexts[pid] = self._discover_contexts(port, ctx_mgr, ctx_name, iso_model)
            else:
                self._io_states[pid] = IoState.UNUSED
                self._port_contexts[pid] = []

    @staticmethod
    def _is_active_in_current(port: Any, iso_model: Any, pname: str = "?") -> bool:
        # Check isolation proxy connections
        try:
            pp = iso_model[port]
            ins = pp.inputs
            outs = pp.outputs
            if (ins is not None and len(ins) > 0) or (outs is not None and len(outs) > 0):
                return True
        except Exception:
            pass

        # Check root connection maps — InputNode ports route through these
        try:
            ri = getattr(iso_model, "_root_inputs", None) or {}
            ro = getattr(iso_model, "_root_outputs", None) or {}
            in_ri = ri.get(port)
            in_ro = ro.get(port)
            if in_ri or in_ro:
                return True
        except Exception:
            pass

        return False

    @staticmethod
    def _has_usd_connections(port: Any, root_prim: Any, iso_model: Any, pname: str = "?") -> bool:
        if root_prim is None:
            return False
        try:
            pp = iso_model[port]
            proxy = getattr(pp, "proxy_attribute", None)
            if proxy is None:
                return False
            attr_name = proxy.name
            attr = root_prim.GetAttribute(attr_name)
            if not attr or not attr.IsValid():
                return False
            usd_input = UsdShade.Input(attr)
            if usd_input:
                sources = usd_input.GetConnectedSources()
                if sources and sources[0]:
                    return True
        except Exception:
            pass
        return False

    @staticmethod
    def _discover_contexts(
        port: Any,
        ctx_mgr: Any,
        current_ctx: str,
        iso_model: Any,
    ) -> List[str]:
        contexts: List[str] = []
        try:
            for name in ctx_mgr.get_context_names():
                if name == current_ctx:
                    continue
                handle = ctx_mgr.get_context(name)
                if handle.is_valid:
                    contexts.append(name)
        except Exception as exc:
            logger.debug("_discover_contexts: %s", exc)
        return contexts if contexts else ["other"]

    # -- display group extraction -------------------------------------------

    def _extract_display_groups(self, ports: List[Any], iso_model: Any) -> None:
        for port in ports:
            pid = id(port)
            try:
                pp = iso_model[port]
                dg = str(getattr(pp, "display_group", "") or "")
                if dg.startswith("Inputs:"):
                    dg = dg[7:]
                elif dg == "Inputs" or not dg:
                    dg = ""
                if ":" in dg:
                    dg = dg.split(":")[0]
                self._display_groups[pid] = dg.strip() if dg.strip() else ""
            except Exception:
                self._display_groups[pid] = ""

    # -- group construction -------------------------------------------------

    def _build_groups(self, ports: List[Any]) -> None:
        group_map: Dict[str, _PortGroup] = {}
        has_semantic = False

        for port in ports:
            pid = id(port)
            io_state = self._io_states.get(pid, IoState.UNUSED)
            dg = self._display_groups.get(pid, "")
            if dg:
                has_semantic = True
            gname = dg if dg else "General"

            if gname not in group_map:
                group_map[gname] = _PortGroup(gname)
            group_map[gname].ports.append((port, io_state))

        total = len(ports)

        # Fallback grouping when no semantic metadata and large port count
        if not has_semantic and total > _MAX_FLAT_PORTS:
            group_map = self._fallback_groups(ports)

        for g in group_map.values():
            g.sort_ports()

        # Order: active-containing groups first, then rest, alphabetical
        active_gs = sorted(
            (g for g in group_map.values() if g.has_active()),
            key=lambda g: g.name,
        )
        other_gs = sorted(
            (g for g in group_map.values() if not g.has_active()),
            key=lambda g: g.name,
        )
        all_gs = active_gs + other_gs

        # Collapse policy
        any_expanded = False
        for g in all_gs:
            override = self._group_collapse_overrides.get(g.name)
            if override is not None:
                g.collapsed = override
                if not override:
                    any_expanded = True
            elif g.count > _GROUP_COLLAPSE_THRESHOLD:
                g.collapsed = True
            else:
                g.collapsed = False
                any_expanded = True

        if not any_expanded and all_gs:
            for g in all_gs:
                if g.has_active():
                    g.collapsed = False
                    any_expanded = True
                    break
            if not any_expanded:
                all_gs[0].collapsed = False

        # Force-split when >16 ports sit in a single group
        if total > _MAX_FLAT_PORTS and len(all_gs) <= 1:
            src = all_gs[0] if all_gs else _PortGroup("General")
            all_gs = self._force_split(src)

        self._groups = all_gs

    def _fallback_groups(self, ports: List[Any]) -> Dict[str, _PortGroup]:
        """Fallback when no semantic display_group exists and port count is
        large.  Groups by first letter or keeps a single 'General' group.
        NEVER creates a 'Current Context' wrapper group."""
        general = _PortGroup("General")
        for port in ports:
            pid = id(port)
            s = self._io_states.get(pid, IoState.UNUSED)
            general.ports.append((port, s))
        return {"General": general}

    @staticmethod
    def _force_split(group: _PortGroup) -> List[_PortGroup]:
        """Split a single large group into chunks by index (A-M / N-Z style)
        to avoid a flat wall.  Never uses context-based naming."""
        ports = group.ports
        chunk_size = max(8, len(ports) // 3)
        result: List[_PortGroup] = []
        for start in range(0, len(ports), chunk_size):
            chunk = ports[start : start + chunk_size]
            first_name = ""
            last_name = ""
            for p, _ in chunk:
                n = getattr(p, "name", "") or str(p)
                if not first_name:
                    first_name = n
                last_name = n
            label = f"{first_name[:12]}...{last_name[:12]}" if first_name != last_name else first_name
            g = _PortGroup(label)
            g.ports = list(chunk)
            g.collapsed = g.count > _GROUP_COLLAPSE_THRESHOLD
            result.append(g)
        if result and all(g.collapsed for g in result):
            result[0].collapsed = False
        return result if result else [group]

    # -- mode-specific entry builders ---------------------------------------

    def _visible_in_group(self, group: _PortGroup, mode: int) -> List[Tuple[Any, int]]:
        if mode == InputNodeViewMode.CURRENT_CONTEXT:
            return [(p, s) for p, s in group.ports if s == IoState.ACTIVE_IN_CURRENT]
        if mode == InputNodeViewMode.ALL_USED:
            return [(p, s) for p, s in group.ports if s != IoState.UNUSED]
        return list(group.ports)

    def _entries_current_context(self, use_grouping: bool) -> list:
        """Strict CURRENT_CONTEXT: only active ports + collapsed summary."""
        entries: list = []
        non_active_total = 0

        for g in self._groups:
            active = [(p, s) for p, s in g.ports if s == IoState.ACTIVE_IN_CURRENT]
            non_active_total += g.count - len(active)

            if not active:
                continue

            if use_grouping:
                override = self._group_collapse_overrides.get(g.name)
                collapsed = override if override is not None else len(active) > _GROUP_COLLAPSE_THRESHOLD
                entries.append(_SyntheticGroupHeader(g.name, len(active), collapsed))
                if not collapsed:
                    entries.extend(active)
            else:
                entries.extend(active)

        # Ensure at least one group is expanded when grouping is used
        if use_grouping and entries:
            all_collapsed = all(
                isinstance(e, _SyntheticGroupHeader) and e.collapsed
                for e in entries
                if isinstance(e, _SyntheticGroupHeader)
            )
            if all_collapsed:
                for i, e in enumerate(entries):
                    if isinstance(e, _SyntheticGroupHeader):
                        e.collapsed = False
                        # Insert the group's ports after the header
                        for g in self._groups:
                            if g.name == e.name:
                                active = [(p, s) for p, s in g.ports if s == IoState.ACTIVE_IN_CURRENT]
                                for j, ap in enumerate(active):
                                    entries.insert(i + 1 + j, ap)
                                break
                        break

        # Collapsed summary for non-active ports
        if non_active_total > 0:
            entries.append(
                _SyntheticGroupHeader(
                    f"Other context ports ({non_active_total})",
                    non_active_total,
                    True,
                    IoState.USED_IN_OTHER,
                )
            )

        # Empty-state: no active ports at all
        if not any(not isinstance(e, _SyntheticGroupHeader) for e in entries):
            if not entries or all(isinstance(e, _SyntheticGroupHeader) for e in entries):
                pass  # EmptyPort appended by caller; C++ handles empty message

        return entries

    def _entries_all_used(self, use_grouping: bool) -> list:
        entries: list = []
        for g in self._groups:
            used = [(p, s) for p, s in g.ports if s != IoState.UNUSED]
            if not used:
                continue
            if use_grouping:
                override = self._group_collapse_overrides.get(g.name)
                collapsed = override if override is not None else (g.collapsed or len(used) > _GROUP_COLLAPSE_THRESHOLD)
                entries.append(_SyntheticGroupHeader(g.name, len(used), collapsed))
                if not collapsed:
                    entries.extend(used)
            else:
                entries.extend(used)
        return entries

    def _entries_all_ports(self, use_grouping: bool) -> list:
        entries: list = []
        for g in self._groups:
            if g.count == 0:
                continue
            if use_grouping:
                override = self._group_collapse_overrides.get(g.name)
                collapsed = override if override is not None else (g.collapsed or g.count > _GROUP_COLLAPSE_THRESHOLD)
                entries.append(_SyntheticGroupHeader(g.name, g.count, collapsed))
                if not collapsed:
                    entries.extend(g.ports)
            else:
                entries.extend(g.ports)
        return entries
