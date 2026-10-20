import carb
import omni.kit.menu.utils
import omni.ui as ui
from omni.kit.menu.utils import MenuItemDescription

from . import menu_common
from .core import Core
from .windows import Windows


class Menu:
    def __init__(self):
        super().__init__()
        self._core = Core()
        self._windows = Windows(self._core)
        self._create_menu_items = []
        self._graph_menu_items = []
        self._create_menu = []

        self.on_startup()

    def on_startup(self) -> None:
        self._core.on_startup()

        # Create -> BasisCurves -> Graph menu
        self._graph_menu_items.append(
            MenuItemDescription(
                name=menu_common.CURVE_FROM_XFORMABLES, onclick_action=("omni.genproc.ui", "curve_from_xformables")
            )
        )
        self._graph_menu_items.append(
            MenuItemDescription(name=menu_common.GET_CURVE_DATA, onclick_action=("omni.genproc.ui", "get_curve_data"))
        )
        self._graph_menu_items.append(
            MenuItemDescription(
                name=menu_common.TAG_CURVES_WITH_RAMP, onclick_action=("omni.genproc.ui", "tag_curves_with_ramp")
            )
        )
        self._graph_menu_items.append(
            MenuItemDescription(name=menu_common.RESAMPLE_CURVES, onclick_action=("omni.genproc.ui", "resample_curves"))
        )

        self._create_menu_items.append(MenuItemDescription(name="Graph", sub_menu=self._graph_menu_items))

        self._create_menu = [
            MenuItemDescription(
                name="BasisCurves", glyph="menu_curve.svg", appear_after="Xform", sub_menu=self._create_menu_items
            ),
        ]

        omni.kit.menu.utils.add_menu_items(self._create_menu, "Create")

        self._graph_menu_items.append(
            MenuItemDescription(
                name=menu_common.CURVE_FROM_XFORMABLES, onclick_action=("omni.genproc.ui", "curve_from_xformables")
            )
        )

    def on_shutdown(self):
        self._core.on_shutdown()
        omni.kit.menu.utils.remove_menu_items(self._create_menu, "Create")
        self._create_menu = []
        self._create_menu_items = []
        self._graph_menu_items = []

    def _on_menu_click(self, menu_item):
        if menu_item is menu_common.CURVE_FROM_XFORMABLES:
            self._windows.curve_from_xformables_clicked()
        elif menu_item is menu_common.GET_CURVE_DATA:
            self._windows.get_curve_data_clicked()
        elif menu_item is menu_common.TAG_CURVES_WITH_RAMP:
            self._windows.tag_curves_with_ramp_clicked()
        elif menu_item is menu_common.RESAMPLE_CURVES:
            self._windows.resample_curves_clicked()
