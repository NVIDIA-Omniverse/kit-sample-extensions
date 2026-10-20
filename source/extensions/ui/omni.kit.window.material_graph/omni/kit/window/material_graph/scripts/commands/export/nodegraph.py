"""NodeGraph export entrypoint that opens the standard export dialog."""

from omni.kit.widget.stage.export_utils import ExportPrimUSD
from pxr import Usd

from ...config.logging import logger
from .directory import resolve_export_directory
from .result import ExportResult


def export_nodegraph(prim: Usd.Prim) -> ExportResult:
    """Show the export UI and export a NodeGraph prim."""
    if not prim:
        logger.warning("export nodegraph failed: the selected prim is invalid or no longer exists; no file was written")
        return ExportResult(False, "invalid prim")
    directory_result = resolve_export_directory()
    if not directory_result.success:
        logger.warning("export nodegraph failed: %s", directory_result.message)
        return directory_result
    ExportPrimUSD(
        select_msg=f'Export NodeGraph "{prim.GetName()}" As...',
        save_msg="Export",
        save_dir=directory_result.target_path or "",
        postfix_name="NodeGraph",
    ).export([prim])
    return ExportResult(
        True,
        "export dialog opened",
        source_path=str(prim.GetPath()),
        target_path=directory_result.target_path,
    )
