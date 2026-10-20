"""Implement material graph extension logic for `config/nodes.py`."""

from .color import rgb_to_abgr


class Nodes:
    """UI color and sizing constants for nodes and backdrops."""

    ERROR_BACKGROUND_COLOR = rgb_to_abgr(0xCB6A6A)
    ERROR_HIGHLIGHT_COLOR = rgb_to_abgr(0xAF4E4E)
    WARNING_BACKGROUND_COLOR = rgb_to_abgr(0xDFCB4A)
    WARNING_HIGHLIGHT_COLOR = rgb_to_abgr(0xA19337)
    WARNING_LABEL_COLOR = rgb_to_abgr(0x292929)
    EXPANSION_ON_COLOR_ABGR = 0xFFA8A8A8
    EXPANSION_OFF_COLOR_ABGR = 0xFF23211F
    COMPOUND_BACKGROUND_COLOR_ABGR = 0xFF5F5F5F
    DROP_OVERLAY_ACCEPT_ABGR = 0x22487244
    DROP_OVERLAY_REJECT_ABGR = 0x225C4A7A

    class Backdrop:
        """Backdrop defaults for graph UI."""

        DEFAULT_SIZE = (200.0, 50.0)
