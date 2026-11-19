import weakref
from typing import List

import omni.usd
from omni import ui
from omni.kit.property.usd import PrimSelectionPayload
from pxr import Sdf, Usd, UsdShade

from .property_style import get_style as get_property_widget_style
from .style import UI_STYLES


class MaterialPropertyWidget:
    def __init__(self):
        try:
            from omni.kit.property.material.scripts.usd_attribute_widget import UsdMaterialAttributeWidget

            self._property_widget = UsdMaterialAttributeWidget(
                schema=UsdShade.Shader,
                title="Shader",
                include_names=["info:mdl:sourceAsset", "info:mdl:sourceAsset:subIdentifier"],
                exclude_names=[],
            )
        except ImportError:
            from omni.kit.property.material.scripts.widgets import UsdShadeMaterialWidget

            self._property_widget = UsdShadeMaterialWidget(
                title="Shader",
            )
        self._property_widget._collapsable = False

        self._property_container = ui.VStack()
        with self._property_container:
            with ui.ScrollingFrame(
                vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                style=get_property_widget_style(),
            ):
                with ui.VStack():
                    with ui.HStack(height=0):
                        ui.Spacer(width=7)
                        ui.Label("Prim Path", width=80, style_type_name_override="Property.Label")
                        ui.Spacer(width=8)
                        self._material_path_field = ui.StringField(
                            enabled=False, style_type_name_override="Property.Path"
                        )
                        ui.Spacer(width=7)

                    self._property_widget.build()

        self._property_widget._collapsable_frame.style_type_name_override = "Property.Frame"
        self._property_widget._collapsable_frame.style = UI_STYLES

    @property
    def visible(self) -> bool:
        return self._property_container.visible

    @visible.setter
    def visible(self, value) -> None:
        self._property_container.visible = value

    def set_materials(self, material_prims: List[Usd.Prim]) -> None:
        material_paths: List[Sdf.Path] = []
        shader_paths: List[Sdf.Path] = []
        if material_prims:
            for prim in material_prims:
                shader_prim = omni.usd.get_shader_from_material(prim, True)
                shader_paths.append(shader_prim.GetPath())
                material_paths.append(prim.GetPath())

        stage = None
        if shader_paths:
            usd_context = omni.usd.get_context()
            stage = weakref.ref(usd_context.get_stage())
            for shader_path in shader_paths:
                try:
                    usd_context.add_to_pending_creating_mdl_paths(path=shader_path.pathString)
                except AttributeError:
                    pass

        payload = PrimSelectionPayload(stage, shader_paths)

        self._property_widget.on_new_payload(payload)
        self._property_widget.request_rebuild()

        if shader_paths:
            tooltip = ""
            if len(material_paths) == 1:
                self._material_path_field.name = ""
                material_path = material_paths[0].pathString
            else:
                self._material_path_field.name = "mixed"
                material_path = "Mixed"
                for index, path in enumerate(material_paths):
                    tooltip += f"{path.pathString}\n"
                    if index > 9:
                        tooltip += f"...."
                        break
            self._material_path_field.model.set_value(material_path)
            self._material_path_field.set_tooltip(tooltip)
        else:
            self._material_path_field.model.set_value("")
            self._material_path_field.set_tooltip("")
