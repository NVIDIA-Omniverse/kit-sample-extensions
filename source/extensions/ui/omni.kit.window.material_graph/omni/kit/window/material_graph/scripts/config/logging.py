"""Logging configuration and helpers for the extension."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

LOG_CHANNEL = "omni.kit.window.material_graph"

logger = logging.getLogger(LOG_CHANNEL)


@dataclass(frozen=True)
class LogContext:
    """Context fields for consistent structured logging."""

    context_name: Optional[str] = None
    plugin_name: Optional[str] = None
    prim_path: Optional[str] = None
    command_name: Optional[str] = None
    action: Optional[str] = None
    file_path: Optional[str] = None
    ext_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Return non-empty fields as a dictionary."""
        data = {
            "context_name": self.context_name,
            "plugin_name": self.plugin_name,
            "prim_path": self.prim_path,
            "command_name": self.command_name,
            "action": self.action,
            "file_path": self.file_path,
            "ext_id": self.ext_id,
        }
        return {key: value for key, value in data.items() if value not in (None, "")}


def get_logger() -> logging.Logger:
    """Return the extension root logger."""
    # keep as wrapper in order to make it easier to modify in the future.
    return logger


def merge_log_context(base: Optional[LogContext] = None, **kwargs: Any) -> LogContext:
    """Merge ad-hoc context fields with a base context."""
    current = base.to_dict() if base else {}
    current.update({key: value for key, value in kwargs.items() if value not in (None, "")})
    return LogContext(
        context_name=current.get("context_name"),
        plugin_name=current.get("plugin_name"),
        prim_path=current.get("prim_path"),
        command_name=current.get("command_name"),
        action=current.get("action"),
        file_path=current.get("file_path"),
        ext_id=current.get("ext_id"),
    )


def context_suffix(context: Optional[LogContext] = None, **kwargs: Any) -> str:
    """Return a canonical context suffix for message formatting."""
    merged = merge_log_context(context, **kwargs)
    data = merged.to_dict()
    if not data:
        return ""
    parts = [f"{key}={value}" for key, value in data.items()]
    return " [" + ", ".join(parts) + "]"


def log_exception(
    log: logging.Logger,
    message: str,
    *,
    context: Optional[LogContext] = None,
    level: int = logging.ERROR,
    exc: Optional[BaseException] = None,
    **kwargs: Any,
) -> None:
    """Log an exception with consistent context and stack traces."""
    suffix = context_suffix(context, **kwargs)
    if exc is None:
        log.log(level, "%s%s", message, suffix, exc_info=True)
    else:
        exc_info = (type(exc), exc, exc.__traceback__)
        log.log(level, "%s%s (%s)", message, suffix, exc, exc_info=exc_info)
