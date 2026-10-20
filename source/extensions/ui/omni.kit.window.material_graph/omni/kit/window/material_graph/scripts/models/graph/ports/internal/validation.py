"""Validation helpers for detecting invalid or cyclical USD port connections."""

from typing import Dict, List, Set

from pxr import Sdf, Usd, UsdShade

from .....config.logging import logger

# pylint: disable=broad-exception-caught


def _iter_connected_sources(input_attr: UsdShade.Input):
    """Yield normalized connected source records for an input attribute."""
    sources = input_attr.GetConnectedSources()
    sources = sources[0] if isinstance(sources, tuple) else sources
    if not sources:
        source_info = input_attr.GetConnectedSource()
        source_info = source_info[0] if isinstance(source_info, tuple) else source_info
        sources = [source_info] if source_info else []
    for source in sources:
        if source:
            yield source


def _resolve_source_path(source: object, root_path: Sdf.Path) -> Sdf.Path | None:
    """Resolve source object to a source prim path under the same root."""
    source_api = getattr(source, "source", source)
    if not source_api:
        return None
    try:
        source_prim = source_api.GetPrim()
    except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
        logger.debug("source_api.GetPrim failed: %s", exc)
        return None
    if not source_prim or not source_prim.IsValid():
        return None
    # Material interfaces are pass-through endpoints, not computation nodes in the shader dependency graph.
    if not (source_prim.IsA(UsdShade.Shader) or source_prim.IsA(UsdShade.NodeGraph)):
        return None
    source_path = source_prim.GetPath()
    return source_path if source_path.HasPrefix(root_path) else None


def _collect_graph_edges(root_prim: Usd.Prim) -> tuple[Dict[Sdf.Path, set[Sdf.Path]], Set[Sdf.Path]]:
    """Collect dependency edges among connectable prims under root."""
    root_path = root_prim.GetPath()
    edges: Dict[Sdf.Path, set[Sdf.Path]] = {}
    nodes: Set[Sdf.Path] = set()
    for prim in Usd.PrimRange(root_prim):
        if not prim or not prim.IsValid():
            continue
        if not (prim.IsA(UsdShade.Shader) or prim.IsA(UsdShade.NodeGraph)):
            continue
        prim_path = prim.GetPath()
        nodes.add(prim_path)
        connectable = UsdShade.ConnectableAPI(prim)
        for input_attr in connectable.GetInputs():
            if not input_attr or not input_attr.HasConnectedSource():
                continue
            for source in _iter_connected_sources(input_attr):
                source_path = _resolve_source_path(source, root_path)
                if source_path:
                    edges.setdefault(source_path, set()).add(prim_path)
    return edges, nodes


def _collect_cycle_nodes(edges: Dict[Sdf.Path, set[Sdf.Path]], nodes: Set[Sdf.Path]) -> Set[Sdf.Path]:
    """Return exactly the node paths participating in dependency cycles.

    Tarjan strongly-connected components avoid two failure modes of the old
    propagated DFS boolean: ancestors leading into a cycle were marked as
    cyclical, and traversal stopped after the first cycle.
    """
    next_index = 0
    indices: Dict[Sdf.Path, int] = {}
    lowlinks: Dict[Sdf.Path, int] = {}
    stack: list[Sdf.Path] = []
    on_stack: Set[Sdf.Path] = set()
    cycle_nodes: Set[Sdf.Path] = set()

    def _visit(node_path: Sdf.Path) -> None:
        """Collect the strongly-connected component rooted at node_path."""
        nonlocal next_index
        indices[node_path] = next_index
        lowlinks[node_path] = next_index
        next_index += 1
        stack.append(node_path)
        on_stack.add(node_path)

        for neighbor in edges.get(node_path, set()):
            if neighbor not in indices:
                _visit(neighbor)
                lowlinks[node_path] = min(lowlinks[node_path], lowlinks[neighbor])
            elif neighbor in on_stack:
                lowlinks[node_path] = min(lowlinks[node_path], indices[neighbor])

        if lowlinks[node_path] != indices[node_path]:
            return

        component: list[Sdf.Path] = []
        while stack:
            member = stack.pop()
            on_stack.remove(member)
            component.append(member)
            if member == node_path:
                break
        if len(component) > 1 or node_path in edges.get(node_path, set()):
            cycle_nodes.update(component)

    for node_path in nodes:
        if node_path not in indices:
            _visit(node_path)
    return cycle_nodes


def _find_cycle_search_root(source_prim: Usd.Prim, target_prim: Usd.Prim) -> Usd.Prim | None:
    """Return the shared material/nodegraph scope for prospective cycle checks."""
    source_stage = source_prim.GetStage()
    if source_stage != target_prim.GetStage():
        return None

    target_path = target_prim.GetPath()
    for prefix in reversed(source_prim.GetPath().GetPrefixes()):
        if not target_path.HasPrefix(prefix):
            continue
        root_prim = source_stage.GetPrimAtPath(prefix)
        if (
            root_prim
            and root_prim.IsValid()
            and (root_prim.IsA(UsdShade.Material) or root_prim.IsA(UsdShade.NodeGraph))
        ):
            return root_prim
    # Avoid pseudo-root fallback: scanning the whole stage is too broad for
    # material graph cycle checks when no shared material/nodegraph scope exists.
    return None


def _has_dependency_path(edges: Dict[Sdf.Path, set[Sdf.Path]], start_path: Sdf.Path, goal_path: Sdf.Path) -> bool:
    """Return True when dependency edges can reach goal_path from start_path."""
    pending = [start_path]
    visited: Set[Sdf.Path] = set()
    while pending:
        node_path = pending.pop()
        if node_path == goal_path:
            return True
        if node_path in visited:
            continue
        visited.add(node_path)
        pending.extend(edges.get(node_path, set()) - visited)
    return False


def would_create_cycle(source_prim: Usd.Prim, target_prim: Usd.Prim) -> bool:
    """Return True if adding source_prim->target_prim closes an existing dependency path."""
    if not source_prim or not target_prim or not source_prim.IsValid() or not target_prim.IsValid():
        return False

    source_path = source_prim.GetPath()
    target_path = target_prim.GetPath()
    if source_path == target_path:
        return True
    if source_prim.IsA(UsdShade.Material) or target_prim.IsA(UsdShade.Material):
        return False
    if source_prim.GetStage() != target_prim.GetStage():
        return True

    root_prim = _find_cycle_search_root(source_prim, target_prim)
    if not root_prim or not root_prim.IsValid():
        return False

    edges, _nodes = _collect_graph_edges(root_prim)
    return _has_dependency_path(edges, target_path, source_path)


def find_cyclical_prims(root_prim: Usd.Prim) -> List[Usd.Prim]:
    """Return prims that participate in cyclical connections."""
    if not root_prim or not root_prim.IsValid():
        return []
    edges, nodes = _collect_graph_edges(root_prim)
    cycle_nodes = _collect_cycle_nodes(edges, nodes)

    if not cycle_nodes:
        return []
    stage = root_prim.GetStage()
    return [stage.GetPrimAtPath(path) for path in cycle_nodes if stage]
