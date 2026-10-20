"""Connection-management helpers for graph attribute models and USD ports."""

from collections import OrderedDict
from typing import Any, Callable, List, Optional, Sequence, Type

import omni.kit.undo
from pxr import Sdf, Usd, UsdShade

from .....commands.execution import execute_command
from .....commands.wrappers.attributes import LockAttribute, UnlockAttribute
from .....commands.wrappers.ports import ConnectInputToSource, ConnectPortToSource, DisconnectSourcePort
from .....config.logging import logger
from .....utils.modifiers import is_force_connection_modifier_pressed
from .....utils.usd_names import is_internal_nodegraph_interface_connection

# pylint: disable=no-member,protected-access


class AttributeConnections:
    """Connection management for attribute models."""

    def __init__(self, model: Any, attribute_model_cls: Type[Any]) -> None:
        """Initialize instance state for this material graph component."""

        self._model = model
        self._attribute_model_cls = attribute_model_cls
        self._connections = OrderedDict()

    def connected_ports(self) -> List[Any]:
        """Execute connected ports behavior for material graph workflows."""

        return list(self._connections.values())

    def HasConnectedSource(self, model: Optional[Any] = None) -> bool:  # noqa: N802
        """Return whether the model's USD port currently has a connected source."""
        port = getattr(model or self._model, "usdshade_port", None)
        return bool(port and port.HasConnectedSource())

    def clear(self) -> None:
        """Execute clear behavior for material graph workflows."""

        self._connections.clear()
        logger.debug("cleared cached connections")

    def set_connections_for_test(self, connections: dict[Sdf.Path, Any]) -> None:
        """Replace cached connections for tests that exercise sync behavior."""
        self._connections = OrderedDict(connections)

    def set_inputs(self, value: Optional[Sequence[Any]]) -> bool:
        """Author source connections and report whether the requested edit succeeded.

        Existing connections are deliberately left authored until a replacement
        has succeeded.  This makes rewires non-destructive when target-port
        creation or the connect command fails.
        """

        model = self._model
        if value is None:
            value = []
        from ...nodes.prim.model import PrimModel

        if self._should_reject_sources(value, model):
            return False

        stage = model.prim.GetStage() if getattr(model, "prim", None) else None
        edit_layer = stage.GetEditTarget().GetLayer() if stage else None
        layer_snapshot = None
        if edit_layer:
            layer_snapshot = Sdf.Layer.CreateAnonymous("material_graph_connection_transaction.usda")
            layer_snapshot.TransferContent(edit_layer)
        cached_connections = OrderedDict(self._connections)
        proxy_metadata = None
        if getattr(model, "proxy_attribute", None) is not None:
            proxy_metadata = dict(model.proxy_attribute._metadata)

        port_path = getattr(model, "path", None)
        root = getattr(model, "model_root", None)
        suppress = getattr(root, "suppress_stage_listener_property_paths_for_frames", None)
        if port_path and callable(suppress):
            suppress([port_path])

        succeeded = False
        undo_context = omni.kit.undo.disabled() if edit_layer else omni.kit.undo.group()
        with undo_context:
            try:
                source_models = self._build_source_models(value, model, PrimModel)
                if value and len(source_models) != len(value):
                    requested_sources = ", ".join(str(getattr(source, "path", source)) for source in value)
                    logger.warning(
                        "cannot connect target %s: one or more requested source ports could not be resolved; sources=%s",
                        model.path,
                        requested_sources,
                    )
                elif value and not model.create_port():
                    logger.warning(
                        "cannot connect target %s from source(s) %s: target USD port creation failed",
                        model.path,
                        ", ".join(str(source.path) for source in source_models),
                    )
                else:
                    had_connection = bool(
                        model.usdshade_port and (self._connections or model.usdshade_port.HasConnectedSource())
                    )
                    lock_succeeded = True
                    if had_connection and model._pause:
                        lock_result = LockAttribute(model.path)
                        lock_succeeded = lock_result.success
                        model._locked = lock_succeeded
                        if not lock_succeeded:
                            logger.warning("cannot edit %s: attribute lock failed", model.path)

                    if lock_succeeded and value:
                        if self._should_update_interface_variability(model, source_models):
                            self._apply_variability(
                                model,
                                self._variability_from_proxy(source_models[0].proxy_attribute),
                            )

                        connected = self._connect_sources(model, source_models)
                        if connected is not None:
                            self._connections = connected
                            succeeded = True
                    elif lock_succeeded and not had_connection:
                        succeeded = True
                    elif lock_succeeded:
                        result = DisconnectSourcePort(model.usdshade_port)
                        if result.success:
                            self._connections.clear()
                            succeeded = True
                        else:
                            logger.warning(
                                "cannot disconnect target %s: %s",
                                model.path,
                                result.error_code or result.message or "disconnect command was rejected",
                            )
            finally:
                if model._pause and model._locked:
                    unlock_result = UnlockAttribute(model.path)
                    if not unlock_result.success:
                        logger.warning("attribute unlock failed for %s", model.path)
                    model._locked = False

        if succeeded and edit_layer and layer_snapshot:
            after_snapshot = Sdf.Layer.CreateAnonymous("material_graph_connection_after.usda")
            after_snapshot.TransferContent(edit_layer)
            transaction_result = execute_command(
                "MaterialGraph_CommitLayerTransactionCommand",
                target_layer=edit_layer,
                before_layer=layer_snapshot,
                after_layer=after_snapshot,
                already_applied=True,
            )
            if not transaction_result.success:
                logger.warning(
                    "cannot commit connection transaction for target %s: %s",
                    model.path,
                    transaction_result.error_code or transaction_result.message or "transaction command was rejected",
                )
                succeeded = False

        if not succeeded:
            if edit_layer and layer_snapshot:
                edit_layer.TransferContent(layer_snapshot)
            self._connections = cached_connections
            if proxy_metadata is not None and getattr(model, "proxy_attribute", None) is not None:
                model.proxy_attribute._metadata = proxy_metadata
                normalize = getattr(model.proxy_attribute, "_normalize_variability_metadata", None)
                if callable(normalize):
                    normalize()
            if model.model_root:
                model.model_root._item_changed(None)
            return False

        if model.model_root:
            notifier = getattr(model.model_root, "notify_connection_changed", None)
            if callable(notifier):
                notify_item = self._connection_notify_item(model)
                self._schedule_connection_notify_after_undo(lambda: notifier(notify_item))
            else:
                root = model.model_root
                self._schedule_connection_notify_after_undo(lambda: root._item_changed(None))
        return True

    @staticmethod
    def _schedule_connection_notify_after_undo(work: Callable[[], None]) -> None:
        """Run graph notifications immediately after ``set_inputs`` returns."""
        work()

    @staticmethod
    def _connection_notify_item(model: Any) -> Any:
        """Return notification item, using full refresh for root material outputs."""
        try:
            prim = getattr(model, "prim", None)
            proxy = getattr(model, "proxy_attribute", None)
            if (
                prim
                and prim.IsA(UsdShade.Material)
                and proxy is not None
                and str(getattr(proxy, "name", "")).startswith(UsdShade.Tokens.outputs)
            ):
                return None
        except (RuntimeError, ValueError, TypeError, AttributeError):
            pass
        return model

    def _connect_sources(self, model: Any, source_models: List[Any]) -> Optional[OrderedDict]:
        """Connect all sources, returning the new cache only on complete success."""

        connect_fn = ConnectInputToSource
        if isinstance(model.usdshade_port, UsdShade.Output):
            connect_fn = ConnectPortToSource
        connected = OrderedDict()
        for source_model in source_models:
            if not source_model.usdshade_port:
                if hasattr(source_model, "create_port") and callable(source_model.create_port):
                    source_model.create_port()
            if not source_model.usdshade_port:
                logger.warning("cannot connect: source port %s has no USD attribute", source_model.path)
                return None
            result = connect_fn(model.usdshade_port, source_model.usdshade_port)
            if not result.success:
                logger.warning(
                    "cannot connect source %s to target %s: %s",
                    source_model.path,
                    model.path,
                    result.error_code or result.message or "connection command was rejected",
                )
                return None
            connected_source_model = self._resolve_connected_source_model(model, source_model)
            connected[connected_source_model.path] = connected_source_model
            logger.debug("connected %s -> %s", source_model.path, model.path)
        return connected

    @staticmethod
    def _connected_source_paths(port: Any) -> List[Sdf.Path]:
        """Return authored source property paths for a connected UsdShade port."""
        if not port or not port.HasConnectedSource():
            return []
        sources = port.GetConnectedSources()
        sources = sources[0] if isinstance(sources, tuple) else sources
        paths: List[Sdf.Path] = []
        for source in sources or []:
            if not source:
                continue
            source_type = source.sourceType if hasattr(source, "sourceType") else UsdShade.AttributeType.Output
            source_name = source.sourceName if hasattr(source, "sourceName") else ""
            source_api = source.source if hasattr(source, "source") else source
            prefix = UsdShade.Tokens.inputs if source_type == UsdShade.AttributeType.Input else UsdShade.Tokens.outputs
            try:
                paths.append(source_api.GetPrim().GetPath().AppendProperty(f"{prefix}{source_name}"))
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning(
                    "skipping invalid connected source '%s' with prefix '%s': %s",
                    source_name,
                    prefix,
                    exc,
                )
        return paths

    @classmethod
    def _connected_source_path(cls, port: Any) -> Optional[Sdf.Path]:
        """Return the first authored source property path for a connected UsdShade port."""
        paths = cls._connected_source_paths(port)
        return paths[0] if paths else None

    def _resolve_connected_source_model(self, model: Any, fallback_source_model: Any) -> Any:
        """Resolve the post-command source model from USD, falling back to the original model."""
        source_path = self._connected_source_path(model.usdshade_port)
        if source_path and getattr(model, "model_root", None):
            resolved = model.model_root.get_item_model(source_path)
            if resolved:
                return resolved
        return fallback_source_model

    def _should_reject_sources(self, value: Sequence[Any], model: Any) -> bool:
        """Execute should reject sources behavior for material graph workflows."""
        force_connection = is_force_connection_modifier_pressed()

        for source in value:
            source_model = (
                source
                if isinstance(source, self._attribute_model_cls)
                else self._model.model_root.get_item_model(source)
            )
            if not isinstance(source_model, self._attribute_model_cls):
                continue

            is_internal_interface = is_internal_nodegraph_interface_connection(source_model, model)

            if is_internal_interface:
                continue

            if force_connection:
                if model.validator.would_create_cycle(source_model, model):
                    logger.debug("rejected cyclical force connection for %s: %s", model.path, source_model.path)
                    return True
                continue

            if not model.validator.can_connect(
                model.context_name,
                model._plugin,
                source_model,
                model,
            ):
                logger.debug(
                    "rejected incompatible source for %s: %s",
                    model.path,
                    source_model.path,
                )
                return True
        if force_connection:
            logger.debug("force connection enabled; bypassing compatibility checks for %s", model.path)
        return False

    def _should_update_interface_variability(self, model: Any, source_models: List[Any]) -> bool:
        """Execute should update interface variability behavior for material graph workflows."""

        if not source_models or not self._is_interface_port(model):
            return False
        if model.connected_ports:
            return False
        return True

    @staticmethod
    def _is_interface_port(model: Any) -> bool:
        """Execute is interface port behavior for material graph workflows."""

        attr_name = model.attribute_name
        if not isinstance(attr_name, str):
            return False
        if not (attr_name.startswith(UsdShade.Tokens.inputs) or attr_name.startswith(UsdShade.Tokens.outputs)):
            return False
        prim = model.prim
        return bool(prim and (prim.IsA(UsdShade.Material) or prim.IsA(UsdShade.NodeGraph)))

    @staticmethod
    def _variability_from_proxy(proxy_attribute: Any) -> Sdf.Variability:
        """Execute variability from proxy behavior for material graph workflows."""

        if proxy_attribute:
            variability = proxy_attribute.variability
            if variability in (Sdf.VariabilityUniform, Sdf.VariabilityVarying):
                return variability
        return Sdf.VariabilityVarying

    @staticmethod
    def _apply_variability(model: Any, variability: Sdf.Variability) -> None:
        """Execute apply variability behavior for material graph workflows."""

        port = model.usdshade_port
        if port:
            attr = port.GetAttr()
            if attr:
                attr.SetVariability(variability)
        proxy_attribute = model.proxy_attribute
        if proxy_attribute is not None:
            proxy_attribute._metadata["variability"] = str(variability)
            normalize = getattr(proxy_attribute, "_normalize_variability_metadata", None)
            if callable(normalize):
                normalize()

    def _build_source_models(self, value: Sequence[Any], model: Any, prim_cls: Type[Any]) -> List[Any]:
        """Execute build source models behavior for material graph workflows."""

        source_models: List[Any] = []
        for source in value:
            source_model = None
            if isinstance(source, self._attribute_model_cls):
                source_model = source
            elif isinstance(source, prim_cls):
                source_model = source.create_port(model)
            if source_model:
                source_models.append(source_model)
        return source_models

    def sync(self) -> None:
        """Execute sync behavior for material graph workflows."""

        model = self._model
        if not model.usdshade_port:
            self._connections.clear()
            return

        existing = list(self._connections.keys())
        added = []
        if model.usdshade_port.HasConnectedSource():
            keep_existing = False
            prop_paths = self._connected_source_paths(model.usdshade_port)
            if not prop_paths:
                added.extend(existing)
            for prop_path in prop_paths:
                added.append(prop_path)
                port_model = model.model_root.get_item_model(prop_path) if getattr(model, "model_root", None) else None
                if port_model:
                    self._connections[port_model.path] = port_model
                elif prop_path not in self._connections:
                    keep_existing = True
            if keep_existing:
                added.extend(existing)

        remove = [key for key in existing if key not in added]
        for key in remove:
            del self._connections[key]
            logger.debug("disconnected %s", key)

    def get_connected_prims(self, recurse_nodegraphs: bool = True) -> List[Usd.Prim]:
        """Execute get connected prims behavior for material graph workflows."""

        reachable_prims = []
        visited_prims = set()
        visited_ports = set()
        traversed_prims = set()

        self._walk_connected_port(
            self._model.usdshade_port,
            recurse_nodegraphs,
            reachable_prims,
            visited_prims,
            visited_ports,
            traversed_prims,
        )
        return reachable_prims

    @staticmethod
    def _enqueue_prim(prim: Usd.Prim, reachable_prims: List[Usd.Prim], visited_prims: set) -> None:
        """Execute enqueue prim behavior for material graph workflows."""

        if not prim or not prim.IsValid():
            return
        if prim.IsA(UsdShade.Material):
            return
        prim_path = prim.GetPath()
        if prim_path in visited_prims:
            return
        visited_prims.add(prim_path)
        reachable_prims.append(prim)

    @classmethod
    def _walk_connected_port(
        cls,
        port: Optional[Usd.Attribute],
        recurse_nodegraphs: bool,
        reachable_prims: List[Usd.Prim],
        visited_prims: set,
        visited_ports: set,
        traversed_prims: set,
    ) -> None:
        """Execute walk connected port behavior for material graph workflows."""

        if not port:
            return
        port_get_path = getattr(port, "GetPath", None)
        if callable(port_get_path):
            visited_ports.add(port_get_path())
        else:
            # Some USD wrappers (e.g. tests/fake ports) do not expose GetPath.
            visited_ports.add(str(port))
        sources = port.GetConnectedSources()
        sources = sources[0] if isinstance(sources, tuple) else sources

        for source in sources:
            if not source:
                continue
            source_get_path = getattr(source.source, "GetPath", None)
            source_key = source_get_path() if callable(source_get_path) else str(source.source)
            if source_key in visited_ports:
                continue
            visited_ports.add(source_key)

            prim = source.source.GetPrim()
            if not prim or not prim.IsValid():
                continue

            cls._enqueue_prim(prim, reachable_prims, visited_prims)

            if recurse_nodegraphs and prim.IsA(UsdShade.NodeGraph) and prim not in traversed_prims:
                traversed_prims.add(prim)
                for output in UsdShade.NodeGraph(prim).GetOutputs():
                    cls._walk_connected_port(
                        output, recurse_nodegraphs, reachable_prims, visited_prims, visited_ports, traversed_prims
                    )
