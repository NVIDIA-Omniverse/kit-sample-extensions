from typing import Dict, List, Optional, Union

from omni import ui
from pxr import Usd

from ..models import StageMaterialModel
from .new_material_menu import NewMaterialMenu
from .style import ICON_PATH


class MaterialToolBarButtonDesc:
    """
    Represent a button in material toolbar
    Args:
        image_url (Optional[str]): Image url of button. None means spacer.
        clicked_fn (callable): Function called when button clicked. Default None. Function signure:
            void clicked_fn()
        tooltips (Optinal[str]): Button tooltips. Default None.
    """

    def __init__(self, image_url: Optional[str], clicked_fn: callable = None, tooltips: Optional[str] = None):
        self.image_url = image_url
        self.clicked_fn = clicked_fn
        self.tooltips = tooltips


class MaterialToolBarBase:
    """
    Represent a base tool bar for materials in stage.
    Args:
        descs (List[MaterialToolBarButtonDesc]): Default buttons to show on tool bar.
    """

    def __init__(self, descs: List[MaterialToolBarButtonDesc]):
        self._buttons: Dict[MaterialToolBarButtonDesc, ui.Button] = {}
        self._button_descs = []
        self._button_descs.extend(descs)

        self.widget = ui.HStack(width=0, height=0, spacing=4)
        self._spacer_visible = True
        self._spacers: List[ui.Spacer] = []
        self._build_buttons()

    @property
    def visible(self) -> bool:
        """
        Material toolbar visibility.
        """
        return self.widget.visible

    @visible.setter
    def visible(self, value) -> None:
        self.widget.visible = value

    @property
    def computed_height(self):
        return self.widget.computed_height

    @property
    def spacer_visible(self) -> bool:
        """Visibility of spacers in toolbar"""
        return self._spacer_visible

    @spacer_visible.setter
    def spacer_visible(self, visible) -> None:
        if visible != self._spacer_visible:
            self._spacer_visible = visible
            for spacer in self._spacers:
                spacer.visible = visible

    def destroy(self) -> None:
        for desc in self._buttons:
            self._buttons[desc] = None
        self.widget = None

    def append_buttons(self, button_descs: Union[MaterialToolBarButtonDesc, List[MaterialToolBarButtonDesc]]) -> None:
        """
        Append buttons to material toolbar.
        Args:
            button_descs (Union[MaterialToolBarButtonDesc, List[MaterialToolBarButtonDesc]]): Desc of buttons to be appended.
        """
        if isinstance(button_descs, list):
            self._button_descs.extend(button_descs)
        else:
            self._button_descs.append(button_descs)
        self._build_buttons()

    def get_button(self, desc: MaterialToolBarButtonDesc) -> Optional[ui.Button]:
        """
        Get material toolbar button by desc. Return None if not found.
        Args:
            desc (MaterialToolBarButtonDesc): Button description.
        """
        return self._buttons[desc] if desc in self._buttons else None

    def _build_buttons(self):
        self.widget.clear()
        self._buttons.clear()
        self._spacers.clear()
        with self.widget:
            for desc in self._button_descs:
                if desc.image_url:
                    with ui.VStack(width=26):
                        ui.Spacer()
                        self._buttons[desc] = ui.Button(
                            image_url=desc.image_url,
                            image_width=20,
                            image_height=20,
                            width=26,
                            height=26,
                            clicked_fn=desc.clicked_fn,
                            style_type_name_override="ToolBar.Button",
                            tooltip=desc.tooltips if desc.tooltips else "",
                        )
                        ui.Spacer()
                else:
                    spacer = ui.Spacer()
                    self._spacers.append(spacer)


class MaterialToolBar(MaterialToolBarBase):
    """
    Represent a tool bar with buttons defined for materials in stage.
    Args:
        model (StageMaterialModel): Stage model, used for picking
        on_materials_picked_fn (callable): Function called when materials picked. Function signure:
            void on_materials_picked_fn(picked_material_prims: Dict[Usd.Prim, any])
        on_trigger_property_fn (callable): Function called when show/hide property button clicked. Function signure:
            void on_trigger_property_fn()
    """

    def __init__(self, model: StageMaterialModel, on_materials_picked_fn: callable, on_trigger_property_fn: callable):
        self._model = model
        self._on_materials_picked_fn = on_materials_picked_fn
        self._on_trigger_property_fn = on_trigger_property_fn
        self._pick_button_desc = MaterialToolBarButtonDesc(
            f"{ICON_PATH}/samples_dark.svg",
            clicked_fn=self._on_pick_materials,
            tooltips="Sample a material from the viewport by clicking on an object",
        )
        self._property_button_desc = MaterialToolBarButtonDesc(
            f"{ICON_PATH}/property_dark.svg",
            clicked_fn=self._on_trigger_property_fn,
            tooltips="Open material parameters",
        )
        super().__init__(
            [
                self._pick_button_desc,
                MaterialToolBarButtonDesc(
                    f"{ICON_PATH}/Create_New_Material.png",
                    clicked_fn=self._create_material,
                    tooltips="Create a new material",
                ),
                MaterialToolBarButtonDesc(""),
                self._property_button_desc,
            ]
        )

    def destroy(self):
        self._stop_pick_material()
        super().destroy()

    @property
    def btnProperty(self) -> ui.Button:
        return self.get_button(self._property_button_desc)

    def _on_pick_materials(self):
        pick_button = self.get_button(self._pick_button_desc)
        if pick_button:
            if pick_button.selected:
                self._stop_pick_material()
            else:
                self._start_pick_material()

    def _start_pick_material(self):
        pick_button = self.get_button(self._pick_button_desc)
        if pick_button:
            pick_button.selected = True
        self._model.start_pick(self._on_materials_picked)

    def _stop_pick_material(self):
        self._model.stop_pick()
        pick_button = self.get_button(self._pick_button_desc)
        if pick_button:
            pick_button.selected = False

    def _create_material(self):
        NewMaterialMenu.show()

    def _on_materials_picked(self, picked_material_prims: Dict[Usd.Prim, any]):
        if picked_material_prims:
            if self._on_materials_picked_fn is not None:
                self._on_materials_picked_fn(picked_material_prims)
            self._stop_pick_material()
