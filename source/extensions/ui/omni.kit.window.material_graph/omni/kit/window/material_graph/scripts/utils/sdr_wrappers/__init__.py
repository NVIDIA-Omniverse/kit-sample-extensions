"""Public SDR compatibility wrapper interfaces."""

from .registry import SdrRegistryWrapper
from .shader_node import SdrShaderNodeWrapper, wrap_shader_node, wrap_shader_nodes
from .type_utils import (
    compute_polymorphic_constraint_score,
    mdl_node_matches_polymorphic_constraints,
    mdl_polymorphic_family_key,
    mdl_property_matches_polymorphic_constraint,
    mdl_type_matches_polymorphic_constraint,
    mdl_type_polymorphic_constraint_score,
    mdl_types_match,
    mdl_value_type_conversion_score,
    mdl_value_types_are_compatible,
    parse_mdl_subidentifier_argument_types,
    resolve_output_value_type,
    resolve_property_display_type_name,
    resolve_property_type_name,
    resolve_sdf_value_type_name,
)

__all__ = [
    "SdrRegistryWrapper",
    "SdrShaderNodeWrapper",
    "compute_polymorphic_constraint_score",
    "mdl_node_matches_polymorphic_constraints",
    "mdl_polymorphic_family_key",
    "mdl_property_matches_polymorphic_constraint",
    "mdl_type_matches_polymorphic_constraint",
    "mdl_type_polymorphic_constraint_score",
    "mdl_types_match",
    "mdl_value_type_conversion_score",
    "mdl_value_types_are_compatible",
    "parse_mdl_subidentifier_argument_types",
    "resolve_output_value_type",
    "resolve_property_display_type_name",
    "resolve_property_type_name",
    "resolve_sdf_value_type_name",
    "wrap_shader_node",
    "wrap_shader_nodes",
]
