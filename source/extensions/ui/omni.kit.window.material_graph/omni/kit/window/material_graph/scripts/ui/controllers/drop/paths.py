"""Implement material graph extension logic for `ui/controllers/drop/paths.py`."""

from typing import Any, Optional

from pxr import Sdf, UsdShade

# pylint: disable=no-member


class PathDropHandler:
    """Handle drops that are USD prim paths."""

    def __init__(self, widget: Any, usd_context: Any) -> None:
        """Initialize path drop handling."""
        self._widget = widget
        self._usd_context = usd_context

    def can_accept(self, drop_data: str) -> bool:
        """Return True if the path resolves to a bound material."""
        if not Sdf.Path.IsValidPathString(drop_data):
            return False
        return bool(self._get_bound_material(drop_data))

    def handle_drop(self, drop_data: str) -> bool:
        """Handle a path drop and return True if consumed."""
        if not Sdf.Path.IsValidPathString(drop_data):
            return False
        material = self._get_bound_material(drop_data)
        if material and material.IsA(UsdShade.Material):
            self._widget.edit_graph(material)
            return True
        return False

    def _get_bound_material(self, drop_data: str) -> Optional[UsdShade.Material]:
        """Return a bound material for a prim path."""
        path = Sdf.Path(drop_data)
        stage = self._usd_context.get_stage() if self._usd_context else None
        if not stage:
            return None

        prim = stage.GetPrimAtPath(path)
        if not prim:
            return None

        if prim == self._widget.prim:
            return None

        if prim.IsA(UsdShade.Material):
            return prim

        api = UsdShade.MaterialBindingAPI(prim)
        if not api:
            return None

        material, _ = api.ComputeBoundMaterial()
        if not material:
            return None

        material_prim = material.GetPrim()
        if material_prim == self._widget.prim:
            return None

        return material_prim

    def destroy(self) -> None:
        """Release drop-handler references and callbacks to avoid retaining stale UI state."""
        self._widget = None
        self._usd_context = None
