"""Command execution helpers that normalize command results and error handling."""

from typing import Callable, Iterable, Optional

import omni.kit.commands
import omni.kit.undo

from ..config.logging import LogContext, context_suffix, log_exception, logger
from .result import CommandResult

# pylint: disable=broad-exception-caught

ValidatorFn = Callable[[CommandResult], CommandResult]


def _format_value(value: object) -> str:
    """Return a safe string for logging."""
    if value is None:
        return "None"
    if isinstance(value, (str, int, float, bool)):
        return repr(value) if isinstance(value, str) else str(value)
    if isinstance(value, (list, tuple, set)):
        items = list(value)
        preview = ", ".join(_format_value(item) for item in items[:3])
        suffix = ", ..." if len(items) > 3 else ""
        return f"[{preview}{suffix}]"
    return str(value)


def format_command_args(*, keys: Optional[Iterable[str]] = None, **kwargs: object) -> str:
    """Format command kwargs for logging context."""
    if not kwargs:
        return ""
    default_keys = [
        "parent_path",
        "prim_path",
        "prim_paths",
        "attribute_path",
        "source_path",
        "target_path",
        "node_type",
        "identifier",
        "prim_name",
        "port_name",
        "source_asset",
        "context_name",
    ]
    keys_to_use = list(keys) if keys is not None else default_keys
    parts = []
    for key in keys_to_use:
        if key not in kwargs:
            continue
        value = kwargs.get(key)
        if value is None:
            continue
        parts.append(f"{key}={_format_value(value)}")
    if not parts:
        return ""
    return " [" + ", ".join(parts) + "]"


def execute_command(
    command_name: str,
    *,
    log_errors: bool = True,
    **kwargs: object,
) -> CommandResult:
    """Execute a command and normalize its return payload."""
    if not command_name:
        return CommandResult(
            False,
            None,
            message="Missing command name",
            error_code="invalid_command",
            command_name=command_name,
        )
    command_ctx = LogContext(command_name=command_name)
    try:
        result = omni.kit.commands.execute(command_name, **kwargs)
    except Exception as exc:
        # Intentional broad boundary catch:
        # this is the command execution entrypoint and we normalize any failure
        # into structured logging + CommandResult for callers.
        context = format_command_args(**kwargs)
        if log_errors:
            log_exception(
                logger,
                "command error: %s%s" % (command_name, context),
                context=command_ctx,
                exc=exc,
            )
        else:
            logger.warning("command error: %s%s (%s)%s", command_name, context, exc, context_suffix(command_ctx))
        return CommandResult(
            False,
            None,
            message=str(exc),
            error_code="exception",
            command_name=command_name,
        )

    if isinstance(result, CommandResult):
        return result

    if result is None:
        logger.warning("command returned no result: %s%s", command_name, context_suffix(command_ctx))
        return CommandResult(
            False,
            None,
            message="Command returned no result",
            error_code="no_result",
            command_name=command_name,
        )

    if isinstance(result, bool):
        success = result
        payload = None
    elif isinstance(result, tuple) and result and isinstance(result[0], bool):
        success = result[0]
        payload = result[1] if len(result) > 1 else None
    else:
        success = True
        payload = result

    if not success:
        context = format_command_args(**kwargs)
        logger.warning("command failed: %s%s", command_name, context)
        return CommandResult(
            False,
            payload,
            message="Command failed",
            error_code="command_failed",
            command_name=command_name,
        )
    return CommandResult(True, payload, command_name=command_name)


def execute_command_checked(
    command_name: str,
    *,
    error_message: Optional[str] = None,
    undo_group: bool = False,
    on_error: Optional[Callable[[CommandResult], None]] = None,
    validator: Optional[ValidatorFn] = None,
    log_context: Optional[LogContext] = None,
    **kwargs: object,
) -> CommandResult:
    """Execute a command and warn on failure."""
    if undo_group:
        with omni.kit.undo.group():
            result = execute_command(command_name, **kwargs)
    else:
        result = execute_command(command_name, **kwargs)
    if validator:
        try:
            result = validator(result)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Intentional broad boundary catch for pluggable validator callbacks.
            # Validator crashes are reported as structured command failures.
            logger.warning("command validator failed for %s: %s", command_name, exc)
            result = CommandResult(
                False,
                result.payload,
                message=str(exc),
                error_code="validation_exception",
                command_name=command_name,
            )
    if not result.success:
        context = format_command_args(**kwargs)
        message = error_message or "command failed: %s%s" % (command_name, context)
        if result.message:
            message = "%s (%s)" % (message, result.message)
        logger.warning("%s%s", message, context_suffix(log_context, command_name=command_name))
        if on_error:
            on_error(result)
    return result
