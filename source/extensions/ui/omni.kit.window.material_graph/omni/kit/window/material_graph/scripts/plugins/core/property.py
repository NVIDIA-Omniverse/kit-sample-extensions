"""Implement material graph extension logic for `plugins/core/property.py`."""

from typing import Any, Optional, Sequence, Union


class PluginProperty:
    """Describes a plugin-configurable property."""

    def __init__(
        self,
        key: str,
        label: str,
        prop_type: Union[str, type],
        default: Any = None,
        description: str = "",
        allowed_values: Optional[Sequence[Any]] = None,
    ) -> None:
        """Initialize instance state for this material graph component."""

        self.key = key
        self.label = label
        self.type = prop_type
        self.default = default
        self.description = description
        self.allowed_values = list(allowed_values) if allowed_values is not None else None
