"""Public command execution surface for Material Graph operations.

This package intentionally exports wrapper functions, not raw command classes.
Wrappers add argument validation, structured `CommandResult` payloads, and
post-condition checks around Kit command execution so callers get consistent
behavior even when underlying commands have bool/tuple return variability.

`impl` contains registration-time command classes used internally by
Kit's command registry. External callers should use wrapper functions here.

Typical consumers: UI controllers, model edit flows, and tests that execute
graph operations through stable wrapper APIs.
"""

from . import wrappers
from .wrappers import *  # noqa: F403

__all__ = list(wrappers.__all__)
