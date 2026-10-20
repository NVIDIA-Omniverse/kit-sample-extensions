"""Export-directory resolution utility with token expansion and validation."""

from pathlib import Path

import carb.settings

from ...config.logging import logger
from ...settings import utils
from .result import ExportResult


def resolve_export_directory() -> ExportResult:
    """Return the compound directory for exports."""
    settings = carb.settings.get_settings()
    directory = settings.get(utils.COMPOUND_DEFAULT_EXPORT_PATH)

    if isinstance(directory, str) and "${" in directory:
        resolved = utils.tokens.resolve(directory)
        if resolved:
            directory = resolved
            settings.set_string(utils.COMPOUND_DEFAULT_EXPORT_PATH, directory)
        else:
            message = "export directory token could not be resolved"
            logger.warning("%s: token=%s", message, directory)
            return ExportResult(False, message, target_path=directory)
    if not directory:
        directory = utils.COMPOUND_DEFAULT_PATH
        if directory:
            settings.set_string(utils.COMPOUND_DEFAULT_EXPORT_PATH, directory)
        else:
            message = "export directory token could not be resolved"
            logger.warning("%s: token=%s", message, directory)
            return ExportResult(False, message)
    if not isinstance(directory, str):
        message = "export directory setting must be a string"
        logger.warning("%s: value=%r", message, directory)
        return ExportResult(False, message)
    if len(directory) > 1 and directory[1] == ":":
        directory = directory[:1].upper() + directory[1:]
    if "://" in directory:
        return ExportResult(True, "resolved", target_path=directory)
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
    except (OSError, TypeError, ValueError) as exc:
        message = f"failed to create export directory '{directory}': {exc}"
        logger.warning(
            "compound export directory setup failed path='%s' setting='%s': %s; no compound was exported",
            directory,
            utils.COMPOUND_DEFAULT_EXPORT_PATH,
            exc,
        )
        return ExportResult(False, message, target_path=directory)
    return ExportResult(True, "resolved", target_path=directory)
