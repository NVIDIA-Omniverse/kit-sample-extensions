# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""SDR registry access for MaterialX identifier validation."""

from typing import Any, Optional

from pxr import Sdr


def get_sdr_registry() -> Any:
    """Return the process-wide SDR registry supplied by the running Kit."""
    return Sdr.Registry()


def find_sdr_node(registry: Any, identifier: str, source_type: str) -> Optional[Any]:
    """Resolve an SDR identifier while containing version-specific API errors."""
    if not identifier:
        return None
    try:
        if source_type:
            node = registry.GetShaderNodeByIdentifierAndType(identifier, source_type)
            if node:
                return node
        return registry.GetShaderNodeByIdentifier(identifier)
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return None
