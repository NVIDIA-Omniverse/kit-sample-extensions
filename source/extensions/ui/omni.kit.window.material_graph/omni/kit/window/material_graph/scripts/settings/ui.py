"""Implement material graph extension logic for `settings/ui.py`."""

from pxr import UsdShade

from . import utils


def get_force_connect() -> bool:
    """Execute get force connect behavior for material graph workflows."""

    return utils.get_bool(utils.FORCE_CONNECT, False)


def color_noodles() -> bool:
    """Return whether connection noodles should use port type colors."""
    return utils.get_bool(utils.COLOR_NOODLES, False)


def show_catalog() -> bool:
    """Execute show catalog behavior for material graph workflows."""

    return utils.get_bool(utils.SHOW_CATALOG, True)


def confine_nodegraphs() -> bool:
    """Execute confine nodegraphs behavior for material graph workflows."""

    return utils.get_bool(utils.CONFINE_NODEGRAPHS, True)


def confine_backdrops() -> bool:
    """Execute confine backdrops behavior for material graph workflows."""

    return utils.get_bool(utils.CONFINE_BACKDROPS, True)


def preview_texture_input() -> bool:
    """Execute preview texture input behavior for material graph workflows."""

    return utils.get_bool(utils.PREVIEW_TEXTURE_INPUT, False)


def get_render_contexts() -> list[str]:
    """Execute get render contexts behavior for material graph workflows."""

    contexts = utils._get_list(utils.RENDER_CONTEXTS)
    normalized = []
    for context in contexts:
        value = "universal" if context == UsdShade.Tokens.universalRenderContext else context
        normalized.append(value)
    return normalized


def get_render_context() -> str:
    """Execute get render context behavior for material graph workflows."""

    contexts = get_render_contexts()
    return contexts[0] if contexts else "universal"
