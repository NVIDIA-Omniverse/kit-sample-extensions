"""Wrapper for context solo/unsolo command."""

from typing import List, Optional

from pxr import Sdf, Usd

from ...config.logging import logger
from ..execution import execute_command_checked
from ..result import CommandResult


def SoloContext(
    prim_path: Sdf.Path,
    output_names: List[str],
    stage: Optional[Usd.Stage] = None,
) -> CommandResult:
    """Disconnect the given Material output ports on the session layer."""
    if not prim_path or not output_names:
        return CommandResult(False, None, message="Missing prim path or output names", error_code="invalid_args")
    return execute_command_checked(
        "MaterialGraph_SoloContextCommand",
        prim_path=prim_path,
        output_names=output_names,
        solo=True,
        stage=stage,
        error_message="solo context failed",
    )


def UnsoloContext(
    prim_path: Sdf.Path,
    output_names: List[str],
    stage: Optional[Usd.Stage] = None,
) -> CommandResult:
    """Remove session layer disconnections for the given Material output ports."""
    if not prim_path or not output_names:
        return CommandResult(False, None, message="Missing prim path or output names", error_code="invalid_args")
    return execute_command_checked(
        "MaterialGraph_SoloContextCommand",
        prim_path=prim_path,
        output_names=output_names,
        solo=False,
        stage=stage,
        error_message="unsolo context failed",
    )
