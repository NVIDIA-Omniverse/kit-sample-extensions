"""Type-resolution helpers for SDR shader properties."""

import re
from typing import Any, Iterable, Optional

import omni.UsdMdl
from pxr import Sdf, Sdr


def resolve_property_type_name(sdr_shader_property: Sdr.ShaderProperty) -> str:
    """Return a stable type name for an SDR property."""
    type_indicator = sdr_shader_property.GetTypeAsSdfType()

    if hasattr(type_indicator, "GetNdrType"):
        type_name = type_indicator.GetNdrType() or type_indicator.GetSdfType()
    else:
        type_name = type_indicator.GetSdfType() if type_indicator.HasSdfType() else type_indicator.GetSdrType()

    return str(type_name)


def resolve_sdf_value_type_name(type_name: Any) -> Sdf.ValueTypeName:
    """Return a valid USD authoring type for an SDR semantic type.

    SDR preserves renderer-specific semantic types such as ``EDF``, ``VDF``,
    ``surfaceshader``, and user-defined structures. Those names are useful for
    compatibility checks, but they are not registered Sdf value types and must
    not be passed to USD attribute creation. USD shading networks represent
    these terminal-like values as token attributes.
    """
    if isinstance(type_name, Sdf.ValueTypeName):
        return type_name if type_name else Sdf.ValueTypeNames.Token
    resolved = Sdf.ValueTypeNames.Find(str(type_name)) if type_name is not None else None
    return resolved if resolved else Sdf.ValueTypeNames.Token


def resolve_property_display_type_name(sdr_shader_property: Sdr.ShaderProperty) -> str:
    """Return a user-facing type name for an SDR property."""
    type_name = resolve_property_type_name(sdr_shader_property)
    fallback_types = {"token", "user", "struct"}
    type_indicator = sdr_shader_property.GetTypeAsSdfType()
    get_sdr_type = getattr(type_indicator, "GetSdrType", None)
    if type_name in fallback_types and callable(get_sdr_type):
        sdr_type = get_sdr_type()
        if sdr_type and str(sdr_type) not in fallback_types:
            return str(sdr_type)
    try:
        metadata = sdr_shader_property.GetMetadata() or {}
    except (RuntimeError, ValueError, TypeError, AttributeError):
        metadata = {}
    render_type = metadata.get(Sdr.PropertyMetadata.RenderType)
    struct_type = metadata.get(omni.UsdMdl.Metadata.StructType) or metadata.get(omni.UsdMdl.Metadata.Symbol)
    if struct_type and (render_type == omni.UsdMdl.Types.Struct or type_name in fallback_types):
        return str(struct_type)
    if type_name in fallback_types:
        for key, value in metadata.items():
            if not isinstance(value, str):
                continue
            key_text = str(key).lower()
            if any(token in key_text for token in ("struct", "symbol", "type")) and value.startswith("::"):
                return value
    return type_name


def parse_mdl_subidentifier_argument_types(subidentifier: str) -> list[str]:
    """Return top-level argument type strings from an MDL function subidentifier."""
    if not isinstance(subidentifier, str):
        raise TypeError("MDL subidentifier must be a string")
    if not subidentifier:
        raise ValueError("MDL subidentifier cannot be empty")
    start = subidentifier.find("(")
    end = subidentifier.rfind(")")
    if start < 0 or end <= start:
        raise ValueError(f"Malformed MDL subidentifier: {subidentifier}")
    if end != len(subidentifier) - 1:
        raise ValueError(f"Malformed MDL subidentifier: {subidentifier}")
    signature = subidentifier[start + 1 : end].strip()
    if not signature:
        return []
    depth = 0
    current = []
    args = []
    for char in signature:
        if char in "(<[":
            depth += 1
        elif char in ")>]":
            depth = max(0, depth - 1)
        if char == "," and depth == 0:
            arg = "".join(current).strip()
            if not arg:
                raise ValueError(f"Malformed MDL subidentifier arguments: {subidentifier}")
            args.append(arg)
            current = []
            continue
        current.append(char)
    if depth != 0:
        raise ValueError(f"Malformed MDL subidentifier arguments: {subidentifier}")
    arg = "".join(current).strip()
    if not arg:
        raise ValueError(f"Malformed MDL subidentifier arguments: {subidentifier}")
    args.append(arg)
    return args


def mdl_polymorphic_family_key(sdr_node: Any, subidentifier: str) -> str:
    """Return the catalog/runtime family key for an MDL overload.

    Constructor overloads with one argument form the editor's polymorphic
    conversion nodes (for example ``Float3``), while multi-argument
    constructors remain distinct catalog nodes (for example ``Float3 from
    floats``). Other MDL overloads are grouped by their display label.
    """
    if not isinstance(subidentifier, str) or not subidentifier:
        return ""
    base_name = subidentifier.split("(", 1)[0].strip()
    if not base_name:
        return ""
    label = ""
    get_label = getattr(sdr_node, "GetLabel", None)
    if callable(get_label):
        try:
            label = str(get_label() or "").strip()
        except (RuntimeError, ValueError, TypeError, AttributeError):
            label = ""

    local_base_name = base_name.rsplit("::", 1)[-1]
    if local_base_name.startswith("construct_"):
        try:
            arity = len(parse_mdl_subidentifier_argument_types(subidentifier))
        except (TypeError, ValueError):
            arity = None
        if arity == 1:
            type_name = local_base_name.removeprefix("construct_")
            return (type_name[0].upper() + type_name[1:]) if type_name else (label or base_name)

    return label or base_name


def resolve_output_value_type(sdr_shader_property: Sdr.ShaderProperty) -> Sdf.ValueTypeName:
    """Resolve output value type with compatibility fallbacks."""
    return resolve_sdf_value_type_name(resolve_property_type_name(sdr_shader_property))


def mdl_types_match(actual_type: str, expected_type: str) -> bool:
    """Return whether two MDL-compatible type identifiers are compatible.

    Args:
        actual_type: The type reported by the SDR property. This may be an MDL
            type string, a USD/SDF type string, or a type object with a stable
            string representation.
        expected_type: The required type to compare against, using the same
            accepted forms as ``actual_type``.

    Returns:
        True when ``actual_type`` is compatible with ``expected_type`` after
        normalizing known MDL/USD aliases; False otherwise.
    """
    if actual_type == expected_type:
        return True
    actual = _normalize_mdl_type_name(actual_type)
    expected = _normalize_mdl_type_name(expected_type)
    aliases = {
        "color": "color",
        "color3f": "color",
        "float3": "vector3f",
        "vector3f": "vector3f",
    }
    return aliases.get(actual, actual) == aliases.get(expected, expected)


def _normalize_mdl_type_name(type_name: Any) -> str:
    """Normalize common qualified MDL type spellings for compatibility checks."""
    raw = str(type_name).strip().lower()
    normalized = raw.lstrip(":")
    if "::" in normalized:
        local_name = normalized.rsplit("::", 1)[-1]
        if normalized.startswith("base::"):
            return local_name
    return normalized


_MDL_VECTOR_TYPE_RE = re.compile(r"^(bool|int|float)([234])?$")
_MDL_NUMERIC_RANK = {"bool": 0, "int": 1, "float": 2}


def _normalize_mdl_value_type(type_name: Any) -> Optional[tuple[str, int]]:
    """Return a compact MDL builtin type key for compatibility checks."""
    if type_name is None:
        return None
    normalized = _normalize_mdl_type_name(type_name)
    if normalized == "boolean":
        normalized = "bool"
    if normalized in ("color", "color3f"):
        return ("color", 3)
    match = _MDL_VECTOR_TYPE_RE.match(normalized)
    if not match:
        return None
    component_type, component_count = match.groups()
    return (component_type, int(component_count or "1"))


def mdl_value_type_conversion_score(source_type: Any, target_type: Any) -> Optional[int]:
    """Return an MDL builtin conversion score, or ``None`` when incompatible.

    A score of zero is an exact normalized match. Positive scores represent
    backend-supported implicit conversions, with lower values preferred when
    resolving overloads.
    """
    if mdl_types_match(source_type, target_type):
        return 0

    source = _normalize_mdl_value_type(source_type)
    target = _normalize_mdl_value_type(target_type)
    if source is None or target is None:
        return None
    if source == target:
        return 0

    source_base, source_components = source
    target_base, target_components = target

    if source_base == "color":
        return 1 if target == ("float", 3) or target == ("float", 1) else None
    if target_base == "color":
        return 1 if source == ("float", 3) or source == ("float", 1) else None
    if source_base == "float" and source_components == 1 and target_base == "float" and target_components > 1:
        return 1
    if source_components == target_components == 1:
        source_rank = _MDL_NUMERIC_RANK.get(source_base)
        target_rank = _MDL_NUMERIC_RANK.get(target_base)
        if source_rank is not None and target_rank is not None and source_rank < target_rank:
            return target_rank - source_rank
    return None


def mdl_value_types_are_compatible(source_type: Any, target_type: Any) -> bool:
    """Return whether MDL can connect ``source_type`` to ``target_type``."""
    return mdl_value_type_conversion_score(source_type, target_type) is not None


def mdl_property_matches_polymorphic_constraint(
    sdr_shader_property: Sdr.ShaderProperty, expected_type: Any, is_input: bool
) -> bool:
    """Return whether an SDR property satisfies a polymorphic port constraint.

    Args:
        sdr_shader_property: The ``Sdr.ShaderProperty`` to validate.
        expected_type: The required type for the port, as an MDL type string,
            USD/SDF type string, or type object with a stable string
            representation.
        is_input: True when validating an input port; False when validating an
            output port. Input constraints apply MDL overload-selection
            normalization before comparison.

    Returns:
        True when the property's resolved type and direction satisfy the
        constraint; False when the property is missing or its type is
        incompatible.
    """
    if not sdr_shader_property:
        return False
    return mdl_type_matches_polymorphic_constraint(
        resolve_property_type_name(sdr_shader_property),
        expected_type,
        is_input,
    )


def mdl_type_matches_polymorphic_constraint(actual_type: Any, expected_type: Any, is_input: bool) -> bool:
    """Return whether a concrete type satisfies a polymorphic port constraint."""
    return mdl_type_polymorphic_constraint_score(actual_type, expected_type, is_input) is not None


def mdl_type_polymorphic_constraint_score(actual_type: Any, expected_type: Any, is_input: bool) -> Optional[int]:
    """Return overload match score; lower is more exact, None means incompatible."""
    if mdl_types_match(actual_type, expected_type):
        return 0
    if is_input:
        return mdl_value_type_conversion_score(expected_type, actual_type)
    return mdl_value_type_conversion_score(actual_type, expected_type)


def compute_polymorphic_constraint_score(sdr_node: Any, constraints: Iterable[tuple[str, Any, bool]]) -> Optional[int]:
    """Return summed polymorphic constraint score for an SDR node, or None if incompatible."""
    total = 0
    for port_name, expected_type, is_input in constraints:
        prop = sdr_node.GetShaderInput(port_name) if is_input else sdr_node.GetShaderOutput(port_name)
        if not prop:
            return None
        score = mdl_type_polymorphic_constraint_score(resolve_property_type_name(prop), expected_type, is_input)
        if score is None:
            return None
        total += score
    return total


def mdl_node_matches_polymorphic_constraints(sdr_node: Any, constraints: Iterable[tuple[str, Any, bool]]) -> bool:
    """Return whether an SDR node satisfies every polymorphic port constraint.

    Args:
        sdr_node: SDR shader node wrapper or compatible object exposing
            ``GetShaderInput`` and ``GetShaderOutput``.
        constraints: Iterable of ``(property_name, expected_type, is_input)``
            tuples. ``property_name`` is the port name, ``expected_type`` uses
            the forms accepted by ``mdl_types_match``, and ``is_input`` selects
            input versus output lookup.

    Returns:
        True only when every constraint resolves to an existing property whose
        type satisfies ``mdl_property_matches_polymorphic_constraint``. Missing
        properties and type mismatches return False.
    """
    return compute_polymorphic_constraint_score(sdr_node, constraints) is not None
