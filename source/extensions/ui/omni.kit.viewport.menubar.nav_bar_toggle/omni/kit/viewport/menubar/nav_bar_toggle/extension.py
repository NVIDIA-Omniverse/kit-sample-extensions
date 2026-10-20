import carb.settings
import carb.tokens
import omni.ext
from omni.kit.viewport.menubar.bottom import get_bottombar_name
from omni.kit.viewport.menubar.core import get_instance as get_menubar_instance

from .button import NavBarToggleButton

# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.

__all__ = ["Extension"]


class Extension(omni.ext.IExt):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    def on_startup(self, ext_id: str) -> None:
        sections = ext_id.split("-")
        self._ext_name = sections[0]

        bottombar_name = get_bottombar_name()
        mbi = get_menubar_instance()
        if not mbi:
            return

        bottombar = mbi.get_menubar(bottombar_name)
        if bottombar:
            tokens = carb.tokens.get_tokens_interface()
            icon_path = tokens.resolve(f"${{{self._ext_name}}}/icons/")

            with bottombar:
                self._button = NavBarToggleButton(icon_path)

    def on_shutdown(self) -> None:
        if hasattr(self, "_button"):
            self._button.destroy()
            del self._button
