"""Startup controller for initial empty-state UI and quick-create entry actions."""

import omni.ui

from ....config.logging import logger
from ....config.paths import Paths

# pylint: disable=no-member


class StartupController:
    """Builds the startup UI for the graph widget."""

    def __init__(self, widget: object, show_startup_buttons: bool = True) -> None:
        """Initialize startup sequencing, extension hooks, and first-run controller state."""
        self._widget = widget
        self._show_startup_buttons = show_startup_buttons

    def build_startup(self) -> None:
        """Build the startup view and buttons."""
        self._widget.set_toolbar_items(self._widget.get_toolbar_items())

        with omni.ui.ZStack():
            omni.ui.Rectangle(
                style_type_name_override="Graph",
                accept_drop_fn=self._widget.on_accept_drop,
                drop_fn=self._widget.on_drop,
            )

            if not self._show_startup_buttons:
                # don't show the default buttons
                logger.debug("startup buttons hidden by flag; skipping startup button rendering this frame")
                self._show_startup_buttons = True
                return

            icon_size = 120
            with omni.ui.HStack(content_clipping=True):
                with omni.ui.VStack():
                    omni.ui.Spacer()
                    with omni.ui.HStack():
                        omni.ui.Spacer()
                        omni.ui.Button(
                            "Edit Selected Material",
                            image_url=f"{Paths.ICON_PATH}/canvas_edit.png",
                            style_type_name_override="Graph",
                            width=icon_size,
                            height=0,
                            image_width=icon_size,
                            image_height=icon_size,
                            spacing=5,
                            clicked_fn=self._widget.edit_graph,
                        )
                        omni.ui.Button(
                            "New Material Graph",
                            image_url=f"{Paths.ICON_PATH}/canvas_new.png",
                            style_type_name_override="Graph",
                            width=icon_size,
                            height=0,
                            image_width=icon_size,
                            image_height=icon_size,
                            spacing=5,
                            clicked_fn=self._widget.new_graph,
                        )
                        omni.ui.Spacer()
                    omni.ui.Spacer()

    def destroy(self) -> None:
        """Release subscriptions, callbacks, and cached references owned by this controller."""
        self._widget = None
