"""Implement material graph extension logic for `models/graph/nodes/prim/model.py`."""

from typing import Any, List, Optional, Union

from omni.kit.widget.graph import GraphModel, IsolationGraphModel
from pxr import Gf, Sdf, Usd, UsdShade, UsdUI

from .....commands.wrappers.ports import CreateInputPort, CreateOutputPort
from .....commands.wrappers.prims import RenamePrim
from .....commands.wrappers.ui_nodes import RemovePosition, SetDisplayColor, SetPosition, SetSize
from .....config.logging import logger
from .....config.nodes import Nodes
from ...core.base import GraphModelBase
from ...ports import (
    AttributeModel,
    InputAttributeGroupModel,
    InputAttributeModel,
    OutputAttributeGroupModel,
    OutputAttributeModel,
)
from .ports import PrimPortSync
from .schema import SchemaAttributeCollector
from .ui_state import PrimUiState


class PrimModel(GraphModelBase):
    """Base model for USD prims in the graph."""

    def __init__(
        self,
        prim: Usd.Prim,
        context_name: str,
        usd_context: Any,
        plugin: Any,
        parent: Any,
        schema_type: Any,
        sync: bool = True,
    ) -> None:
        """Initialize the prim model and its port groups."""
        prim_path = prim.GetPath()
        super().__init__(prim_path.name, schema_type, prim_path, parent, prim, context_name, usd_context, plugin, False)

        self._inputs = InputAttributeGroupModel(self, prim, context_name, usd_context, plugin, False)
        self._outputs = OutputAttributeGroupModel(self, prim, context_name, usd_context, plugin, False)

        self._description = None

        self._expansion_state = GraphModel.ExpansionState.OPEN
        self._sizes_on_begin_end = {}
        self._isolation_model = None
        self._ui_state = PrimUiState(self._prim, Nodes.Backdrop.DEFAULT_SIZE)

        self._schema_attribute_collector = SchemaAttributeCollector(self._prim)
        self._schema_attributes = {}
        self._applied_schemas_cache = None
        self._port_sync = PrimPortSync(self._prim, self._inputs, self._outputs, self._schema_attribute_collector)
        self._input_port_sig: Optional[tuple] = None
        self._output_port_sig: Optional[tuple] = None
        if sync:
            self.sync()

        self._item_changed_subscription = self.subscribe_item_changed(self._on_item_changed_cb)

    def clear(self) -> None:
        """Reset schema/UI caches and clear transient sync state for this model."""
        self._clear_schema_cache()
        self._clear_ui_cache()
        if self._port_sync:
            self._port_sync.clear()
        super().clear()

    def _clear_schema_cache(self) -> None:
        """Drop cached applied-schema attributes so they are recollected on next sync."""
        self._schema_attributes = {}
        self._applied_schemas_cache = None

    def _clear_ui_cache(self) -> None:
        """Reset cached UI-derived values used for position, size, and display state."""
        self._sizes_on_begin_end = {}
        if self._ui_state:
            self._ui_state.clear()

    def destroy(self) -> None:
        """Destroy child models and release subscriptions."""
        if self._item_changed_subscription:
            try:
                self._item_changed_subscription.unsubscribe()
            except AttributeError:
                try:
                    self._item_changed_subscription.release()
                except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
                    logger.debug("item_changed unsubscribe skipped: %s", exc)
            except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
                logger.debug("item_changed unsubscribe skipped: %s", exc)
        self._item_changed_subscription = None
        if self._inputs:
            self._inputs.destroy()
        if self._outputs:
            self._outputs.destroy()
        self._inputs = None
        self._outputs = None
        self._ui_state = None
        self._port_sync = None
        self._schema_attribute_collector = None
        self._schema_attributes = {}
        super().destroy()

    def _on_item_changed_cb(self, item: Optional[Any] = None) -> None:
        """Route graph item-change callbacks to the appropriate model instance."""
        if not item:
            self.on_item_changed(None)
        else:
            model = self.get_item_model(item)
            if model:
                model.on_item_changed(item)

    def on_item_changed(self, item: Optional[Any]) -> None:
        """Respond to item changes by syncing from USD."""
        if not self.prim_exists():
            return
        self.sync()

    def get_property_model(self, item: Any) -> Optional[Any]:
        """Resolve input/output property paths to their corresponding port child models."""
        if item.name.startswith(UsdShade.Tokens.inputs):
            return self._inputs.get_child_by_path(item)

        if item.name.startswith(UsdShade.Tokens.outputs):
            return self._outputs.get_child_by_path(item)

    def sync_description(self) -> None:
        """Refresh description cache from authored metadata fields on the backing prim."""
        self._description = None

    def set_valid(self) -> None:
        """Recompute validity by checking whether the backing USD prim still exists."""
        self._valid = self.prim_exists()

    def get_input_attributes(self, input_proxy_attributes: List[Any]) -> None:
        """Collect and append input proxy attributes discovered on the backing prim."""
        self._port_sync.collect_inputs(input_proxy_attributes)

    def _port_signature(self, is_output: bool) -> Optional[tuple]:
        """Return a lightweight signature of port names and types for change detection."""
        if not self._prim:
            return None
        api = UsdShade.ConnectableAPI(self._prim)
        if not api:
            return None
        ports = api.GetOutputs() if is_output else api.GetInputs()
        return tuple((p.GetFullName(), str(p.GetTypeName())) for p in ports)

    def sync_inputs(self) -> None:
        """Rebuild input proxy attributes and synchronize the input group model tree."""
        sig = self._port_signature(False)
        if sig is not None and sig == self._input_port_sig:
            return
        self._input_port_sig = sig
        input_proxy_attributes = []
        self.get_input_attributes(input_proxy_attributes)
        input_proxy_attributes = self._schema_attribute_collector.insert_schema_attributes(
            False,
            input_proxy_attributes,
            self._schema_attributes,
        )
        self._inputs.sync(input_proxy_attributes)

    def get_output_attributes(self, output_proxy_attributes: List[Any]) -> None:
        """Collect and append output proxy attributes discovered on the backing prim."""
        self._port_sync.collect_outputs(output_proxy_attributes)

    def sync_outputs(self) -> None:
        """Rebuild output proxy attributes and synchronize the output group model tree."""
        sig = self._port_signature(True)
        if sig is not None and sig == self._output_port_sig:
            return
        self._output_port_sig = sig
        output_proxy_attributes = []
        self.get_output_attributes(output_proxy_attributes)
        output_proxy_attributes = self._schema_attribute_collector.insert_schema_attributes(
            True,
            output_proxy_attributes,
            self._schema_attributes,
        )
        self._outputs.sync(output_proxy_attributes)

    def sync(self, *args: Any, **kwargs: Any) -> None:
        """Synchronize schema, ports, and UI caches from current USD prim state."""
        stage = self._get_stage()
        if stage and (not self._prim or not self._prim.IsValid()):
            refreshed = stage.GetPrimAtPath(self._prim_path)
            if refreshed and refreshed.IsValid():
                self._prim = refreshed
            else:
                logger.warning("prim sync failed: missing prim %s", self._prim_path)
                self._valid = False
                self.clear()
                return

        if not self.prim_exists():
            logger.warning("prim sync failed: prim no longer exists %s", self._prim_path)
            self._valid = False
            self.clear()
            return

        self.set_valid()
        applied_schemas = tuple(self._prim.GetAppliedSchemas())
        if applied_schemas != self._applied_schemas_cache:
            self._schema_attributes = self._schema_attribute_collector.collect()
            self._applied_schemas_cache = applied_schemas
        self.sync_outputs()
        self.sync_inputs()
        self.sync_description()
        self.sync_ui()

    def sync_size(self) -> None:
        """Refresh cached node size from the UI-state helper derived from USD metadata."""
        self._ui_state.sync_size()

    def sync_position(self) -> None:
        """Refresh cached node position from the UI-state helper derived from USD metadata."""
        self._ui_state.sync_position()

    def sync_ui(self) -> None:
        """Refresh all cached UI fields (position/size/color/order/preview) from USD."""
        self.sync_position()
        self.sync_size()
        self._ui_state.sync_ui()

    def sync_ports(self) -> None:
        """Synchronize runtime connection state for both input and output port groups."""
        self._outputs.sync_ports()
        self._inputs.sync_ports()

    def set_pause(self, enabled: bool) -> None:
        """Propagate pause/resume state to input and output port group models."""
        self._inputs.set_pause(enabled)
        self._outputs.set_pause(enabled)

    def set_name(self, value: str) -> bool:
        """Rename the backing prim, reporting failure without refreshing caches."""
        result = RenamePrim(self.prim, value)
        if not result.success:
            logger.warning(
                "rename prim failed source='%s' requested_name='%s': %s; the original name was preserved",
                self.prim_path,
                value,
                result.error_code or result.message or "command returned no reason",
            )
            return False
        self._clear_schema_cache()
        if self._parent and self._parent.model_root:
            self._parent.model_root._item_changed(self)
        return True

    @property
    def prim_model(self, item: Optional[Any] = None) -> "PrimModel":
        """Return the owning prim model, delegating through proxy items when provided."""
        return item.prim_model if item else self

    @property
    def preview(self, item: Optional[Any] = None) -> Optional[Union[str, Any]]:
        """Return the preview icon asset path authored for this node, when available."""
        if item:
            return item.preview

    @property
    def inputs(self, item: Optional[Any] = None) -> Optional[Any]:
        """Return input-port group model, delegating to proxy items when requested."""
        return item.inputs if item else None

    @inputs.setter
    def inputs(self, value: Any, item: Optional[Any] = None) -> None:
        """Forward input-group assignments to proxy items that manage their own state."""
        if item:
            item.inputs = value

    @property
    def outputs(self, item: Optional[Any] = None) -> Optional[Any]:
        """Return output-port group model, delegating to proxy items when requested."""
        return item.outputs if item else None

    @property
    def ports(self, item: Optional[Any] = None) -> List[Any]:
        """Return combined input/output port models for this prim or delegated item."""
        return item.ports if item else (self._outputs.ports + self._inputs.ports)

    @ports.setter
    def ports(self, value: Any, item: Optional[Any] = None) -> None:
        """Forward complete port-list updates to proxy items in delegated contexts."""
        if item:
            item.ports = value

    @property
    def expansion_state(self, item: Optional[Any] = None) -> GraphModel.ExpansionState:
        """Return expanded/collapsed state, with special handling for isolation placeholders."""
        if isinstance(item, IsolationGraphModel.EmptyPort):
            return self.ExpansionState.OPEN
        return item.expansion_state if item else self._expansion_state

    @expansion_state.setter
    def expansion_state(self, value: GraphModel.ExpansionState, item: Optional[Any] = None) -> None:
        """Persist expansion-state changes for this model or delegated child/proxy items."""
        if item is None:
            model = self
        elif isinstance(item, PrimModel):
            if item._expansion_state != value:
                item._expansion_state = value
                if item.model_root:
                    item.model_root._item_changed(None)
            return
        elif item is not self and "expansion_state" in dir(item):
            item.expansion_state = value
            if item.model_root:
                item.model_root._item_changed(None)
            return
        else:
            model = self.get_item_model(item)
            if not model:
                return
        if model != self:
            model.expansion_state = value
        elif self._expansion_state != value:
            self._expansion_state = value
            self.model_root._item_changed(None)

    def remove_position_cmd(self) -> Any:
        """Remove persisted UI position metadata from the backing prim."""
        stage = self._get_command_stage()
        if stage:
            return RemovePosition(self._prim_path, stage=stage)
        return RemovePosition(self._prim_path)

    def _get_command_stage(self) -> Optional[Usd.Stage]:
        """Return the backing prim's stage without requiring proxy properties."""
        prim = getattr(self, "_prim", None)
        get_stage = getattr(prim, "GetStage", None)
        return get_stage() if callable(get_stage) else None

    def set_position_cmd(self, value: Any, prev: Any = None) -> Any:
        """Persist UI position metadata with previous value for undo-aware commands."""
        command_args = (
            self.prim_path,
            value,
            self._ui_state.position if prev is None else prev,
            self.type == UsdShade.Material,
            self._context_name,
        )
        stage = self._get_command_stage()
        if stage:
            return SetPosition(*command_args, stage=stage)
        return SetPosition(*command_args)

    def _positions_close(self, current_value: Any, value: Any) -> bool:
        """Return whether two position values are equivalent within numeric tolerance."""
        if value is None:
            return current_value is None
        elif current_value is None:
            return value is None
        # Context custom data created from Python tuples can resolve to Vec2d,
        # while GraphCanvas and later context-position updates provide Vec2f.
        # Gf.IsClose only accepts vectors with matching scalar types, so
        # normalize both operands before selecting the C++ overload.
        return Gf.IsClose(Gf.Vec2d(current_value), Gf.Vec2d(value), 1e-3)

    @property
    def position(self, item: Optional[Any] = None) -> Any:
        """Return cached node position for this model or delegated proxy item."""
        return item.position if item else self._ui_state.position

    @position.setter
    def position(self, value: Any, item: Optional[Any] = None) -> None:
        """Update node position and author USD metadata when the value actually changed."""
        self.set_position(value, item=item)

    def set_position(self, value: Any, item: Optional[Any] = None, notify: bool = True) -> bool:
        """Update node position, optionally notifying observers without forcing a full sync."""
        if item and item != self:
            set_position = getattr(item, "set_position", None)
            if callable(set_position):
                result = set_position(value, notify=notify)
            else:
                item.position = value
                result = True
            return result is not False
        elif not self._positions_close(self._ui_state.position, value):
            previous = self._ui_state.position
            if value is None:
                result = self.remove_position_cmd()
            else:
                result = self.set_position_cmd(value, prev=previous)

            if not getattr(result, "success", False):
                logger.warning(
                    "set node position failed for prim='%s' requested_position=%s: %s; "
                    "the previous position=%s was preserved",
                    self.prim_path,
                    value,
                    getattr(result, "error_code", None)
                    or getattr(result, "message", None)
                    or "command returned no reason",
                    previous,
                )
                return False

            self._ui_state.position = value

            if notify:
                notifier = getattr(self.model_root, "notify_position_changed", None)
                if callable(notifier):
                    notifier(self)
                else:
                    self.model_root._item_changed(self)
        return True

    def set_size_cmd(self, value: Any) -> None:
        """Apply size metadata authoring; concrete subclasses provide implementation."""
        pass

    @property
    def size(self, item: Optional[Any] = None) -> Any:
        """Return cached node size used by graph layout and editing interactions."""
        return item.size if item else self._ui_state.size

    @size.setter
    def size(self, value: Any, item: Optional[Any] = None) -> None:
        """Track in-progress size edits so final changes can be committed atomically."""
        if item and item.prim_path in self._sizes_on_begin_end:
            self._sizes_on_begin_end[item.prim_path][1] = value

    def size_begin_edit(self, item: Any) -> None:
        """Record size at the start of a drag/resize."""
        size = item.size
        self._sizes_on_begin_end[item.prim_path] = [size, size]

    def size_end_edit(self, item: Any) -> bool:
        """Apply size change at the end of a drag/resize."""
        if item and (item.prim_path in self._sizes_on_begin_end):
            value = self._sizes_on_begin_end[item.prim_path]
            self._sizes_on_begin_end.pop(item.prim_path)
            if value[0] != value[1]:
                result = item.set_size_cmd(value)
                if result is False or not getattr(result, "success", True):
                    logger.warning("set node size failed for %s", item.prim_path)
                    return False
        return True

    @property
    def description(self, item: Optional[Any] = None) -> Optional[str]:
        """Return human-readable description text used in tooltips and editors."""
        return item.description if item else self._description

    @description.setter
    def description(self, value: str, item: Optional[Any] = None) -> None:
        """Delegate description updates to backdrop models."""
        from ..backdrop import BackdropModel

        model = self.get_item_model(item)
        if isinstance(model, BackdropModel):
            model.description = value

    @property
    def display_color(self, item: Optional[Any] = None) -> Any:
        """Return node display-color value from UI cache or delegated item."""
        return item.display_color if item else self._ui_state.display_color

    @display_color.setter
    def display_color(self, value: Any, item: Optional[Any] = None) -> None:
        """Set display color and author USD UI metadata."""

        self.set_display_color(value, item)

    def set_display_color(self, value: Any, item: Optional[Any] = None) -> bool:
        """Set display color and report whether USD authoring succeeded."""
        if item and item != self:
            setter = getattr(item, "set_display_color", None)
            if callable(setter):
                return setter(value) is not False
            item.display_color = value
            return True
        if value is None:
            return False

        def _to_color3(color_value: Any) -> Optional[tuple[float, float, float]]:
            """Execute to color3 behavior for material graph workflows."""

            try:
                values = tuple(color_value)
            except TypeError:
                return None
            if len(values) < 3:
                return None
            return (float(values[0]), float(values[1]), float(values[2]))

        new_color = _to_color3(value)
        if new_color is None:
            return False

        current_color = _to_color3(self._ui_state.display_color)
        if current_color and all(abs(a - b) <= 1e-6 for a, b in zip(current_color, new_color)):
            return True

        stage = self._get_command_stage()
        if stage:
            result = SetDisplayColor(self.prim_path, new_color, current_color, stage=stage)
        else:
            result = SetDisplayColor(self.prim_path, new_color, current_color)
        if not result.success:
            logger.warning(
                "set node display color failed for prim='%s' requested_color=%s: %s; color was not changed",
                self.prim_path,
                new_color,
                result.error_code or result.message or "command returned no reason",
            )
            return False
        self._ui_state.display_color = new_color
        if self.model_root:
            self.model_root._item_changed(self)
        return True

    @property
    def stacking_order(self, item: Optional[Any] = None) -> Any:
        """Return node stacking order, defaulting to zero when metadata is unset."""
        value = item.stacking_order if item else self._ui_state.stacking_order
        return 0 if value is None else value

    @property
    def add_empty_output_port(self, item: Optional[Any] = None) -> bool:
        """Return whether this node should render placeholder output-port UI rows."""
        from ..material import MaterialModel

        return not isinstance(item, MaterialModel)

    def create_input_port(
        self,
        name: str,
        value_type_name: Any,
        unique_name: bool = True,
        variability: Optional[Any] = None,
    ) -> Optional[InputAttributeModel]:
        """Create an input USD attribute port on this prim and return its model wrapper."""
        return self._inputs.create_port(name, value_type_name, unique_name, variability=variability)

    def create_output_port(
        self,
        name: str,
        value_type_name: Any,
        unique_name: bool = True,
        variability: Optional[Any] = None,
    ) -> Optional[OutputAttributeModel]:
        """Create an output USD attribute port on this prim and return its model wrapper."""
        return self._outputs.create_port(name, value_type_name, unique_name, variability=variability)

    def create_port(self, model: AttributeModel) -> Optional[Union[InputAttributeModel, OutputAttributeModel]]:
        """Create an input/output USD port mirroring the source model contract."""
        variability = None
        if model.proxy_attribute is not None:
            variability = model.proxy_attribute.variability
            if variability not in (Sdf.VariabilityUniform, Sdf.VariabilityVarying):
                variability = None
        if isinstance(model, InputAttributeModel):
            port_model = self.create_input_port(model.attribute_name, model.type, variability=variability)
        elif isinstance(model, OutputAttributeModel):
            port_model = self.create_output_port(model.attribute_name, model.type, variability=variability)
        else:
            return None

        if port_model and model.proxy_attribute is not None and port_model.proxy_attribute is not None:
            port_model.proxy_attribute.polymorphic_unresolved = getattr(
                model.proxy_attribute, "polymorphic_unresolved", False
            )
            port_model.update_proxy_attribute(port_model.proxy_attribute)
        return port_model

    @property
    def connected_ports(self, item: Optional[Any] = None) -> List[Any]:
        """Return all connected input/output ports, optionally from a proxy item."""
        if item:
            return item.connected_ports
        return self._outputs.connected_ports + self._inputs.connected_ports

    @connected_ports.setter
    def connected_ports(self, value: Any, item: Optional[Any] = None) -> None:
        """Forward connected-port updates to proxy items that manage their own state."""
        if item:
            item.connected_ports = value

    @property
    def isolation_model(self, item: Optional[Any] = None) -> Optional[Any]:
        """Return isolation model backing IO-node projection for this prim model."""
        return item.isolation_model if item else self._isolation_model

    @isolation_model.setter
    def isolation_model(self, value: Any) -> None:
        """Store isolation model used when this node is shown in isolation mode."""
        self._isolation_model = value

    @property
    def tooltip_text(self, item: Optional[Any] = None) -> str:
        """Build tooltip text including prim identity and authored description when present."""
        if item:
            if isinstance(item, IsolationGraphModel.EmptyPort):
                return IsolationGraphModel.EmptyPort.get_type_name()
            else:
                return item.tooltip_text

        text = f"{self._prim_path}\t({self.type.__name__})"
        if self._description:
            text += f"\n\nDescription:\n\t{self._description}"
        return text
