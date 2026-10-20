"""Core preferences builder helpers and layout constants.

This package provides the PreferencesBuilderBase and layout constants
(SECTION_SPACING, ITEM_SPACING, INDENT, ROW_HEIGHT, etc.) used to
build consistent preferences pages. The base class defines the
section/row structure; constants ensure visual consistency.

Architectural role: Core preferences are a leaf layer; they define
the structure and spacing for all preferences sections without
depending on domain logic.

Typical consumers: All preferences section builders and the
preferences page assembly.
"""

from .builder import PreferencesBuilderBase
from .constants import (
    BUTTON_WIDTH,
    INDENT,
    ITEM_SPACING,
    LIST_MAX_ROWS,
    LIST_MIN_ROWS,
    LIST_PADDING,
    ROW_HEIGHT,
    SECTION_SPACING,
)

__all__ = [
    "BUTTON_WIDTH",
    "INDENT",
    "ITEM_SPACING",
    "LIST_MAX_ROWS",
    "LIST_MIN_ROWS",
    "LIST_PADDING",
    "PreferencesBuilderBase",
    "ROW_HEIGHT",
    "SECTION_SPACING",
]
