"""Attribute-level port model used for typed input/output graph socket behavior."""

from typing import Any, List, Optional, Sequence, Type

from omni.kit.widget.graph import GraphModel
from pxr import Sdf, Sdr, UsdShade

from .....commands.result import CommandResult
from .....commands.wrappers.attributes import RenameProperty, UnlockAttribute
from .....config.logging import logger
from .....config.paths import Paths
from .....utils.modifiers import is_force_connection_modifier_pressed
from ...core.base import GraphModelBase
from ..internal.connections import AttributeConnections
from ..internal.metadata import AttributeMetadata
from ..internal.style_cache import AttributeStyleCache
from ..proxy import ProxyAttribute


def _desaturate_abgr(color: int, amount: float) -> int:
    """Return an ABGR color desaturated by amount (0..1)."""
    if not isinstance(color, int):
        return color
    amount = max(0.0, min(1.0, amount))
    a = (color >> 24) & 0xFF
    b = (color >> 16) & 0xFF
    g = (color >> 8) & 0xFF
    r = color & 0xFF
    gray = int(round(0.299 * r + 0.587 * g + 0.114 * b))
    r = int(round(r * (1.0 - amount) + gray * amount))
    g = int(round(g * (1.0 - amount) + gray * amount))
    b = int(round(b * (1.0 - amount) + gray * amount))
    return (a << 24) | (b << 16) | (g << 8) | r


class AttributeModel(GraphModelBase):
    """Base model for shader input/output attributes."""

    def __init__(
        self,
        parent: Any,
        prim: Any,
        context_name: str,
        usd_context: Any,
        plugin: Any,
        pause: bool,
        proxy_attribute: Any,
        port_cls: Any,
    ) -> None:
        """Initialize instance state for this material graph component."""

        self._proxy_attribute = proxy_attribute
        self._metadata = AttributeMetadata(self._proxy_attribute, parent)
        self._attribute_name = self._metadata.attribute_name
        super().__init__(
            self._metadata.name,
            self._metadata.type_name,
            self._metadata.path,
            parent,
            prim,
            context_name,
            usd_context,
            plugin,
            pause,
        )

        self._expansion_state = GraphModel.ExpansionState.OPEN
        self._locked = False
        self._connections = AttributeConnections(self, AttributeModel)
        self._port_cls = port_cls
        self._usdshade_port = None

        attribute = self.stage.GetAttributeAtPath(self.path) if self.stage else None
        if attribute:
            self._usdshade_port = self._port_cls(attribute)
        self._style = self.get_style(self.type, self._proxy_attribute)

    @classmethod
    def create(
        cls,
        parent: Any,
        prim: Any,
        context_name: str,
        usd_context: Any,
        plugin: Any,
        pause: bool,
        name: str,
        value_type_name: Any,
        port_create_cmd: Any,
        model_cls: Type["AttributeModel"],
        variability: Optional[Sdf.Variability] = None,
    ) -> Optional["AttributeModel"]:
        """Execute create behavior for material graph workflows."""

        port_name = name.removeprefix(UsdShade.Tokens.inputs).removeprefix(UsdShade.Tokens.outputs)
        usdshade_port = port_create_cmd(
            prim.GetPath(),
            port_name,
            value_type_name,
            variability=variability,
            stage=prim.GetStage(),
        )
        if isinstance(usdshade_port, CommandResult):
            usdshade_port = usdshade_port.payload if usdshade_port.success else None
        if not usdshade_port:
            return None

        attr = usdshade_port.GetAttr()
        if not attr:
            return None
        is_output = isinstance(usdshade_port, UsdShade.Output)
        proxy_attribute = ProxyAttribute(attr.GetName(), is_output, attribute=attr)
        return model_cls(parent, prim, context_name, usd_context, plugin, pause, proxy_attribute)

    @property
    def prim_model(self, item: Optional[Any] = None) -> Any:
        """Execute prim model behavior for material graph workflows."""

        if item:
            return item.prim_model
        if self.parent:
            return self.parent.prim_model
        return None

    def _get_candidate_port_types(self) -> list:
        """Return candidate type names for this port from the parent ShaderModel."""
        pm = self.prim_model
        if pm is None:
            return []
        get_types = getattr(pm, "_get_candidate_port_types", None)
        if not callable(get_types):
            return []
        is_input = self._proxy_attribute.name.startswith(UsdShade.Tokens.inputs)
        port_name = self._proxy_attribute.name.removeprefix(UsdShade.Tokens.inputs).removeprefix(
            UsdShade.Tokens.outputs
        )
        return get_types(port_name, is_input)

    @property
    def attribute_name(self) -> str:
        """Execute attribute name behavior for material graph workflows."""

        return self._attribute_name

    @property
    def connected_ports(self, item: Optional[Any] = None) -> List[Any]:
        """Execute connected ports behavior for material graph workflows."""

        return item.connected_ports if item else self._connections.connected_ports()

    @classmethod
    def get_style(cls, value_type_name: Any, proxy_attribute: Any) -> Any:
        """Execute get style behavior for material graph workflows."""

        style = AttributeStyleCache.get_style(value_type_name, proxy_attribute)
        try:
            if proxy_attribute and proxy_attribute.variability == Sdf.VariabilityUniform:
                port_type = str(value_type_name)
                style_key = f"Graph.Node.Port.Input.Icon::{port_type}"
                entry = dict(style.get(style_key, {}))
                entry["image_url"] = str(Paths.ICON_PATH / "omnigraph_input_value_dark_uniform.svg")
                if entry:
                    style = dict(style)
                    style[style_key] = entry
                output_key = f"Graph.Node.Port.Output.CustomColor::{port_type}"
                out_entry = dict(style.get(output_key, {}))
                port_color = out_entry.get("border_color", out_entry.get("background_color"))
                if port_color is not None:
                    out_entry["background_color"] = _desaturate_abgr(port_color, 0.85)
                    style = dict(style)
                    style[output_key] = out_entry
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:  # pylint: disable=broad-exception-caught
            logger.debug("uniform style override skipped: %s", exc)
        return style

    @property
    def usdshade_port(self, item: Optional[Any] = None) -> Optional[Any]:
        """Execute usdshade port behavior for material graph workflows."""

        return item.usdshade_port if item else self._usdshade_port

    @usdshade_port.setter
    def usdshade_port(self, value, item: Optional[Any] = None) -> None:
        """Execute usdshade port behavior for material graph workflows."""

        if item:
            item.usdshade_port = value
        else:
            self._usdshade_port = value

    @property
    def style(self, item: Optional[Any] = None) -> Any:
        """Execute style behavior for material graph workflows."""

        return item.style if item else self._style

    @property
    def proxy_attribute(self, item: Optional[Any] = None) -> Any:
        """Execute proxy attribute behavior for material graph workflows."""

        return item.proxy_attribute if item else self._proxy_attribute

    def __eq__(self, other: Any) -> bool:
        """Execute eq behavior for material graph workflows."""

        return (
            isinstance(other, AttributeModel)
            and self.path == other.path
            and self.name == other.name
            and self.type == other.type
            and self.display_group == other.display_group
        )

    def __hash__(self) -> int:
        """Execute hash behavior for material graph workflows."""

        return hash((self.path, self.name, self.type, type(self), self.display_group))

    @property
    def display_group(self, item: Optional[Any] = None) -> str:
        """Execute display group behavior for material graph workflows."""

        if item:
            return item.display_group
        if self.parent:
            return self.parent.display_group
        return ""

    def on_item_changed(self, item: Any) -> None:
        """Execute on item changed behavior for material graph workflows."""

        if self.model_root:
            self.model_root._item_changed(None)

    def update_proxy_attribute(self, proxy_attribute: Any) -> None:
        """Execute update proxy attribute behavior for material graph workflows."""

        if proxy_attribute is None:
            return
        self._proxy_attribute = proxy_attribute
        self._metadata.update(self._proxy_attribute, self.parent)
        self._attribute_name = self._metadata.attribute_name
        self._name = self._metadata.name
        self._type = self._metadata.type_name
        self._path = self._metadata.path
        self._style = self.get_style(self.type, self._proxy_attribute)

    def set_pause(self, enabled: bool) -> None:
        """Execute set pause behavior for material graph workflows."""

        super().set_pause(enabled)
        if not self._pause and self._locked:
            result = UnlockAttribute(self.path)
            if result.success:
                self._locked = False
            else:
                logger.warning(
                    "unlock attribute failed for '%s': %s; the port remains locked",
                    self.path,
                    result.error_code or result.message or "command returned no reason",
                )

    def set_name(self, value: str) -> bool:
        """Execute set name behavior for material graph workflows."""

        new_path = self.path.ReplaceName(value)
        if new_path == self.path:
            return True
        if self.stage.GetAttributeAtPath(new_path):
            logger.warning("rename attribute failed: target already exists at %s", new_path)
            return False
        result = RenameProperty(self.path.GetPrimPath(), self._attribute_name, value, stage=self.prim.GetStage())
        if not result.success:
            logger.warning(
                "rename attribute failed source='%s' requested_name='%s': %s; the original attribute was preserved",
                self.path,
                value,
                result.error_code or result.message or "command returned no reason",
            )
        return result.success

    def create_port(self, prefix: str, create_port_cmd: Any) -> bool:
        """Execute create port behavior for material graph workflows."""

        if not self._usdshade_port:
            namespace_prefix = (
                prefix if prefix.endswith(Sdf.Path.namespaceDelimiter) else f"{prefix}{Sdf.Path.namespaceDelimiter}"
            )
            port_name = self._attribute_name.removeprefix(namespace_prefix)

            result = create_port_cmd(
                self.prim_path,
                port_name,
                self.type,
                variability=self._proxy_attribute.variability,
                stage=self.prim.GetStage(),
            )
            if isinstance(result, CommandResult):
                result = result.payload if result.success else None
            if result and not isinstance(result, self._port_cls):
                result = self._port_cls(result)
            self._usdshade_port = result

        if not self._usdshade_port:
            attribute = self.stage.GetAttributeAtPath(self.path) if self.stage else None
            if attribute:
                self._usdshade_port = self._port_cls(attribute)
        return bool(self._usdshade_port)

    def get_inputs(self) -> Optional[List[Any]]:
        """Execute get inputs behavior for material graph workflows."""

        return None

    def get_outputs(self) -> Optional[List[Any]]:
        """Execute get outputs behavior for material graph workflows."""

        return None

    @property
    def inputs(self, item: Optional[Any] = None) -> Optional[List[Any]]:
        """Execute inputs behavior for material graph workflows."""

        if item:
            return item.inputs
        return self.get_inputs()

    @inputs.setter
    def inputs(self, value: Optional[Sequence[Any]], item: Optional[Any] = None) -> None:
        """Execute inputs behavior for material graph workflows."""

        self.set_inputs(value, item)

    def set_inputs(self, value: Optional[Sequence[Any]], item: Optional[Any] = None) -> bool:
        """Author input connections and preserve the structured success result."""

        if item:
            setter = getattr(item, "set_inputs", None)
            if callable(setter):
                return setter(value) is not False
            item.inputs = value
            return True
        return self._connections.set_inputs(value)

    @property
    def outputs(self, item: Optional[Any] = None) -> Optional[List[Any]]:
        """Execute outputs behavior for material graph workflows."""

        if item:
            return item.outputs
        return self.get_outputs()

    def sync(self, *args: Any, **kwargs: Any) -> None:
        """Execute sync behavior for material graph workflows."""

        self._connections.sync()

    @property
    def tooltip_text(self, item: Optional[Any] = None) -> str:
        """Execute tooltip text behavior for material graph workflows."""

        import omni.UsdMdl

        if item:
            return item.tooltip_text

        if self._proxy_attribute.polymorphic_unresolved:
            text = self._attribute_name
            candidate_types = self._get_candidate_port_types()
            if candidate_types:
                unique = sorted(set(candidate_types))
                text += f"\n\nCandidate types:\n\t{', '.join(unique)}"
            documentation = self._proxy_attribute.documentation
            if documentation:
                text += f"\n\nDescription:\n\t{documentation}"
            return text

        text = self._attribute_name
        text += f"\n\t{Sdf.PrimSpec.TypeNameKey}: {self.type}"

        render_type = self._proxy_attribute.render_type
        if render_type:
            text += f"\n\t{Sdr.PropertyMetadata.RenderType}: {render_type} ({self._proxy_attribute.variability})"
            if render_type == omni.UsdMdl.Types.Struct:
                text += f"\n\t\t{omni.UsdMdl.Metadata.StructType}: {self._proxy_attribute.mdl_struct_type}"
                text += f"\n\t\t{omni.UsdMdl.Metadata.Symbol}: {self._proxy_attribute.mdl_symbol}"
            elif render_type == omni.UsdMdl.Types.Enum:
                text += f"\n\t\t{omni.UsdMdl.Metadata.Symbol}: {self._proxy_attribute.mdl_symbol}"
            elif render_type == omni.UsdMdl.Types.Array:
                text += f"\n\t\t{omni.UsdMdl.Metadata.ArrayElementType}: {self._proxy_attribute.mdl_array_element_type}"

        documentation = self._proxy_attribute.documentation
        if documentation:
            text += f"\n\nDescription:\n\t{documentation}"
        return text

    def get_connected_prims(self, recurse_nodegraphs: bool = True) -> List[Any]:
        """Execute get connected prims behavior for material graph workflows."""

        return self._connections.get_connected_prims(recurse_nodegraphs)

    def can_connect(self, target: Any) -> bool:
        """Execute can connect behavior for material graph workflows."""
        if not isinstance(target, AttributeModel):
            return False
        if is_force_connection_modifier_pressed():
            if self.validator.would_create_cycle(self, target):
                return False
            source_prim = self.prim
            target_prim = target.prim
            if (
                source_prim
                and target_prim
                and source_prim.IsValid()
                and target_prim.IsValid()
                and source_prim.GetPath() == target_prim.GetPath()
            ):
                return False
            return True
        return self.validator.can_connect(self.context_name, self._plugin, self, target)
