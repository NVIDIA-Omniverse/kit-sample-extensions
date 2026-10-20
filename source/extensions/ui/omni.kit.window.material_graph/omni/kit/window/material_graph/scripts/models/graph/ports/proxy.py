"""Proxy attribute wrapper exposing normalized SDR/USD metadata for graph ports."""

__all__ = ["ProxyAttribute"]

import pickle
from typing import Any, Optional

import omni.UsdMdl
from pxr import Sdf, Sdr, Usd, UsdShade

from ....utils.sdr_wrappers import resolve_property_type_name


class ProxyAttribute:
    """Metadata wrapper for shader attribute definitions."""

    def __init__(
        self,
        name: str,
        is_output: bool,
        sdr_shader_property: Optional[Sdr.ShaderProperty] = None,
        attribute: Optional[Usd.Attribute] = None,
        attribute_definition: Optional[Any] = None,
    ) -> None:
        """Initialize proxy metadata by merging SDR, USD attribute, and definition hints."""
        self.name = name
        self._is_output = is_output
        self._metadata = {}

        if sdr_shader_property:
            self._metadata = sdr_shader_property.GetMetadata()
            self._metadata[Sdf.AttributeSpec.DisplayNameKey] = sdr_shader_property.GetLabel()
            self._metadata[Sdf.AttributeSpec.DisplayGroupKey] = sdr_shader_property.GetPage()
            self._metadata[Sdf.PrimSpec.TypeNameKey] = resolve_property_type_name(sdr_shader_property)
            self._metadata["documentation"] = sdr_shader_property.GetHelp()
            modifier = self._metadata.get(omni.UsdMdl.Metadata.Modifier, omni.UsdMdl.TypeModifiers.Varying)
            variability = (
                Sdf.VariabilityVarying if modifier == omni.UsdMdl.TypeModifiers.Varying else Sdf.VariabilityUniform
            )
            self._metadata["variability"] = self._serialize_variability(variability)
            hints = sdr_shader_property.GetHints()
            self._metadata["hidden"] = isinstance(hints, dict) and any(k in hints for k in ("hidden", "unused"))

        if attribute:
            self._metadata.update(attribute.GetAllMetadata())
            owner_prim = attribute.GetPrim()
            self._metadata["owner_is_interface"] = bool(
                owner_prim
                and owner_prim.IsValid()
                and (owner_prim.IsA(UsdShade.NodeGraph) or owner_prim.IsA(UsdShade.Material))
            )

        if attribute_definition:
            self._metadata.update(
                {
                    field_name: attribute_definition.GetMetadata(field_name)
                    for field_name in attribute_definition.ListMetadataFields()
                }
            )

        self._normalize_metadata_values()

    @staticmethod
    def _serialize_variability(value: Any) -> str:
        """Return a pickle-safe variability token."""
        text = str(value).lower().replace("sdf.", "").replace("sdf", "").replace("variability", "")
        text = text.replace("_", "").replace("-", "").replace(" ", "").replace(".", "")
        if value == Sdf.VariabilityUniform or text == "uniform":
            return "uniform"
        return "varying"

    @classmethod
    def _deserialize_variability(cls, value: Any) -> Sdf.Variability:
        """Return a USD variability value from stored metadata."""
        if value in (Sdf.VariabilityUniform, Sdf.VariabilityVarying):
            return value
        return Sdf.VariabilityUniform if cls._serialize_variability(value) == "uniform" else Sdf.VariabilityVarying

    def _normalize_variability_metadata(self) -> None:
        """Store variability metadata without raw pxr enum objects."""
        if "variability" in self._metadata:
            self._metadata["variability"] = self._serialize_variability(self._metadata["variability"])

    @classmethod
    def _make_pickle_safe_metadata_value(cls, value: Any) -> Any:
        """Return metadata value safe for graph-model caching/copying."""
        if isinstance(value, (type(None), bool, int, float, str)):
            return value
        if isinstance(value, (bytes, bytearray)):
            return bytes(value).decode("utf-8", errors="replace")
        if isinstance(value, dict):
            return {str(key): cls._make_pickle_safe_metadata_value(val) for key, val in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls._make_pickle_safe_metadata_value(item) for item in value]
        value_type = type(value)
        if value_type.__module__.startswith("pxr."):
            if value_type.__module__ == "pxr.Vt" and value_type.__name__.endswith("Array"):
                try:
                    return [cls._make_pickle_safe_metadata_value(item) for item in value]
                except (TypeError, RuntimeError, ValueError, AttributeError):
                    pass
            return str(value)
        try:
            pickle.dumps(value)
            return value
        except (pickle.PickleError, TypeError, RuntimeError, ValueError, AttributeError):
            pass
        try:
            return [cls._make_pickle_safe_metadata_value(item) for item in value]
        except (TypeError, RuntimeError, ValueError, AttributeError):
            return str(value)

    def _normalize_metadata_values(self) -> None:
        """Normalize USD metadata to Python values that can be copied safely.

        Always rebuilds the ``Inputs:``/``Outputs:`` display-group prefix so a
        subsequent USD-metadata merge in ``update()`` cannot leave a bare
        authored value that ``filter_proxy_attributes`` would later drop.
        """
        self._metadata = {
            str(key): self._make_pickle_safe_metadata_value(value) for key, value in self._metadata.items()
        }
        self._normalize_variability_metadata()
        self._build_display_group()

    def _build_display_group(self) -> None:
        """Normalize display group metadata for inputs/outputs."""
        value = str(self._metadata.get(Sdf.AttributeSpec.DisplayGroupKey, "") or "")
        if not value:
            value = "Outputs" if self._is_output else "Inputs"
        elif self._is_output:
            if not value.startswith("Outputs"):
                value = f"Outputs:{value}"
        elif not value.startswith("Inputs"):
            value = f"Inputs:{value}"
        self._metadata[Sdf.AttributeSpec.DisplayGroupKey] = value

    @property
    def display_name(self, item: Optional[Any] = None) -> str:
        """Execute display name behavior for material graph workflows."""

        return item.display_name if item else self._metadata.get(Sdf.AttributeSpec.DisplayNameKey, "")

    @display_name.setter
    def display_name(self, value: str) -> None:
        """Execute display name behavior for material graph workflows."""

        self._metadata[Sdf.AttributeSpec.DisplayNameKey] = value

    @property
    def display_group(self, item: Optional[Any] = None) -> str:
        """Execute display group behavior for material graph workflows."""

        return item.display_group if item else self._metadata.get(Sdf.AttributeSpec.DisplayGroupKey, "")

    @display_group.setter
    def display_group(self, value: str) -> None:
        """Execute display group behavior for material graph workflows."""

        self._metadata[Sdf.AttributeSpec.DisplayGroupKey] = value

    @property
    def type_name(self, item: Optional[Any] = None) -> Optional[Any]:
        """Execute type name behavior for material graph workflows."""

        return item.type_name if item else self._metadata.get(Sdf.PrimSpec.TypeNameKey, None)

    @type_name.setter
    def type_name(self, value: Any) -> None:
        """Execute type name behavior for material graph workflows."""

        self._metadata[Sdf.PrimSpec.TypeNameKey] = value

    @property
    def render_type(self, item: Optional[Any] = None) -> Optional[Any]:
        """Execute render type behavior for material graph workflows."""

        return item.render_type if item else self._metadata.get(Sdr.PropertyMetadata.RenderType, None)

    @render_type.setter
    def render_type(self, value: Any) -> None:
        """Execute render type behavior for material graph workflows."""

        self._metadata[Sdr.PropertyMetadata.RenderType] = value

    @property
    def hidden(self, item: Optional[Any] = None) -> bool:
        """Execute hidden behavior for material graph workflows."""

        return item.hidden if item else self._metadata.get("hidden", False)

    @property
    def connectability(self, item: Optional[Any] = None) -> Any:
        """Execute connectability behavior for material graph workflows."""

        return item.connectability if item else self._metadata.get("connectability", UsdShade.Tokens.full)

    @property
    def owner_is_interface(self) -> bool:
        """Return whether the authored port belongs to a material/nodegraph interface."""
        return bool(self._metadata.get("owner_is_interface", False))

    @property
    def documentation(self, item: Optional[Any] = None) -> str:
        """Execute documentation behavior for material graph workflows."""

        return item.documentation if item else self._metadata.get("documentation", "")

    @property
    def variability(self, item: Optional[Any] = None) -> Sdf.Variability:
        """Execute variability behavior for material graph workflows."""

        if item:
            return item.variability
        return self._deserialize_variability(self._metadata.get("variability", Sdf.VariabilityVarying))

    @property
    def mdl_struct_type(self, item: Optional[Any] = None) -> Optional[Any]:
        """Execute mdl struct type behavior for material graph workflows."""

        return item.mdl_struct_type if item else self._metadata.get(omni.UsdMdl.Metadata.StructType, None)

    @mdl_struct_type.setter
    def mdl_struct_type(self, value: Any) -> None:
        """Execute mdl struct type behavior for material graph workflows."""

        self._metadata[omni.UsdMdl.Metadata.StructType] = value

    @property
    def mdl_symbol(self, item: Optional[Any] = None) -> Optional[Any]:
        """Execute mdl symbol behavior for material graph workflows."""

        return item.mdl_symbol if item else self._metadata.get(omni.UsdMdl.Metadata.Symbol, None)

    @mdl_symbol.setter
    def mdl_symbol(self, value: Any) -> None:
        """Execute mdl symbol behavior for material graph workflows."""

        self._metadata[omni.UsdMdl.Metadata.Symbol] = value

    @property
    def mdl_array_element_type(self, item: Optional[Any] = None) -> Optional[Any]:
        """Execute mdl array element type behavior for material graph workflows."""

        return item.mdl_array_element_type if item else self._metadata.get(omni.UsdMdl.Metadata.ArrayElementType, None)

    @property
    def polymorphic_unresolved(self, item: Optional[Any] = None) -> bool:
        """Execute polymorphic unresolved behavior for material graph workflows."""

        return bool(item.polymorphic_unresolved) if item else bool(self._metadata.get("polymorphic_unresolved", False))

    @polymorphic_unresolved.setter
    def polymorphic_unresolved(self, value: bool) -> None:
        """Execute polymorphic unresolved behavior for material graph workflows."""

        self._metadata["polymorphic_unresolved"] = bool(value)

    def update(self, other: Any, prefer_existing: bool = False) -> None:
        """Merge metadata from another proxy attribute or USD attribute."""
        if isinstance(other, ProxyAttribute):
            incoming = other._metadata
        elif isinstance(other, Usd.Attribute):
            incoming = other.GetAllMetadata()
        else:
            return
        for key, value in incoming.items():
            if prefer_existing and key in self._metadata:
                continue
            self._metadata[key] = value
        self._normalize_metadata_values()
