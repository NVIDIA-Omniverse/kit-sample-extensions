"""Per-context material validation pipeline."""

from typing import Callable, Iterable, List, Optional, Set

from pxr import Sdf, Usd, UsdShade

from ..config.logging import log_exception, logger
from ..models.graph.ports.internal.validation import find_cyclical_prims
from ..models.graph.ports.proxy import ProxyAttribute
from .issue import ValidationIssue
from .result import ValidationResult
from .severity import ValidationSeverity


def _internal_validation_issue(
    context_name: str,
    action: str,
    exc: Exception,
    prim_path: Optional[str] = None,
) -> ValidationIssue:
    """Return a visible issue when validation itself cannot complete safely."""
    location = f" for '{prim_path}'" if prim_path else ""
    return ValidationIssue(
        code="VALIDATION_INTERNAL_ERROR",
        message=(
            f"Validation could not complete '{action}' in context '{context_name}'{location}: "
            f"{type(exc).__name__}: {exc}"
        ),
        severity=ValidationSeverity.ERROR,
        prim_path=prim_path,
        context_name=context_name,
    )


def _extend_issues_safely(
    issues: List[ValidationIssue],
    context_name: str,
    action: str,
    callback: Callable[[], Iterable[ValidationIssue]],
    prim_path: Optional[str],
) -> None:
    """Collect issues without allowing one validator to terminate the pipeline."""
    try:
        issues.extend(callback() or [])
    except Exception as exc:  # pylint: disable=broad-exception-caught
        log_exception(
            logger,
            "validation collector failed",
            context_name=context_name,
            prim_path=prim_path,
            action=action,
            exc=exc,
        )
        issues.append(_internal_validation_issue(context_name, action, exc, prim_path))


def _iter_connected_sources(input_attr: UsdShade.Input) -> Iterable[object]:
    """Yield connected source records for one input attribute."""
    sources = input_attr.GetConnectedSources()
    if isinstance(sources, tuple):
        sources = sources[0]
    if not sources:
        source_info = input_attr.GetConnectedSource()
        if isinstance(source_info, tuple):
            source_info = source_info[0]
        sources = [source_info] if source_info else []
    for source in sources:
        if source:
            yield source


def _resolve_source_prim(source: object) -> Optional[Usd.Prim]:
    """Resolve the source prim from a connection record."""
    # Dynamic USD boundary: source record shape differs by binding/version.
    source_api = source.source if hasattr(source, "source") else source
    if not source_api:
        return None
    try:
        prim = source_api.GetPrim()
    except (RuntimeError, ValueError, TypeError, AttributeError):
        return None
    if not prim or not prim.IsValid():
        return None
    return prim


def _source_attribute_from_connection(source: object, source_prim: Usd.Prim) -> Optional[Usd.Attribute]:
    """Resolve source attribute from source connection metadata."""
    # Dynamic USD boundary: connection records may not carry sourceName/sourceType.
    source_name = source.sourceName if hasattr(source, "sourceName") else None
    if not source_name:
        return None
    source_type = source.sourceType if hasattr(source, "sourceType") else UsdShade.AttributeType.Output
    if source_type == UsdShade.AttributeType.Input:
        attr_name = f"{UsdShade.Tokens.inputs}{source_name}"
    else:
        attr_name = f"{UsdShade.Tokens.outputs}{source_name}"
    return source_prim.GetAttribute(attr_name)


def _source_path_from_connection(source: object, source_prim: Usd.Prim) -> str:
    """Return the most specific source property path available from a connection record."""
    source_attr = _source_attribute_from_connection(source, source_prim)
    if source_attr:
        return str(source_attr.GetPath())
    return str(source_prim.GetPath())


def _connection_message(
    context_name: str,
    source_path: str,
    target_path: str,
    reason: str,
) -> str:
    """Build an actionable connection diagnostic with both endpoints."""
    return (
        f"Invalid connection in context '{context_name}':\n"
        f"  source: {source_path}\n"
        f"  target: {target_path}\n"
        f"  reason: {reason}"
    )


def _collect_output_reachable_connectables(
    root_prim: Usd.Prim, output_names: Optional[Set[str]] = None
) -> Set[Sdf.Path]:
    """Collect connectable prims reachable from selected material outputs."""
    reachable: Set[Sdf.Path] = set()
    visited_ports: Set[Sdf.Path] = set()
    visited_prims: Set[Sdf.Path] = set()

    def _walk_output(output_port: UsdShade.Output) -> None:
        if not output_port:
            return
        try:
            output_path = output_port.GetAttr().GetPath()
        except (AttributeError, RuntimeError):
            return
        if output_path in visited_ports:
            return
        visited_ports.add(output_path)
        sources = output_port.GetConnectedSources()
        if isinstance(sources, tuple):
            sources = sources[0]
        for source in sources:
            # Dynamic USD boundary: source info may be absent for broken links.
            source_api = source.source if hasattr(source, "source") else None
            if not source_api:
                continue
            source_prim = source_api.GetPrim()
            if not source_prim or not source_prim.IsValid():
                continue
            _walk_prim(source_prim)
            source_name = source.sourceName if hasattr(source, "sourceName") else None
            if source_prim.IsA(UsdShade.NodeGraph) and source_name:
                nested = UsdShade.NodeGraph(source_prim).GetOutput(source_name)
                if nested:
                    _walk_output(nested)

    def _walk_prim(prim: Usd.Prim) -> None:
        prim_path = prim.GetPath()
        if prim_path in visited_prims:
            return
        visited_prims.add(prim_path)
        if not (prim.IsA(UsdShade.Shader) or prim.IsA(UsdShade.NodeGraph)):
            return
        reachable.add(prim_path)
        connectable = UsdShade.ConnectableAPI(prim)
        for input_attr in connectable.GetInputs():
            if not input_attr or not input_attr.HasConnectedSource():
                continue
            for source in _iter_connected_sources(input_attr):
                source_prim = _resolve_source_prim(source)
                if source_prim:
                    _walk_prim(source_prim)

    material = UsdShade.Material(root_prim)
    for output in material.GetOutputs():
        if output_names is not None and output.GetFullName() not in output_names:
            continue
        _walk_output(output)
    return reachable


def _collect_context_prims(root_prim: Usd.Prim, model: Optional[object]) -> List[Usd.Prim]:
    """Collect context-relevant prims from MaterialModel; fallback to output traversal."""
    if model:
        prims = [root_prim]
        seen = {root_prim.GetPath()}

        def _append_graph_children(graph_model: object) -> None:
            try:
                child_prims = graph_model.get_child_prims()
            except (RuntimeError, ValueError, TypeError, AttributeError):
                return
            for prim in child_prims:
                if not prim or not prim.IsValid():
                    continue
                prim_path = prim.GetPath()
                if prim_path in seen:
                    continue
                seen.add(prim_path)
                prims.append(prim)
                if not prim.IsA(UsdShade.NodeGraph):
                    continue
                try:
                    child_model = graph_model.get_item_model(prim_path)
                except (RuntimeError, ValueError, TypeError, AttributeError):
                    child_model = None
                if child_model:
                    _append_graph_children(child_model)

        _append_graph_children(model)
        return prims

    reachable_paths = _collect_output_reachable_connectables(root_prim)
    stage = root_prim.GetStage()
    prims = [root_prim]
    if not stage:
        return prims
    for prim_path in reachable_paths:
        prim = stage.GetPrimAtPath(prim_path)
        if prim and prim.IsValid():
            prims.append(prim)
    return prims


def _collect_invalid_nodes(
    prims: List[Usd.Prim], plugin: object, context_name: str, reachable: Set[Sdf.Path]
) -> List[ValidationIssue]:
    """Return shader nodes that cannot be resolved to a valid node definition."""
    issues: List[ValidationIssue] = []
    for prim in prims:
        if not prim or not prim.IsValid() or not prim.IsA(UsdShade.Shader):
            continue
        try:
            supported = plugin.is_supported_prim(prim)
        except (RuntimeError, ValueError, TypeError, AttributeError):
            supported = False
        if not supported:
            continue
        try:
            shader_node = plugin.get_shader_node_for_prim(prim)
        except (RuntimeError, ValueError, TypeError, AttributeError):
            shader_node = None
        if shader_node:
            continue
        prim_path_str = str(prim.GetPath())
        is_reachable = prim.GetPath() in reachable
        severity = ValidationSeverity.ERROR if is_reachable else ValidationSeverity.WARNING
        reference = _describe_shader_reference(prim, context_name)
        reference_line = f"\nReference: {reference}" if reference else ""
        issues.append(
            ValidationIssue(
                code="INVALID_NODE_DEFINITION_MISSING",
                message=f"Undefined node: {prim_path_str}\nNode definition cannot be found.{reference_line}",
                severity=severity,
                prim_path=prim_path_str,
                context_name=context_name,
            )
        )
    return issues


def _describe_shader_reference(prim: Usd.Prim, context_name: str) -> str:
    """Return the authored identifier or source-asset reference for an invalid shader."""

    try:
        shader = UsdShade.Shader(prim)
        if not shader:
            return ""
        shader_id = shader.GetShaderId()
        if shader_id:
            return f"identifier={shader_id}"
        api = UsdShade.NodeDefAPI(prim)
        if not api or shader.GetImplementationSource() != UsdShade.Tokens.sourceAsset:
            return ""
        source_asset = api.GetSourceAsset(context_name)
        subidentifier = api.GetSourceAssetSubIdentifier(context_name)
        parts = []
        if source_asset:
            parts.append(f"asset={source_asset}")
        if subidentifier:
            parts.append(f"subIdentifier={subidentifier}")
        return ", ".join(parts)
    except (RuntimeError, ValueError, TypeError, AttributeError):
        return ""


def _collect_invalid_nodegraphs(
    prims: List[Usd.Prim], context_name: str, model: Optional[object], reachable: Set[Sdf.Path]
) -> List[ValidationIssue]:
    """Return NodeGraph prims whose model reports invalid (contains invalid children)."""
    if not model:
        return []
    issues: List[ValidationIssue] = []
    for prim in prims:
        if not prim or not prim.IsValid() or not prim.IsA(UsdShade.NodeGraph):
            continue
        if prim.IsA(UsdShade.Material):
            continue
        try:
            item_model = model.get_item_model(prim.GetPath())
            has_invalid_children = getattr(item_model, "has_invalid_connected_children", None)
            if item_model and callable(has_invalid_children) and has_invalid_children():
                prim_path_str = str(prim.GetPath())
                is_reachable = prim.GetPath() in reachable
                severity = ValidationSeverity.ERROR if is_reachable else ValidationSeverity.WARNING
                issues.append(
                    ValidationIssue(
                        code="INVALID_NODEGRAPH_CHILDREN",
                        message=f"Invalid node(s) in: {prim_path_str}\nNodeGraph contains nodes that cannot be resolved.",
                        severity=severity,
                        prim_path=prim_path_str,
                        context_name=context_name,
                    )
                )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            prim_path_str = str(prim.GetPath())
            log_exception(
                logger,
                "nodegraph validation failed",
                context_name=context_name,
                prim_path=prim_path_str,
                action="invalid_nodegraph_children",
                exc=exc,
            )
            issues.append(
                _internal_validation_issue(
                    context_name,
                    "invalid nodegraph children",
                    exc,
                    prim_path_str,
                )
            )
    return issues


def _collect_invalid_shader_ports(
    prims: List[Usd.Prim],
    plugin: object,
    context_name: str,
    reachable: Optional[Set[Sdf.Path]] = None,
) -> List[ValidationIssue]:
    """Return shader ports that are not declared by SDR or schema definitions."""
    issues: List[ValidationIssue] = []
    for prim in prims:
        if not prim or not prim.IsValid() or not prim.IsA(UsdShade.Shader):
            continue
        sdr_node = plugin.get_shader_node_for_prim(prim)
        if not sdr_node:
            continue
        declared: Set[str] = set(prim.GetPrimDefinition().GetPropertyNames() or [])
        declared.update(f"{UsdShade.Tokens.inputs}{name}" for name in sdr_node.GetShaderInputNames())
        declared.update(f"{UsdShade.Tokens.outputs}{name}" for name in sdr_node.GetShaderOutputNames())
        for prop in prim.GetProperties():
            prop_name = prop.GetName()
            if not (prop_name.startswith(UsdShade.Tokens.inputs) or prop_name.startswith(UsdShade.Tokens.outputs)):
                continue
            if prop_name in declared:
                continue
            issues.append(
                ValidationIssue(
                    code="INVALID_SHADER_PORT_DEFINITION",
                    message=(
                        f"Invalid shader port in context '{context_name}': {prop.GetPath()}\n"
                        "Port is not defined by the node definition or an applied schema."
                    ),
                    severity=(
                        ValidationSeverity.ERROR
                        if reachable is None or prim.GetPath() in reachable
                        else ValidationSeverity.WARNING
                    ),
                    prim_path=str(prop.GetPath()),
                    context_name=context_name,
                )
            )
    return issues


def _collect_invalid_connections(
    root_prim: Usd.Prim,
    prims: List[Usd.Prim],
    plugin: object,
    context_name: str,
    can_connect_fn: Callable[[str, object, ProxyAttribute, ProxyAttribute], bool],
    reachable: Set[Sdf.Path],
) -> List[ValidationIssue]:
    """Return invalid connections that can affect a material output."""
    issues: List[ValidationIssue] = []
    root_path = root_prim.GetPath()
    valid_paths = {prim.GetPath() for prim in prims if prim and prim.IsValid()}
    valid_paths.add(root_path)

    for prim in prims:
        if not prim or not prim.IsValid():
            continue
        if not (prim.IsA(UsdShade.Material) or prim.IsA(UsdShade.NodeGraph) or prim.IsA(UsdShade.Shader)):
            continue
        # Disconnected graph fragments are valid authoring state.  A malformed
        # connection within one cannot affect the material until the fragment
        # is wired into an output, so it must not raise a material-level error.
        if prim.GetPath() != root_path and prim.GetPath() not in reachable:
            continue

        connectable = UsdShade.ConnectableAPI(prim)
        for input_attr in connectable.GetInputs():
            if not input_attr or not input_attr.HasConnectedSource():
                continue
            target_attr = input_attr.GetAttr()
            if not target_attr:
                continue
            target_path = str(target_attr.GetPath())
            for source in _iter_connected_sources(input_attr):
                source_prim = _resolve_source_prim(source)
                if not source_prim:
                    issues.append(
                        ValidationIssue(
                            code="INVALID_CONNECTION_BROKEN_SOURCE",
                            message=_connection_message(
                                context_name,
                                "<missing or invalid>",
                                target_path,
                                "the authored source prim could not be resolved",
                            ),
                            severity=ValidationSeverity.ERROR,
                            prim_path=target_path,
                            context_name=context_name,
                            target_path=target_path,
                            root_path=str(root_path),
                        )
                    )
                    continue
                source_path = source_prim.GetPath()
                source_property_path = _source_path_from_connection(source, source_prim)
                if not source_path.HasPrefix(root_path):
                    issues.append(
                        ValidationIssue(
                            code="INVALID_CONNECTION_OUTSIDE_MATERIAL_ROOT",
                            message=_connection_message(
                                context_name,
                                source_property_path,
                                target_path,
                                f"the source is outside material root '{root_path}'",
                            ),
                            severity=ValidationSeverity.ERROR,
                            prim_path=target_path,
                            context_name=context_name,
                            source_path=source_property_path,
                            target_path=target_path,
                            root_path=str(root_path),
                        )
                    )
                    continue
                if source_path not in valid_paths:
                    issues.append(
                        ValidationIssue(
                            code="INVALID_CONNECTION_OUTSIDE_CONTEXT",
                            message=_connection_message(
                                context_name,
                                source_property_path,
                                target_path,
                                "the source belongs to this material but is not part of the active context graph",
                            ),
                            severity=ValidationSeverity.ERROR,
                            prim_path=target_path,
                            context_name=context_name,
                            source_path=source_property_path,
                            target_path=target_path,
                            root_path=str(root_path),
                        )
                    )
                    continue

                source_attr = _source_attribute_from_connection(source, source_prim)
                if not source_attr:
                    issues.append(
                        ValidationIssue(
                            code="INVALID_CONNECTION_SOURCE_ATTRIBUTE_MISSING",
                            message=_connection_message(
                                context_name,
                                source_property_path,
                                target_path,
                                "the source attribute could not be resolved",
                            ),
                            severity=ValidationSeverity.ERROR,
                            prim_path=target_path,
                            context_name=context_name,
                            source_path=source_property_path,
                            target_path=target_path,
                            root_path=str(root_path),
                        )
                    )
                    continue
                source_proxy = ProxyAttribute(source_attr.GetName(), True, attribute=source_attr)
                target_proxy = ProxyAttribute(target_attr.GetName(), False, attribute=target_attr)
                src_type = str(source_attr.GetTypeName()) if source_attr else "?"
                tgt_type = str(target_attr.GetTypeName()) if target_attr else "?"
                can_conn = can_connect_fn(context_name, plugin, source_proxy, target_proxy)
                if can_conn:
                    continue
                src_path = str(source_attr.GetPath())
                tgt_path = str(target_attr.GetPath())
                detail = _connection_message(
                    context_name,
                    src_path,
                    tgt_path,
                    f"the source type '{src_type}' is incompatible with the target type '{tgt_type}'",
                )
                issues.append(
                    ValidationIssue(
                        code="INVALID_CONNECTION_TYPE_MISMATCH",
                        message=detail,
                        severity=ValidationSeverity.ERROR,
                        prim_path=tgt_path,
                        context_name=context_name,
                        source_path=src_path,
                        target_path=tgt_path,
                        root_path=str(root_path),
                    )
                )
                issues.append(
                    ValidationIssue(
                        code="INVALID_CONNECTION_TYPE_MISMATCH_SOURCE",
                        message=detail,
                        severity=ValidationSeverity.ERROR,
                        prim_path=src_path,
                        context_name=context_name,
                        source_path=src_path,
                        target_path=tgt_path,
                        root_path=str(root_path),
                    )
                )
    return issues


def _collect_cycle_issues(
    root_prim: Usd.Prim,
    context_name: str,
    reachable_paths: Optional[Set[Sdf.Path]] = None,
) -> List[ValidationIssue]:
    """Return cyclical nodegraph issues under output-reachable material subgraph."""
    cyclical_prims = find_cyclical_prims(root_prim)
    if not cyclical_prims:
        return []
    if reachable_paths is None:
        reachable_paths = _collect_output_reachable_connectables(root_prim)
    paths = [
        str(prim.GetPath()) for prim in cyclical_prims if prim and prim.IsValid() and prim.GetPath() in reachable_paths
    ]
    if not paths:
        return []
    listed = ", ".join(paths[:6])
    if len(paths) > 6:
        listed += f", +{len(paths) - 6} more"
    return [
        ValidationIssue(
            code="CYCLICAL_NODEGRAPHS",
            message=f"Material has cyclical nodegraph connections in context '{context_name}': {listed}",
            severity=ValidationSeverity.ERROR,
            prim_path=str(root_prim.GetPath()),
            context_name=context_name,
        )
    ]


def _collect_mixed_networks(
    prims: List[Usd.Prim],
    context_name: str,
    plugin: object,
    reachable: Optional[Set[Sdf.Path]] = None,
) -> List[ValidationIssue]:
    """Return issues when a context graph includes unsupported shader nodes."""
    issues: List[ValidationIssue] = []
    for shader_prim in prims:
        if not shader_prim or not shader_prim.IsValid() or not shader_prim.IsA(UsdShade.Shader):
            continue
        if reachable is not None and shader_prim.GetPath() not in reachable:
            continue
        if plugin.is_supported_prim(shader_prim):
            continue
        issues.append(
            ValidationIssue(
                code="MIXED_NETWORK_CONTEXT",
                message=(
                    f"Unsupported shader in material output network for context '{context_name}': "
                    f"{shader_prim.GetPath()}"
                ),
                severity=ValidationSeverity.ERROR,
                prim_path=str(shader_prim.GetPath()),
                context_name=context_name,
            )
        )
    return issues


def _dedupe(issues: Iterable[ValidationIssue]) -> List[ValidationIssue]:
    """Remove duplicate issues while preserving order."""
    seen: Set[tuple] = set()
    deduped: List[ValidationIssue] = []
    for issue in issues:
        key = (
            issue.code,
            issue.message,
            issue.severity.value,
            issue.prim_path,
            issue.context_name,
            issue.source_path,
            issue.target_path,
            issue.root_path,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(issue)
    return deduped


def validate_material_context(
    root_prim: Optional[Usd.Prim],
    context_name: str,
    plugin: object,
    *,
    can_connect_fn: Optional[Callable[[str, object, ProxyAttribute, ProxyAttribute], bool]] = None,
    model: Optional[object] = None,
) -> ValidationResult:
    """Run core and plugin-specific validation for one context."""
    if not root_prim or not root_prim.IsValid():
        return ValidationResult(
            context_name=context_name,
            issues=[
                ValidationIssue(
                    code="MATERIAL_ROOT_INVALID",
                    message=f"Material root is invalid or unavailable for context '{context_name}'",
                    severity=ValidationSeverity.ERROR,
                    prim_path=None,
                    context_name=context_name,
                )
            ],
        )

    if can_connect_fn is None:

        def _default_can_connect(_context_name, selected_plugin, source_proxy, target_proxy):
            return selected_plugin.can_connect(source_proxy, target_proxy)

        can_connect_fn = _default_can_connect

    root_path = str(root_prim.GetPath())
    issues: List[ValidationIssue] = []
    try:
        context_prims = _collect_context_prims(root_prim, model)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        log_exception(
            logger,
            "validation context collection failed",
            context_name=context_name,
            prim_path=root_path,
            action="collect_context",
            exc=exc,
        )
        context_prims = [root_prim]
        issues.append(_internal_validation_issue(context_name, "collect graph context", exc, root_path))
    try:
        get_output_names = getattr(plugin, "get_material_output_names", None)
        output_names = set(get_output_names()) if callable(get_output_names) else None
        reachable = _collect_output_reachable_connectables(root_prim, output_names)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        log_exception(
            logger,
            "validation reachability collection failed",
            context_name=context_name,
            prim_path=root_path,
            action="collect_reachability",
            exc=exc,
        )
        reachable = set()
        issues.append(_internal_validation_issue(context_name, "collect graph reachability", exc, root_path))

    collectors = (
        ("invalid_nodes", lambda: _collect_invalid_nodes(context_prims, plugin, context_name, reachable)),
        (
            "invalid_nodegraphs",
            lambda: _collect_invalid_nodegraphs(context_prims, context_name, model, reachable),
        ),
        (
            "invalid_shader_ports",
            lambda: _collect_invalid_shader_ports(context_prims, plugin, context_name, reachable),
        ),
        (
            "invalid_connections",
            lambda: _collect_invalid_connections(
                root_prim,
                context_prims,
                plugin,
                context_name,
                can_connect_fn,
                reachable,
            ),
        ),
        ("cycles", lambda: _collect_cycle_issues(root_prim, context_name, reachable)),
        (
            "mixed_networks",
            lambda: _collect_mixed_networks(context_prims, context_name, plugin, reachable),
        ),
    )
    for action, collector in collectors:
        _extend_issues_safely(issues, context_name, action, collector, root_path)

    plugin_issues: List[ValidationIssue] = []
    _extend_issues_safely(
        plugin_issues,
        context_name,
        "plugin_validation",
        lambda: plugin.get_validation_issues(context_name, root_prim),
        root_path,
    )
    for issue in plugin_issues:
        issues.append(issue.with_context(context_name) if issue.context_name is None else issue)

    deduped = _dedupe(issues)
    if deduped:
        logger.info(
            "validation complete context=%s errors=%s warnings=%s total=%s",
            context_name,
            sum(1 for issue in deduped if issue.severity == ValidationSeverity.ERROR),
            sum(1 for issue in deduped if issue.severity == ValidationSeverity.WARNING),
            len(deduped),
        )
    return ValidationResult(context_name=context_name, issues=deduped)
