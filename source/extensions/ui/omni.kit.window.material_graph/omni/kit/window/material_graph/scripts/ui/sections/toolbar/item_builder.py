"""Toolbar item descriptor builder."""

from typing import Any, Dict, List

from ....config.paths import Paths


class ToolbarItemBuilder:
    """Build toolbar item descriptors."""

    def __init__(self, controller: Any, add_pause_button: bool) -> None:
        """Store toolbar controller context for item generation."""
        self._controller = controller
        self._add_pause_button = add_pause_button

    def build(self) -> List[Dict[str, Any]]:
        """Create toolbar item descriptors for current controller state.

        Not used for rendering (parent toolbar is disabled). Kept for pause state detection.
        """
        controller = self._controller
        toolbar_items: List[Dict[str, Any]] = []

        toolbar_items.append({"name": "__catalog_tabs__"})

        toolbar_items.append({"name": " "})

        if controller._widget.current_context:
            toolbar_items.append({"name": "__context_tabs__"})

        toolbar_items.append({"name": " "})

        if self._add_pause_button and controller._widget.model:
            toolbar_items.extend(self._build_pause_items())

        toolbar_items.append(
            {
                "name": "Help",
                "enabled": True,
                "tooltip": "MaterialGraph documentation",
                "on_clicked": controller.on_toolbar_help_clicked,
                "icon": f"{Paths.TOOLBAR_ICON_PATH}/help_dark.svg",
            }
        )

        return toolbar_items

    def _build_pause_items(self) -> List[Dict[str, Any]]:
        """Build pause and recompile toolbar items."""
        controller = self._controller
        items: List[Dict[str, Any]] = []
        if controller._widget.model.pause:
            items.append(
                {
                    "name": "Recompile",
                    "enabled": True,
                    "tooltip": ("Refresh material, allowing it to compile and then immediately pausing.\n(CTRL+R)"),
                    "on_clicked": controller.unpause_and_pause,
                    "icon": f"{Paths.TOOLBAR_ICON_PATH}/reload_dark.svg",
                }
            )

        icon = f"{Paths.TOOLBAR_ICON_PATH}/pause_dark_a.svg"
        tooltip_prefix = "Pause"
        style_type_name_override = "ToolBar.Button"

        if controller._widget.model.pause:
            icon = f"{Paths.TOOLBAR_ICON_PATH}/pause_red_dark_a.svg"
            tooltip_prefix = "Resume"
            style_type_name_override = "ToolBar.Button.Pause"

        items.append(
            {
                "name": "Pause",
                "enabled": True,
                "tooltip": f"{tooltip_prefix} material compilation.",
                "on_clicked": controller.toggle_material_compilation,
                "icon": icon,
                "style_type_name_override": style_type_name_override,
            }
        )
        return items
