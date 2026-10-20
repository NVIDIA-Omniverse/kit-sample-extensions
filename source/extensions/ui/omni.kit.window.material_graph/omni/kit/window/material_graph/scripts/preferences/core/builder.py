"""Implement material graph extension logic for `preferences/core/builder.py`."""

import asyncio
from contextlib import contextmanager
from typing import Optional

import carb.settings

# pylint: disable=no-member
import omni.ui

from ...utils.lifecycle_registry import LifecycleRegistry
from .constants import INDENT, ITEM_SPACING, LIST_MAX_ROWS, LIST_MIN_ROWS, LIST_PADDING, ROW_HEIGHT, SECTION_SPACING


class PreferencesBuilderBase:
    """Shared lifecycle/layout helpers for preferences builders."""

    def _initialize_builder_state(self) -> None:
        """Execute initialize builder state behavior for material graph workflows."""

        self._lifecycle: Optional[LifecycleRegistry] = LifecycleRegistry()
        self._subscribed = False
        self._refresh_task: Optional[asyncio.Task] = None

        self._section_spacing = SECTION_SPACING
        self._item_spacing = ITEM_SPACING
        self._indent = INDENT
        self._row_height = ROW_HEIGHT
        self._list_min_rows = LIST_MIN_ROWS
        self._list_max_rows = LIST_MAX_ROWS
        self._list_padding = LIST_PADDING

    @contextmanager
    def _indented_stack(self, spacing: Optional[int] = None):
        """Indent content under a section."""
        with omni.ui.HStack():
            omni.ui.Spacer(width=self._indent)
            with omni.ui.VStack(spacing=spacing if spacing is not None else self._item_spacing):
                yield

    def indented_stack(self, spacing: Optional[int] = None):
        """Public wrapper for an indented stack."""
        return self._indented_stack(spacing)

    def schedule_refresh(self, refresh_fn) -> None:
        """Defer UI refresh to avoid modifying UI during draw callbacks."""
        if not self._lifecycle:
            return

        async def _defer() -> None:
            """Asynchronously execute defer behavior for material graph workflows."""

            await omni.kit.app.get_app().next_update_async()
            if not self._lifecycle:
                return
            refresh_fn()

        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()

        if isinstance(self._lifecycle, LifecycleRegistry):
            self._refresh_task = self._lifecycle.add_task(_defer(), label="preferences refresh")
            return

        settings = carb.settings.get_settings()
        if settings and settings.get("/app/isTestRun"):
            self._refresh_task = asyncio.create_task(_defer())
            self._lifecycle.add_task(self._refresh_task)

    @property
    def indent(self) -> int:
        """Execute indent behavior for material graph workflows."""

        return self._indent

    @property
    def item_spacing(self) -> int:
        """Execute item spacing behavior for material graph workflows."""

        return self._item_spacing

    @property
    def row_height(self) -> int:
        """Execute row height behavior for material graph workflows."""

        return self._row_height

    @property
    def list_min_rows(self) -> int:
        """Execute list min rows behavior for material graph workflows."""

        return self._list_min_rows

    @property
    def list_max_rows(self) -> int:
        """Execute list max rows behavior for material graph workflows."""

        return self._list_max_rows

    @property
    def list_padding(self) -> int:
        """Execute list padding behavior for material graph workflows."""

        return self._list_padding
