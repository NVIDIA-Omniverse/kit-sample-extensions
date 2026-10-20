"""Low-level USD prim export routine used by material graph export commands."""

import omni.kit.app
from omni.kit.helper.file_utils import FILE_SAVED_GLOBAL_EVENT, FileEventModel
from pxr import Sdf, Tf, Usd, UsdUI

from ...config.logging import logger
from .result import ExportResult


def export(path: str, prim: Usd.Prim) -> ExportResult:
    """Export prim to external USD file."""
    if not prim:
        logger.warning("export failed: invalid prim target=%s", path)
        return ExportResult(False, "invalid prim", target_path=path)
    stage = prim.GetStage()
    if not stage:
        prim_path = prim.GetPath() if prim else None
        logger.warning("export failed: missing stage prim=%s target=%s", prim_path, path)
        return ExportResult(False, "missing stage", source_path=str(prim_path), target_path=path)
    source_path = prim.GetPath()
    source_path_str = str(source_path) if source_path else "<unknown>"
    try:
        source_layer = stage.Flatten()
    except (RuntimeError, ValueError, TypeError, AttributeError, Tf.ErrorException) as exc:
        logger.warning("export failed: prim=%s target=%s error=%s", source_path_str, path, exc)
        return ExportResult(False, "flatten failed", source_path=source_path_str, target_path=path)
    try:
        target_layer = Sdf.Layer.CreateNew(path)
    except (RuntimeError, ValueError, OSError, AttributeError, Tf.ErrorException) as exc:
        logger.warning(
            "export failed: prim=%s target=%s error=could not create layer (%s)",
            source_path_str,
            path,
            exc,
        )
        return ExportResult(False, "create layer failed", source_path=source_path_str, target_path=path)
    if not target_layer:
        logger.warning("export failed: prim=%s target=%s error=empty layer", source_path_str, path)
        return ExportResult(False, "create layer failed", source_path=source_path_str, target_path=path)
    target_path = Sdf.Path.absoluteRootPath.AppendChild(source_path.name)

    try:
        copied = Sdf.CopySpec(source_layer, source_path, target_layer, target_path)
    except (RuntimeError, ValueError, TypeError, AttributeError, Tf.ErrorException) as exc:
        logger.warning(
            "export failed: prim=%s target=%s copy error=%s",
            source_path_str,
            path,
            exc,
        )
        return ExportResult(False, "copy spec failed", source_path=source_path_str, target_path=path)
    if not copied:
        logger.warning("export failed: prim=%s target=%s copy returned false", source_path_str, path)
        return ExportResult(False, "copy spec failed", source_path=source_path_str, target_path=path)

    target_layer.defaultPrim = target_path.name
    spec = target_layer.GetPrimAtPath(target_path)
    if not spec:
        logger.warning("export failed: prim=%s target=%s copied spec missing", source_path_str, path)
        return ExportResult(False, "copied spec missing", source_path=source_path_str, target_path=path)
    attributes = spec.attributes

    if UsdUI.Tokens.uiDisplayGroup not in attributes:
        attr = Sdf.AttributeSpec(spec, UsdUI.Tokens.uiDisplayGroup, Sdf.ValueTypeNames.Token)
        attr.default = "Material Graphs"

    if UsdUI.Tokens.uiDisplayName not in attributes:
        attr = Sdf.AttributeSpec(spec, UsdUI.Tokens.uiDisplayName, Sdf.ValueTypeNames.Token)
        attr.default = target_path.name

    if "ui:order" not in attributes:
        attr = Sdf.AttributeSpec(spec, "ui:order", Sdf.ValueTypeNames.Int)
        attr.default = 1024

    try:
        target_layer.Save()
    except (RuntimeError, ValueError, OSError, AttributeError, Tf.ErrorException) as exc:
        logger.warning(
            "export failed: prim=%s target=%s save error=%s",
            source_path_str,
            path,
            exc,
        )
        return ExportResult(False, "save failed", source_path=source_path_str, target_path=path)

    logger.info("export success: prim=%s target=%s", source_path_str, path)
    omni.kit.app.queue_event(FILE_SAVED_GLOBAL_EVENT, FileEventModel(url=path).dict())
    return ExportResult(True, "exported", source_path=source_path_str, target_path=path)
