"""Cross-cutting utility package shared across extension layers.

Utilities here provide reusable infrastructure primitives rather than domain
models: async/task helpers, lifecycle cleanup registries, and timestamp caches.

These modules reduce duplication across commands, plugins, models, and UI while
keeping foundational concerns decoupled from material-graph domain logic.

Typical consumers: all extension layers that need shared async/lifecycle/cache
primitives without introducing circular domain dependencies.
"""

from .async_utils import ensure_future_logged, wait_for_updates
from .file_timestamp_cache import FileTimestampCache
from .lifecycle_registry import LifecycleRegistry
from .modifiers import clear_active_modifier_flags, is_force_connection_modifier_pressed, set_active_modifier_flags

__all__ = [
    "FileTimestampCache",
    "LifecycleRegistry",
    "ensure_future_logged",
    "clear_active_modifier_flags",
    "is_force_connection_modifier_pressed",
    "set_active_modifier_flags",
    "wait_for_updates",
]
