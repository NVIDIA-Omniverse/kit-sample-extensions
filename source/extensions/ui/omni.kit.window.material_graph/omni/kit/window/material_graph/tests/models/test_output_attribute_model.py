from types import SimpleNamespace
from unittest.mock import patch

from pxr import UsdShade

from ...scripts.config.paths import Paths
from ...scripts.models.graph.ports.attribute.output import OutputAttributeModel
from ..base import MaterialGraphTestBase


class _PrimStub:
    """Prim stub with configurable IsA behavior."""

    def __init__(self, is_material: bool) -> None:
        self._is_material = is_material

    def IsA(self, schema_type: object) -> bool:
        """Return material-schema match when configured."""
        return bool(self._is_material and schema_type == UsdShade.Material)


class TestOutputAttributeModel(MaterialGraphTestBase):
    """Tests for output-port rename rules."""

    async def test_set_name_blocks_reserved_material_outputs(self) -> None:
        """Reserved material outputs should not invoke base rename."""
        # Patch base set_name to verify that guarded ports skip rename execution.
        model = OutputAttributeModel.__new__(OutputAttributeModel)
        model._attribute_name = f"{UsdShade.Tokens.outputs}:{UsdShade.Tokens.surface}"
        model._parent = SimpleNamespace(prim=_PrimStub(is_material=True))
        with patch(
            f"{Paths.MODULE_ID}.scripts.models.graph.ports.attribute.output.AttributeModel.set_name",
            autospec=True,
        ) as base_set_name:
            self.assertFalse(model.set_name("renamed"))
        base_set_name.assert_not_called()

    async def test_set_name_allows_non_reserved_material_outputs(self) -> None:
        """Custom material outputs should rename via base output namespace path."""
        # Patch base set_name to assert namespaced forwarding for custom outputs.
        model = OutputAttributeModel.__new__(OutputAttributeModel)
        model._attribute_name = f"{UsdShade.Tokens.outputs}:customOut"
        model._parent = SimpleNamespace(prim=_PrimStub(is_material=True))
        with patch(
            f"{Paths.MODULE_ID}.scripts.models.graph.ports.attribute.output.AttributeModel.set_name",
            autospec=True,
            return_value=True,
        ) as base_set_name:
            self.assertTrue(model.set_name("renamed"))
        base_set_name.assert_called_once_with(model, f"{UsdShade.Tokens.outputs}renamed")
