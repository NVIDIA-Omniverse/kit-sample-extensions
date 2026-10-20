from pxr import UsdShade

from ...scripts.plugins.core.polymorphic_state import PolymorphicState


class DummyPlugin:
    """Minimal plugin stub for model tests."""

    def __init__(self) -> None:
        """Initialize the dummy plugin."""
        self.context_name = "universal"

    def get_material_output_names(self) -> list[str]:
        """Return default material output names."""
        return [f"{UsdShade.Tokens.outputs}{UsdShade.Tokens.surface}"]

    def is_supported_prim(self, prim) -> bool:
        """Return True if the prim is a shader."""
        return prim.IsA(UsdShade.Shader)

    def get_shader_node_for_prim(self, _prim) -> None:
        """Return None for shader node lookup."""
        return None

    def can_connect(self, _source_placeholder, _target_placeholder) -> bool:
        """Allow all connections in tests."""
        return True

    def can_connect_polymorphic_models(self, _target_model, _source_model) -> bool:
        """Default to non-polymorphic fallback for test stubs."""
        return False

    def get_polymorphic_state_for_prim(self, _prim) -> PolymorphicState:
        """Return concrete non-polymorphic state for test stubs."""
        return PolymorphicState()
