from typing import Collection, Optional

from omni import ui
from omni.kit.browser.core import BrowserWidget, OptionMenuDescription, OptionsMenu
from omni.kit.browser.material import MaterialDetailDelegate, MaterialOptionsMenu

from .delegate import MaterialPrimDelegate
from .panel_mode import PanelModes


class MaterialStageOptionsMenu(OptionsMenu):
    """
    Represent options menu used in stage materials.
    Args:
        stage_delegate (MaterialPrimDelegate): Delegate for stage material
    """

    def __init__(self, stage_delegate: MaterialPrimDelegate):
        super().__init__()
        self._stage_delegate = stage_delegate

        self._menu_descs = []
        self.append_menu_item(
            OptionMenuDescription(
                "Capture Thumbnail For Selected",
                clicked_fn=self._on_capture_selected_thumbnails,
            )
        )
        self.append_menu_item(
            OptionMenuDescription(
                "Capture Thumbnail For All",
                clicked_fn=self._on_capture_all_thumbnails,
            )
        )

    def _on_capture_selected_thumbnails(self) -> None:
        if self._browser_widget is None:
            return

        detail_items = self._browser_widget.detail_selection
        for detail_item in detail_items:
            if detail_item.prim:
                self._stage_delegate.capture_thumbnail(detail_item)

    def _on_capture_all_thumbnails(self) -> None:
        if self._browser_widget is None:
            return

        model = self._browser_widget.model
        collection_items = model.get_item_children()
        for collection_item in collection_items:
            category_items = model.get_item_children(collection_item)
            for category_item in category_items:
                detail_items = model.get_item_children(category_item)
                for detail_item in detail_items:
                    if detail_item.prim:
                        self._stage_delegate.capture_thumbnail(detail_item)
