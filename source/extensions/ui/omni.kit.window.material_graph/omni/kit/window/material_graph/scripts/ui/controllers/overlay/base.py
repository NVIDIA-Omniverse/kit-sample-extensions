"""Implement material graph extension logic for `ui/controllers/overlay/base.py`."""

from typing import Optional


class BaseDropOverlayController:
    """Shared drop overlay controller behavior."""

    TRANSPARENT = 0x00000000

    def __init__(self) -> None:
        """Initialize overlay state with fully transparent color."""
        self._current_color = self.TRANSPARENT

    @property
    def current_color(self) -> int:
        """Return the current overlay color."""
        return self._current_color

    def show(self, can_drop: bool) -> None:
        """Show the overlay with accept/reject coloring."""
        raise NotImplementedError

    def hide(self) -> None:
        """Reset overlay state to transparent without releasing controller objects."""
        self._current_color = self.TRANSPARENT

    def destroy(self) -> None:
        """Release controller-held state so teardown does not retain UI references."""
        self._current_color = self.TRANSPARENT

    def _set_color(self, color: Optional[int]) -> None:
        """Set current overlay color, defaulting None to transparent."""
        if color is None:
            self._current_color = self.TRANSPARENT
        else:
            self._current_color = color
