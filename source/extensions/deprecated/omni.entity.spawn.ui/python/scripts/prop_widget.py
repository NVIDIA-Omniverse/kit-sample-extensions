from functools import partial

import omni.graph.core as og
import omni.kit.commands
import omni.kit.window.property as prop_wnd
import omni.ui as ui
import omni.usd
from omni.kit.property.usd import UsdAttributeModel
from omni.kit.property.usd.relationship import RelationshipTargetPicker
from omni.kit.property.usd.usd_property_widget import UsdPropertiesWidget, UsdPropertiesWidgetBuilder
from pxr import Gf, Sdf, Usd, UsdGeom

from .event_ui import build_destroy_event_ui, build_spawn_event_ui
from .source_paths_ui import build_source_paths_ui
from .style import ICON_SIZE, LABEL_WIDTH, PROPERTY_WIDGET_ALIGN_WIDTH, spawn_property_style
from .utils import get_upstream_node


class SpawnGraphPropWidget(UsdPropertiesWidget):
    def startup():
        wnd = prop_wnd.get_window()
        if not wnd:
            return

        wnd.register_widget("prim", "spawn_graph", SpawnGraphPropWidget())

    def shutdown():
        wnd = prop_wnd.get_window()
        if not wnd:
            return

        wnd.unregister_widget("prim", "spawn_graph")

    def __init__(self):
        super().__init__("Spawn Graph", False, False)

    def on_new_payload(self, payload):
        self._payload = payload
        return self._find_spawn_node() is not None

    def _find_spawn_node(self):
        # Find the only one spawn node of the graph
        spawn_node = None
        for prim_path in self._payload:
            graph = og.Controller.graph(prim_path)
            if graph is None:
                continue

            for node in graph.get_nodes():
                if node.get_type_name() == "omni.entity.spawn.core.SpawnEntity":
                    if spawn_node is None:
                        spawn_node = node
                    else:
                        return None

        return spawn_node

    def _show_prim_picker(self, cb: callable, filter_types: list = []):
        stage = self._payload.get_stage()
        picker = RelationshipTargetPicker(stage, filter_types, None, {})
        picker.show(1, cb)

    def _build_value_transform(self, index):
        transform_attr = self._find_spawn_node().get_attribute("inputs:transform")
        make_transform_node = get_upstream_node(transform_attr, ["inputs:input" + str(index)])

        if not make_transform_node:
            with ui.VStack():
                ui.Label("Graph Modified")
                ui.Label("Use Grahph Editor or restore original connections")
                return

        stage = self._payload.get_stage()
        make_transform_node_path = Sdf.Path(make_transform_node.get_prim_path())

        def build_vec3(attr_name, display_name, default_value=None):
            attr_path = make_transform_node_path.AppendProperty(attr_name)
            attr = stage.GetAttributeAtPath(attr_path)
            self._build_usd_prop_widget(attr, display_name, default_value)

        with ui.VStack(spacing=5):
            build_vec3("inputs:translation", "Position")
            build_vec3("inputs:rotationXYZ", "Rotation")
            build_vec3("inputs:scale", "Scale", Gf.Vec3f(1.0, 1.0, 1.0))

    def _build_relation_prim(self, attr_path, attr_name, filter_types=[]):
        stage = self._payload.get_stage()

        def get_prim_transform_text():
            targets = stage.GetRelationshipAtPath(attr_path).GetTargets()
            if len(targets) > 0:
                prim_path = targets[0].pathString
                remove_enable = True
            else:
                prim_path = "[ no prim set ]"
                remove_enable = False
            return prim_path, remove_enable

        def on_prim_transform_changed(model):
            text, enable = get_prim_transform_text()
            prim_path_label.text = text
            prim_path_btn.enabled = enable

        def set_prim_transform(attr_path, new_path):
            omni.kit.commands.execute(
                "SetRelationshipTargetsCommand",
                relationship=stage.GetPropertyAtPath(attr_path),
                targets=new_path,
            )

        with ui.VStack(spacing=2):
            model = UsdAttributeModel(stage, [attr_path], False, {})
            model.add_value_changed_fn(on_prim_transform_changed)
            self._models[attr_path].append(model)

            with ui.HStack():
                ui.Label(attr_name, width=LABEL_WIDTH, height=24)
                ui.Spacer(width=PROPERTY_WIDGET_ALIGN_WIDTH)
                prim_path, remove_enable = get_prim_transform_text()
                prim_path_label = ui.Label(prim_path)
                prim_path_btn = ui.Button(
                    name="trash",
                    width=ICON_SIZE,
                    enabled=remove_enable,
                    tooltip="Remove",
                    clicked_fn=lambda: set_prim_transform(attr_path, []),
                )

            with ui.HStack():
                ui.Spacer(width=LABEL_WIDTH + PROPERTY_WIDGET_ALIGN_WIDTH)
                ui.Button(
                    "Select Prim",
                    name="string",
                    width=80,
                    alignment=ui.Alignment.CENTER,
                    clicked_fn=partial(self._show_prim_picker, partial(set_prim_transform, attr_path), filter_types),
                )

    def _build_curve_transform(self, index):
        transform_attr = self._find_spawn_node().get_attribute("inputs:transform")
        transform_node = get_upstream_node(transform_attr, ["inputs:input" + str(index), "inputs:curvesBundle"])
        if not transform_node:
            with ui.VStack():
                ui.Label("Graph Modified")
                ui.Label("Use Grahph Editor or restore original connections")
                return

        node_path = Sdf.Path(transform_node.get_prim_path())
        attr_path = node_path.AppendProperty("inputs:prim")
        self._build_relation_prim(attr_path, "Curve", [UsdGeom.BasisCurves])

    def _build_prim_transform(self, index):
        transform_attr = self._find_spawn_node().get_attribute("inputs:transform")
        transform_node = get_upstream_node(transform_attr, ["inputs:input" + str(index), "inputs:transform"])
        with ui.VStack():
            if not transform_node:
                ui.Label("Graph Modified")
                ui.Label("Use Grahph Editor or restore original connections")
                return
            node_path = Sdf.Path(transform_node.get_prim_path())
            attr_path = node_path.AppendProperty("inputs:prim")
            self._build_relation_prim(attr_path, "Xform Path")
            select_transform_node = get_upstream_node(transform_attr, ["inputs:input" + str(index)])
            prim_path = Sdf.Path(select_transform_node.get_prim_path())
            stage = self._payload.get_stage()
            self._build_usd_prop_widget(
                stage.GetAttributeAtPath(prim_path.AppendProperty("inputs:useTranslation")), "Use Position"
            )
            self._build_usd_prop_widget(
                stage.GetAttributeAtPath(prim_path.AppendProperty("inputs:useRotation")), "Use Rotation"
            )
            self._build_usd_prop_widget(
                stage.GetAttributeAtPath(prim_path.AppendProperty("inputs:useScale")), "Use Scale"
            )

    def _build_mesh_transform(self, index):
        with ui.VStack(spacing=5):
            transform_attr = self._find_spawn_node().get_attribute("inputs:transform")
            transform_node = get_upstream_node(transform_attr, ["inputs:input" + str(index), "inputs:prim"])
            if not transform_node:
                with ui.VStack():
                    ui.Label("Graph Modified")
                    ui.Label("Use Grahph Editor or restore original connections")
                    return
            node_path = Sdf.Path(transform_node.get_prim_path())
            attr_path = node_path.AppendProperty("inputs:prim")
            self._build_relation_prim(attr_path, "Mesh")

            with ui.HStack():
                ui.Label("Distribution", width=LABEL_WIDTH)
                ui.Spacer(width=PROPERTY_WIDGET_ALIGN_WIDTH)
                ui.ComboBox(__class__.ScatterPointsTypeComboBoxModel(self._find_spawn_node(), index))

    class TransformTypeComboBoxModel(ui.AbstractItemModel):
        class Item(ui.AbstractItem):
            def __init__(self, text) -> None:
                super().__init__()

                self.model = ui.SimpleStringModel(text)

        def __init__(self, spawn_node: og.Node):
            super().__init__()

            self._spawn_node = spawn_node

            transform_attr = self._spawn_node.get_attribute("inputs:transform")

            select_node = get_upstream_node(transform_attr, [])
            index = select_node.get_attribute("inputs:index").get()

            self.current_index = ui.SimpleIntModel(index)
            self.current_index.add_value_changed_fn(lambda a: self._item_changed(None))
            self._items = [
                __class__.Item(text)
                for text in ["Value Transform", "Value Range", "Prim Transform", "Prim Mesh", "Curve"]
            ]

        def _item_changed(self, arg0: ui.AbstractItem):
            transform_type_index = self.current_index.as_int

            transform_attr = self._spawn_node.get_attribute("inputs:transform")
            select_node = get_upstream_node(transform_attr, [])
            omni.kit.commands.execute(
                "ChangeProperty",
                prop_path=select_node.get_prim_path() + ".inputs:index",
                value=transform_type_index,
                prev=None,
            )

            super()._item_changed(arg0)

        def get_item_children(self, parentItem):
            return self._items

        def get_item_value_model(self, item=None, column_id: int = 0):
            if item is None:
                return self.current_index
            else:
                return item.model

        def clean(self):
            pass

    class ScatterPointsTypeComboBoxModel(ui.AbstractItemModel):
        class Item(ui.AbstractItem):
            def __init__(self, text) -> None:
                super().__init__()

                self.model = ui.SimpleStringModel(text)

        def __init__(self, spawn_node: og.Node, index):
            super().__init__()

            self._spawn_node = spawn_node
            self._index = index

            scatter_type = self._get_scatter_type()

            if scatter_type is not None:
                self._items = [__class__.Item(text) for text in ["Surface", "Volume"]]
                index = None
                if scatter_type == "Surface":
                    index = 0
                else:
                    index = 1

                self.current_index = ui.SimpleIntModel(index)
            else:
                self._items = [__class__.Item("Customized")]
                self.current_index = ui.SimpleIntModel(0)

            self.current_index.add_value_changed_fn(lambda a: self._item_changed(None))

        def _get_scatter_points_node(self):
            transform_attr = self._spawn_node.get_attribute("inputs:transform")
            return get_upstream_node(transform_attr, ["inputs:input" + str(self._index)])

        def _get_scatter_type(self):
            scatter_points_node = self._get_scatter_points_node()
            on_surface = scatter_points_node.get_attribute("inputs:scatterOnSurface").get()
            inside_volume = scatter_points_node.get_attribute("inputs:scatterInsideVolume").get()

            if (on_surface != inside_volume) and (on_surface or inside_volume):
                if on_surface:
                    return "Surface"
                elif inside_volume:
                    return "Volume"
            else:
                return None

        def _item_changed(self, arg0: ui.AbstractItem):
            if len(self._items) > 1:
                scatter_type_index = self.current_index.as_int

                scatter_points_node = self._get_scatter_points_node()

                with omni.kit.undo.group():
                    if scatter_type_index == 0:
                        omni.kit.commands.execute(
                            "ChangeProperty",
                            prop_path=scatter_points_node.get_prim_path() + ".inputs:scatterOnSurface",
                            value=True,
                            prev=None,
                        )
                        omni.kit.commands.execute(
                            "ChangeProperty",
                            prop_path=scatter_points_node.get_prim_path() + ".inputs:scatterInsideVolume",
                            value=False,
                            prev=None,
                        )
                    elif scatter_type_index == 1:
                        omni.kit.commands.execute(
                            "ChangeProperty",
                            prop_path=scatter_points_node.get_prim_path() + ".inputs:scatterOnSurface",
                            value=False,
                            prev=None,
                        )
                        omni.kit.commands.execute(
                            "ChangeProperty",
                            prop_path=scatter_points_node.get_prim_path() + ".inputs:scatterInsideVolume",
                            value=True,
                            prev=None,
                        )

            super()._item_changed(arg0)

        def get_item_children(self, parentItem):
            return self._items

        def get_item_value_model(self, item=None, column_id: int = 0):
            if item is None:
                return self.current_index
            else:
                return item.model

    def _build_ranged_transform(self, index):
        transform_attr = self._find_spawn_node().get_attribute("inputs:transform")
        ranged_transform_node = get_upstream_node(transform_attr, ["inputs:input" + str(index)])

        if not ranged_transform_node:
            ui.Label("Graph Modified")
            ui.Label("Use Grahph Editor or restore original connections")
            return

        stage = self._payload.get_stage()
        ranged_transform_node_path = Sdf.Path(ranged_transform_node.get_prim_path())

        def build_vec3(attr_name, display_name, default_value=None):
            attr_path = ranged_transform_node_path.AppendProperty(attr_name)
            attr = stage.GetAttributeAtPath(attr_path)
            self._build_usd_prop_widget(attr, display_name, default_value)

        with ui.VStack(spacing=2):
            build_vec3("inputs:position", "Position")
            build_vec3("inputs:positionRandom", "Pos. Random")
            ui.Spacer(height=5)
            build_vec3("inputs:rotateXYZ", "Rotation")
            build_vec3("inputs:rotateXYZRandom", "Rot. Random")
            ui.Spacer(height=5)
            build_vec3("inputs:scale", "Scale", Gf.Vec3f(1.0, 1.0, 1.0))
            build_vec3("inputs:scaleRandom", "Scale Random")

    def _build_spawn_transform(self):
        spawn_transform_frame = ui.CollapsableFrame(
            "Spawn Transform", name="subFrame", build_header_fn=self._build_frame_header
        )
        spawn_transform_frame.style = spawn_property_style
        with spawn_transform_frame:
            with ui.VStack(spacing=6):
                combo_box_model = None

                with ui.HStack(height=0):
                    ui.Label("Type", width=LABEL_WIDTH)
                    ui.Spacer(width=PROPERTY_WIDGET_ALIGN_WIDTH)
                    combo_box = ui.ComboBox(__class__.TransformTypeComboBoxModel(self._find_spawn_node()))
                    combo_box_model = combo_box.model

                    transform_attr = self._find_spawn_node().get_attribute("inputs:transform")

                    select_node = get_upstream_node(transform_attr, [])
                    self._models[select_node.get_prim_path() + ".inputs:index"] = [combo_box_model]

                transform_frame = ui.Frame()

                def build_transform_frame():
                    transform_type_index = combo_box_model.current_index.as_int
                    if transform_type_index == 0:
                        self._build_value_transform(transform_type_index)
                    if transform_type_index == 1:
                        self._build_ranged_transform(transform_type_index)
                    elif transform_type_index == 2:
                        self._build_prim_transform(transform_type_index)
                    elif transform_type_index == 3:
                        self._build_mesh_transform(transform_type_index)
                    elif transform_type_index == 4:
                        self._build_curve_transform(transform_type_index)

                transform_frame.set_build_fn(build_transform_frame)

                def on_transform_type_changed(model, item):
                    transform_frame.rebuild()

                combo_box_model.add_item_changed_fn(on_transform_type_changed)

    def _build_usd_prop_widget(self, prop: Usd.Property, display_name: str, default_value=None, widget_kwargs=None):
        metadata = prop.GetAllMetadata()
        metadata["displayName"] = display_name
        if default_value:
            custom_data = metadata.get("customData", None)
            if custom_data:
                custom_data["default"] = default_value
            else:
                metadata["customData"] = {"default": default_value}
        models = UsdPropertiesWidgetBuilder.build(
            prop.GetPrim().GetStage(),
            prop.GetName(),
            metadata,
            prop.__class__,
            [prop.GetPrimPath()],
            additional_widget_kwargs=widget_kwargs,
        )
        if not isinstance(models, list):
            models = [models]
        self._models[prop.GetPath()] = models

    def _customize_props_layout(self, props):
        stage = self._payload.get_stage()
        node = self._find_spawn_node()
        self._collapsable_frame.style = spawn_property_style
        self._collapsable_frame.name = "groupFrame"
        if node:
            build_source_paths_ui(self, stage, node)
            build_spawn_event_ui(self, stage, node)
            self._build_spawn_transform()
            build_destroy_event_ui(self, stage, node)

        return []
