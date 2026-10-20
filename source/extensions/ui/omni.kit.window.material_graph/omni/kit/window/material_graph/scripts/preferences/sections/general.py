"""Implement material graph extension logic for `preferences/sections/general.py`."""

from typing import Any, List, Optional

import carb.settings

# pylint: disable=no-member
import omni.ui

from ...config.logging import logger
from ...settings.settings import Settings
from ...settings.utils import (
    DROPPABLE_TEXTURE_FORMATS_DEFAULT,
    normalize_texture_format,
)
from ..core.constants import BUTTON_WIDTH
from ..ui.lists import build_path_list


class GeneralSettingsSection:
    """Builds the General Settings preferences section."""

    def __init__(self, builder) -> None:
        """Initialize instance state for this material graph component."""

        self._builder = builder
        self._texture_format_stack: Optional[Any] = None
        self._texture_format_model: Optional[Any] = None

    def build(self) -> None:
        """Execute build behavior for material graph workflows."""

        settings = carb.settings.get_settings()
        supported_texture_formats = settings.get(Settings.DROPPABLE_TEXTURE_FORMATS)
        if supported_texture_formats is None:
            settings.set(Settings.DROPPABLE_TEXTURE_FORMATS, list(DROPPABLE_TEXTURE_FORMATS_DEFAULT))

        with self._builder.add_frame("General Settings"):
            with self._builder.indented_stack():
                frame = self._builder.add_frame("Droppable Texture Formats")
                frame.tooltip = (
                    "Texture file extensions supported by graph drag-and-drop "
                    "(for example: png, jpg, exr). Enter values without a leading dot."
                )
                with frame:
                    self._texture_format_stack = omni.ui.VStack(height=0)
                    with self._texture_format_stack:
                        self._build_texture_formats_frame()

    def _build_texture_formats_frame(self) -> None:
        """Execute build texture formats frame behavior for material graph workflows."""

        with omni.ui.VStack(height=0, spacing=self._builder.item_spacing):
            self._texture_format_model = omni.ui.SimpleStringModel("")
            field_tooltip = "Enter a texture extension (for example: png, jpg, exr)."
            with omni.ui.HStack(height=self._builder.row_height):
                string_field = omni.ui.StringField(self._texture_format_model, height=self._builder.row_height)
                string_field.tooltip = field_tooltip
                add_button = omni.ui.Button(
                    "Add",
                    clicked_fn=self.add_supported_texture_format,
                    height=self._builder.row_height,
                    width=BUTTON_WIDTH,
                )
                add_button.tooltip = field_tooltip
            omni.ui.Spacer(height=self._builder.item_spacing)
            self._build_path_list(
                Settings.get_droppable_texture_formats(),
                self._on_remove_supported_texture_format,
            )

    def _build_path_list(self, paths: List[str], remove_fn) -> None:
        """Execute build path list behavior for material graph workflows."""

        build_path_list(self._builder, paths, remove_fn)

    def add_supported_texture_format(self) -> None:
        """Execute add supported texture format behavior for material graph workflows."""

        if not self._texture_format_model:
            return
        token = self._texture_format_model.get_value_as_string()
        normalized = normalize_texture_format(token)
        if not normalized:
            logger.warning("catalog texture format rejected: %r", token)
            self._texture_format_model.set_value("")
            return
        current = Settings.get_droppable_texture_formats()
        if normalized not in current:
            current.append(normalized)
            Settings.set_droppable_texture_formats(current)
        self._texture_format_model.set_value("")
        self._builder.schedule_refresh(self.refresh_texture_format_list)

    def _on_remove_supported_texture_format(self, token: str) -> None:
        """Execute on remove supported texture format behavior for material graph workflows."""

        normalized = normalize_texture_format(token)
        current = Settings.get_droppable_texture_formats()
        updated = [item for item in current if item != normalized]
        Settings.set_droppable_texture_formats(updated)
        self._builder.schedule_refresh(self.refresh_texture_format_list)

    def refresh_texture_format_list(self) -> None:
        """Execute refresh texture format list behavior for material graph workflows."""

        if not self._texture_format_stack:
            return
        self._texture_format_stack.clear()
        with self._texture_format_stack:
            self._build_texture_formats_frame()
