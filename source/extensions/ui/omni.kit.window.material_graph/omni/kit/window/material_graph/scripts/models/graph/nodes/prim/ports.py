# pylint: disable=no-member
"""Implement material graph extension logic for `models/graph/nodes/prim/ports.py`."""

from typing import Any, List, Optional

from pxr import UsdShade


class PrimPortSync:
    """Synchronizes USD ports into proxy attributes."""

    def __init__(self, prim: Any, inputs_model: Any, outputs_model: Any, schema_collector: Any) -> None:
        """Initialize port-sync helper with prim, port-group models, and schema collector."""
        self._prim = prim
        self._inputs = inputs_model
        self._outputs = outputs_model
        self._schema_collector = schema_collector

    def clear(self) -> None:
        """Clear cached prim reference to prevent stale stage access after teardown."""
        self._prim = None

    def _get_connectable_api(self) -> Optional[Any]:
        """Return the connectable API for the prim."""
        if not self._prim:
            return None
        return UsdShade.ConnectableAPI(self._prim)

    def collect_inputs(self, proxy_attributes: List[Any]) -> None:
        """Collect input attributes into proxy list."""
        api = self._get_connectable_api()
        if not api:
            return
        for usdshade_input in api.GetInputs():
            self._schema_collector.add_or_update_proxy_attribute(
                False,
                usdshade_input.GetAttr(),
                proxy_attributes,
            )

    def collect_outputs(self, proxy_attributes: List[Any]) -> None:
        """Collect output attributes into proxy list."""
        api = self._get_connectable_api()
        if not api:
            return
        for usdshade_output in api.GetOutputs():
            self._schema_collector.add_or_update_proxy_attribute(
                True,
                usdshade_output.GetAttr(),
                proxy_attributes,
            )
