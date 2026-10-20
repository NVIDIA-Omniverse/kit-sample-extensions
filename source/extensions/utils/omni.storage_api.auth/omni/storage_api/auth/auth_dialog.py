"""Modal dialog shown while waiting for portal auth (status text + ping-pong indicator + cancel)."""

import asyncio
from typing import Callable, Optional


class AuthStatusDialog:
    """Modal dialog with status text, sliding activity indicator, and cancel button."""

    def __init__(self, title: str = "Authentication", cancel_callback: Optional[Callable] = None):
        self._title = title
        self._cancel_callback = cancel_callback
        self._window = None
        self._status_label = None
        self._indicator_spacer = None
        self._is_cancelled = False
        self._closing_programmatically = False
        self._animate_task = None

        self._build_ui()

    def _build_ui(self):
        """Build the dialog UI."""
        import omni.ui as ui

        self._window = ui.Window(
            self._title,
            visible=False,
            width=420,
            height=0,
            dockPreference=ui.DockPreference.DISABLED,
            auto_resize=True,
            visibility_changed_fn=self._on_visibility_changed,
        )

        self._window.flags = (
            ui.WINDOW_FLAGS_NO_COLLAPSE
            | ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_NO_SCROLLBAR
            | ui.WINDOW_FLAGS_NO_MOVE
            | ui.WINDOW_FLAGS_MODAL
        )

        with self._window.frame:
            with ui.VStack(spacing=12, height=0):
                self._status_label = ui.Label(
                    "Initializing...",
                    alignment=ui.Alignment.CENTER,
                    word_wrap=True,
                )

                with ui.HStack(height=6):
                    ui.Spacer()
                    with ui.ZStack(width=300, height=6):
                        ui.Rectangle(style={"background_color": 0x40FFFFFF, "border_radius": 3})
                        with ui.HStack():
                            self._indicator_spacer = ui.Spacer(width=0)
                            ui.Rectangle(
                                width=60,
                                style={"background_color": 0xFFFF9E3D, "border_radius": 3},
                            )
                            ui.Spacer()
                    ui.Spacer()

                with ui.HStack(height=30):
                    ui.Spacer()
                    ui.Button(
                        "Cancel",
                        width=80,
                        height=30,
                        clicked_fn=self._on_cancel_clicked,
                    )
                    ui.Spacer()

    def _on_cancel_clicked(self):
        """Cancel button handler — treated the same as a user close."""
        self._trigger_cancel()

    def _on_visibility_changed(self, visible: bool):
        """Treat X-button close as a cancel (``_closing_programmatically`` suppresses our own ``hide()`` calls)."""
        if visible or self._closing_programmatically or self._window is None:
            return
        self._trigger_cancel()

    def _trigger_cancel(self):
        """Hide the dialog and notify the cancel callback (idempotent)."""
        if self._is_cancelled:
            return
        self._is_cancelled = True
        self.hide()
        if self._cancel_callback:
            self._cancel_callback()

    def show(self):
        """Show the dialog and start the activity indicator animation."""
        if self._window:
            self._is_cancelled = False
            self._window.visible = True
            self._window.focus()
            self._start_animation()

    def hide(self):
        """Hide the dialog and stop the animation."""
        self._stop_animation()
        if self._window:
            self._closing_programmatically = True
            try:
                self._window.visible = False
            finally:
                self._closing_programmatically = False

    def _start_animation(self):
        """Start the ping-pong activity indicator animation."""
        self._stop_animation()

        async def _animate():
            import math

            import omni.kit.app
            import omni.ui as ui

            track_width = 300.0
            indicator_width = 60.0
            max_offset = track_width - indicator_width
            t = 0.0
            try:
                while True:
                    await omni.kit.app.get_app().next_update_async()
                    t += 0.03
                    offset = ((math.sin(t * math.pi) + 1.0) / 2.0) * max_offset
                    if self._indicator_spacer:
                        self._indicator_spacer.width = ui.Length(offset)
            except asyncio.CancelledError:
                pass

        self._animate_task = asyncio.ensure_future(_animate())

    def _stop_animation(self):
        """Stop the activity indicator animation."""
        if self._animate_task and not self._animate_task.done():
            self._animate_task.cancel()
            self._animate_task = None

    def set_status(self, status_text: str):
        """Update the status text."""
        if self._status_label:
            self._status_label.text = status_text

    def destroy(self):
        """Clean up the dialog."""
        self._stop_animation()
        if self._window:
            self._closing_programmatically = True
            self._window.visible = False
            self._window.destroy()
            self._window = None
        self._status_label = None
        self._indicator_spacer = None
        self._cancel_callback = None
