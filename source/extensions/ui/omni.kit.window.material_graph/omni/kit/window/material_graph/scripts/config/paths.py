"""Implement material graph extension logic for `config/paths.py`."""

from pathlib import Path


def _find_extension_root(start: Path) -> Path:
    """Return nearest parent containing the extension's config marker."""
    for parent in [start] + list(start.parents):
        if (parent / "config" / "extension.toml").exists():
            return parent
    return start


class Paths:
    """Static paths and identifiers for this extension."""

    EXT_PATH = _find_extension_root(Path(__file__).resolve().parent)
    DATA_PATH = EXT_PATH.joinpath("data")
    ICON_PATH = EXT_PATH.joinpath("icons")
    TOOLBAR_ICON_PATH = ICON_PATH.joinpath("toolbar")
    DOCS_URL = "https://docs.omniverse.nvidia.com/extensions/latest/ext_material/ext_material-graph.html"
    MODULE_ID = "omni.kit.window.material_graph"
