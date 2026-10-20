"""Controller for context soloing — delegates to undoable solo/unsolo commands."""

from typing import List, Optional, Tuple

import carb.settings
import omni.kit.app
import omni.usd
from pxr import Sdf, Usd, UsdShade

from ....commands.wrappers.solo import SoloContext, UnsoloContext
from ....config.logging import logger

_MIN_KIT_MAJOR_FOR_FABRIC_SOLO = 111
_FABRIC_SETTING = "/app/useFabricSceneDelegate"


def is_solo_supported() -> Tuple[bool, str]:
    """Return (supported, reason) — False when Fabric is active on Kit < 111."""
    settings = carb.settings.get_settings()
    fabric_enabled = settings.get_as_bool(_FABRIC_SETTING) if settings else False
    if not fabric_enabled:
        return True, ""

    version_str = "unknown"
    try:
        version_str = omni.kit.app.get_app().get_kit_version_short()
        major = int(version_str.split(".")[0])
    except (ValueError, IndexError, AttributeError):
        major = 0

    if major < _MIN_KIT_MAJOR_FOR_FABRIC_SOLO:
        reason = (
            f"Context soloing is disabled because the Fabric scene delegate is enabled "
            f"and Kit {version_str} (< {_MIN_KIT_MAJOR_FOR_FABRIC_SOLO}.0)."
        )
        return False, reason
    return True, ""


class ContextSoloController:
    """Solo a render context by disconnecting other contexts' Material outputs on the session layer."""

    def __init__(self, widget: object, context_manager: object) -> None:
        self._widget = widget
        self._context_manager = context_manager
        self._soloed_context: Optional[str] = None
        self._disconnected_outputs: List[str] = []
        self._ignored_attr_paths: list = []

    @property
    def soloed_context(self) -> Optional[str]:
        return self._soloed_context

    def toggle_solo(self, context_name: str) -> None:
        supported, reason = is_solo_supported()
        if not supported:
            logger.warning("context solo unavailable: %s", reason)
            return
        if self._soloed_context == context_name:
            self._unsolo()
        else:
            self._solo(context_name)
        if self._widget:
            self._widget.rebuild_graph_toolbar()

    def clear(self) -> None:
        if self._soloed_context:
            self._unsolo()
            if self._widget:
                self._widget.rebuild_graph_toolbar()

    def _solo(self, context_name: str) -> None:
        if self._soloed_context and not self._unsolo():
            return

        material_prim = self._get_material_prim()
        if not material_prim:
            model_path = getattr(getattr(self._widget, "model", None), "prim_path", None) if self._widget else None
            logger.warning(
                "context solo '%s' was not applied: no valid material prim is loaded (model_path=%s)",
                context_name,
                model_path or "<none>",
            )
            return

        non_soloed = self._get_non_soloed_output_names(context_name)
        prim_path = material_prim.GetPath()
        material = UsdShade.Material(material_prim)

        all_output_names = non_soloed + self._get_soloed_output_names(context_name)
        all_attr_paths: List[Sdf.Path] = []
        for output_name in all_output_names:
            output = material.GetOutput(output_name)
            if output:
                all_attr_paths.append(output.GetAttr().GetPath())

        if self._widget and all_attr_paths:
            self._widget.ignore_stage_listener_paths(all_attr_paths)

        result = SoloContext(prim_path, non_soloed, stage=material_prim.GetStage())
        if not result.success:
            logger.warning(
                "context solo '%s' failed for material '%s' outputs=%s: %s; connections were not changed",
                context_name,
                prim_path,
                non_soloed,
                getattr(result, "error_code", None) or getattr(result, "message", None) or "command returned no reason",
            )
            if self._widget and all_attr_paths:
                self._widget.unignore_stage_listener_paths(all_attr_paths)
            return

        self._soloed_context = context_name
        self._disconnected_outputs = list(non_soloed)
        self._ignored_attr_paths = all_attr_paths
        logger.info("Context solo: soloed '%s', disconnected %d outputs", context_name, len(self._disconnected_outputs))

    def _unsolo(self) -> bool:
        if self._widget and self._ignored_attr_paths:
            self._widget.unignore_stage_listener_paths(self._ignored_attr_paths)

        material_prim = self._get_material_prim()
        if not material_prim or not self._disconnected_outputs:
            self._soloed_context = None
            self._disconnected_outputs = []
            self._ignored_attr_paths = []
            return True

        prim_path = material_prim.GetPath()
        result = UnsoloContext(prim_path, list(self._disconnected_outputs), stage=material_prim.GetStage())
        if not result.success:
            logger.warning(
                "context unsolo '%s' failed for material '%s' outputs=%s: %s; solo state remains active",
                self._soloed_context,
                prim_path,
                self._disconnected_outputs,
                getattr(result, "error_code", None) or getattr(result, "message", None) or "command returned no reason",
            )
            return False

        prev = self._soloed_context
        self._soloed_context = None
        self._disconnected_outputs = []
        self._ignored_attr_paths = []
        logger.info("Context solo: unsoloed '%s'", prev)
        return True

    def _get_material_prim(self) -> Optional[Usd.Prim]:
        if not self._widget:
            return None
        model = self._widget.model
        if not model:
            return None
        prim = model.prim
        if prim and prim.IsValid():
            return prim
        return None

    def _get_non_soloed_output_names(self, soloed_context: str) -> List[str]:
        output_names = []
        for plugin in self._context_manager.get_plugins():
            if plugin.name == soloed_context:
                continue
            try:
                names = plugin.get_material_output_names()
                for name in names:
                    output_names.append(name.removeprefix(UsdShade.Tokens.outputs))
            except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
                logger.warning("Context solo: failed to get output names for '%s': %s", plugin.name, exc)
        return output_names

    def _get_soloed_output_names(self, soloed_context: str) -> List[str]:
        output_names = []
        for plugin in self._context_manager.get_plugins():
            if plugin.name != soloed_context:
                continue
            try:
                names = plugin.get_material_output_names()
                for name in names:
                    output_names.append(name.removeprefix(UsdShade.Tokens.outputs))
            except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
                logger.warning("Context solo: failed to get output names for '%s': %s", plugin.name, exc)
        return output_names

    def destroy(self) -> None:
        self.clear()
        self._widget = None
        self._context_manager = None
