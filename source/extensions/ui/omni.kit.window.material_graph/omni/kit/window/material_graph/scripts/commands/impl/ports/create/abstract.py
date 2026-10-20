"""Base implementation for port-creation commands."""

from typing import Optional

import omni.kit.commands
from omni.kit.window.material_graph.scripts.commands.impl.nodegraph_api import ensure_nodegraph_node_api, prim_from_attr
from omni.kit.window.material_graph.scripts.config.logging import get_logger
from pxr import Sdf, Usd

from ...stage_helper import UsdStageHelper

logger = get_logger()


def _get_attr_path(attr: object) -> Optional[Sdf.Path]:
    """Return the attribute path when available."""
    if attr is None:
        return None
    if hasattr(attr, "GetPath"):
        return attr.GetPath()
    if isinstance(attr, Sdf.Path):
        return attr
    return None


def _command_created_attribute(command: object, _result: object) -> bool:
    """Return whether a port command successfully created its attribute."""
    return bool(command.__dict__.get("_created_attr"))


@ensure_nodegraph_node_api(prim_from_attr("_prim_path"), should_apply=_command_created_attribute)
class MaterialGraph_CreateAbstractPortCommand(omni.kit.commands.Command, UsdStageHelper):
    """Shared implementation for CreateInputPortCommand and CreateOutputPortCommand."""

    def __init__(
        self,
        prim_path: Sdf.Path,
        port_name: str,
        port_type: Sdf.ValueTypeName,
        stage: Optional[Usd.Stage] = None,
        variability: Sdf.Variability = Sdf.VariabilityVarying,
    ) -> None:
        """Store port-creation parameters and stage context for undoable execution."""
        UsdStageHelper.__init__(self, stage)
        self._prim_path = prim_path
        self._port_name = port_name
        self._port_type = port_type
        self._variability = variability if variability is not None else Sdf.VariabilityVarying
        self._created_attr = None
        self._port_prefix = ""
        self._failed = False

    def _get_port_name(self) -> str:
        """Return normalized port name including required input/output prefix."""
        if self._port_name.startswith(self._port_prefix):
            return self._port_name
        return f"{self._port_prefix}{self._port_name}"

    def do(self) -> Optional[object]:
        """Create the USD attribute for this port and cache it for undo."""
        if self._failed:
            return None
        if not isinstance(self._port_type, Sdf.ValueTypeName) or not self._port_type:
            logger.warning("create port skipped: invalid USD value type for %s", self._get_port_name())
            self._failed = True
            return None
        stage = self._get_stage()
        if not stage:
            self._failed = True
            return None
        prim = stage.GetPrimAtPath(self._prim_path)
        if not prim:
            self._failed = True
            return None
        port_name = self._get_port_name()
        if prim.HasAttribute(port_name):
            logger.warning("create port skipped: attribute already exists at %s.%s", self._prim_path, port_name)
            self._failed = True
            return None

        # This registered command owns the attribute lifecycle. Authoring
        # directly avoids a nested CreateUsdAttributeCommand that could remain
        # on the undo stack if later command validation failed.
        attr = prim.CreateAttribute(
            port_name,
            self._port_type,
            custom=False,
            variability=self._variability,
        )
        if attr and attr.IsValid():
            self._created_attr = attr
        else:
            self._failed = True

        return self._created_attr

    def undo(self) -> None:
        """Remove the created port attribute if it still exists on stage."""
        prop_path = _get_attr_path(self._created_attr)
        if prop_path is None:
            return
        stage = self._get_stage()
        prim = stage.GetPrimAtPath(prop_path.GetPrimPath()) if stage else None
        if prim and stage.GetPropertyAtPath(prop_path):
            if prim.RemoveProperty(prop_path.name) is False or stage.GetPropertyAtPath(prop_path):
                logger.warning("undo remove port property failed: %s", prop_path)
