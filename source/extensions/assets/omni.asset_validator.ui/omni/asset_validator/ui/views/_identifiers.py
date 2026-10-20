# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

from functools import singledispatchmethod

import omni.ui
from omni.asset_validator.core import Identifier, LayerId, PrimId, PropertyId, StageId, VariantIdMixin

__all__ = ["IdentifierLabel"]


class IdentifierLabel:
    """Renders one or more identifiers as labels inside the current omni.ui context."""

    def __init__(self, identifier: Identifier | tuple[Identifier, ...] | None) -> None:
        identifiers: tuple[Identifier, ...] = (
            identifier if isinstance(identifier, tuple) else ((identifier,) if identifier is not None else ())
        )
        if len(identifiers) == 1:
            label = omni.ui.Label(self._format(identifiers[0]))
            if isinstance(identifiers[0], VariantIdMixin):
                label.set_tooltip(identifiers[0].variant_selection_path.pathString)
        elif identifiers:
            with omni.ui.CollapsableFrame("Multiple Locations", collapsed=True):
                with omni.ui.VStack():
                    for ident in identifiers:
                        label = omni.ui.Label(self._format(ident))
                        if isinstance(ident, VariantIdMixin):
                            label.set_tooltip(ident.variant_selection_path.pathString)

    @singledispatchmethod
    def _format(self, identifier: Identifier) -> str:
        return identifier.as_str()

    @_format.register(PrimId)
    @_format.register(PropertyId)
    def _(self, identifier: PrimId | PropertyId) -> str:
        return f"{identifier.path}"

    @_format.register(LayerId)
    @_format.register(StageId)
    def _(self, identifier: LayerId | StageId) -> str:
        return f"@{identifier.identifier}@"
