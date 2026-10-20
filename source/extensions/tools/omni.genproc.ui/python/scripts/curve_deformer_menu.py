"""
Manage Menu for creating deformer.
"""

import carb
import omni.graph.core as og
import omni.usd
from omni.kit.menu.utils import MenuItemDescription
from pxr import Gf, Sdf, Usd, UsdGeom, UsdUtils


def get_selection():
    """
    get a selected object list from scene
    """
    return omni.usd.get_context().get_selection().get_selected_prim_paths() or []


def get_prim(path):
    """
    To get Usd Prim by given path.

    Args:
        path: Path or Sdf path or Usd Prim.

    Returns:
        UsdPrim at the given path.

    """
    stage = omni.usd.get_context().get_stage()

    if isinstance(path, Usd.Prim):
        return path
    elif isinstance(path, str) or isinstance(path, Sdf.Path):
        return stage.GetPrimAtPath(path)
    else:
        try:
            return get_prim(path.GetPath())
        except:
            return None


def is_prim_like_mesh(prim):
    points_attr = prim.HasAttribute("points")
    return points_attr


def is_prim_like_curve(prim):
    points_attr = prim.HasAttribute("points")
    curve_vertex_counts_attr = prim.HasAttribute("curveVertexCounts")
    return curve_vertex_counts_attr and points_attr


def has_time_sampled_points(prim):
    points_attr = prim.GetAttribute("points")
    return points_attr.GetTimeSamples()


class NodeBase:
    node_type = None
    output_name = None

    def __init__(self, root_path, node_name):
        self.node = CurveDeformerMenu.create_node(f"{root_path}/{node_name}", self.node_type)

    def relate(self, input_attr, input_prim):
        CurveDeformerMenu.create_relationship(self.node, input_attr, input_prim)

    def connect(self, input_attr, input_prim):
        CurveDeformerMenu.create_connection(self.node, input_attr, input_prim)

    def output(self):
        return f"{self.node.get_prim_path()}/{self.output_name}"


class TimeNode(NodeBase):
    node_type = "omni.graph.core.Time"
    output_name = "output:frame"

    def __init__(self, root_path, node_name):
        super().__init__(root_path, node_name)

    def output(self):
        return f"{self.node.get_prim_path()}.{self.output_name}"


class ImportNode(NodeBase):
    node_type = "omni.graph.nodes.ReadPrimsV2"
    output_name = "outputs_primsBundle"

    def __init__(self, root_path, node_name):
        super().__init__(root_path, node_name)

    def set_input_prim(self, input_prim):
        self.relate("inputs:prims", input_prim)

    def set_time(self, input_prim):
        self.connect("inputs:usdTimecode", input_prim)


class ExportNode(NodeBase):
    node_type = "omni.graph.ExportUSDPrim"
    output_name = "outputs_output"

    def __init__(self, root_path, node_name):
        super().__init__(root_path, node_name)

    def set_input_bundle(self, input_bundle):
        self.relate("inputs:bundle", input_bundle)

    def set_time(self, input_prim):
        self.connect("inputs:usdTimecode", input_prim)


class CurveDeformerNode(NodeBase):
    node_type = "omni.graph.DeformByCurve"
    output_name = "outputs_mesh"

    def __init__(self, root_path, node_name):
        super().__init__(root_path, node_name)

    def set_input_curve(self, input_prim):
        self.relate("inputs:curve", input_prim)

    def set_input_mesh(self, input_prim):
        self.relate("inputs:mesh", input_prim)


class ExportToHydraNode(NodeBase):
    node_name = "ExportToHydra"
    node_type = "omni.graph.ExportToHydra"

    def __init__(self, root_path, node_name):
        super().__init__(root_path, node_name)

    def set_input_mesh(self, input_prim):
        self.relate("inputs:mesh", input_prim)


class CurveDeformerMenu:
    """
    Class to create and manage menu item for the deformer
    """

    def __init__(self):
        super().__init__()
        self.menus = []
        self.on_startup()

    def on_startup(self) -> None:
        """
        Method called by the extension on startup to create the menu items.
        :return: None
        """
        sub_menus = [
            MenuItemDescription(
                name="Create Curve Deformer", appear_after="From Pencil", onclick_fn=self._on_create_curve_clicked
            )
        ]
        self.menus = [
            MenuItemDescription(name="BasisCurves", glyph="menu_curve.svg", appear_after="Xform", sub_menu=sub_menus),
        ]
        omni.kit.menu.utils.add_menu_items(self.menus, "Create")

    def on_shutdown(self) -> None:
        """
        Method called by the extension on shutdown
        :return: None
        """
        omni.kit.menu.utils.remove_menu_items(self.menus, "Create")
        self.menus = []

    @staticmethod
    def _on_create_curve_clicked():
        # omni.anim.prox.get_instance()._ui.show()
        paths = get_selection()
        meshes = []
        curves = []
        bind_points = []

        for path in paths:
            prim = get_prim(path)

            if is_prim_like_curve(prim):
                curves.append(path)
                points = list(prim.GetAttribute("points").Get(0))
                bind_points += points

            elif is_prim_like_mesh(prim):
                meshes.append(path)

        if len(curves) == 0:
            print("No curves selected")
            return

        if len(meshes) == 0:
            print("No meshes selected")
            return

        root_path = "/CurveDeformer"
        stage = omni.usd.get_context().get_stage()
        root_path = omni.usd.get_stage_next_free_path(stage, root_path, False)

        time_node = TimeNode(root_path, "Time")

        mesh_import = ImportNode(root_path, "MeshImport")
        mesh_import.set_input_prim(meshes)
        mesh_import.set_time(time_node.output())

        curve_import = ImportNode(root_path, "CurveImport")
        curve_import.set_input_prim(curves)
        curve_import.set_time(time_node.output())

        curve_deformer = CurveDeformerNode(root_path, "CurveDeformer")

        curve_deformer.set_input_curve([curve_import.output()])
        curve_deformer.set_input_mesh([mesh_import.output()])

        prim = stage.GetPrimAtPath(curve_deformer.node.get_prim_path())
        prim.CreateAttribute("inputs:bindCurvePoints", Sdf.ValueTypeNames.Point3fArray).Set(bind_points)

        export_to_hydra = False

        if export_to_hydra:
            export_node = ExportToHydraNode(root_path, "ExportToHydra")
            export_node.set_input_mesh([curve_deformer.output()])
        else:
            export_node = ExportNode(root_path, "MeshExport")
            export_node.set_input_bundle([curve_deformer.output()])

            output_meshes = []
            for mesh in meshes:
                base = mesh.split("/")[-1]
                output_mesh = f"{root_path}/{base}"
                output_mesh = omni.usd.get_stage_next_free_path(stage, output_mesh, False)
                output_meshes.append(output_mesh)
                omni.usd.duplicate_prim(stage, mesh, output_mesh, duplicate_layers=True)

            CurveDeformerMenu.create_relationship(export_node.node, "outputs_prim", output_meshes)

    @staticmethod
    def create_relationship(node, attr_name, targets):
        stage = omni.usd.get_context().get_stage()

        prim = stage.GetPrimAtPath(node.get_prim_path())
        prim.CreateRelationship(attr_name, False).SetTargets(targets)

    @staticmethod
    def create_connection(node, attr_name, target):

        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath(node.get_prim_path())
        attr = prim.GetAttribute(attr_name)

        attr.AddConnection(target)

    # @staticmethod
    # def get_prim(node):
    #     stage = omni.usd.get_context().get_stage()
    #     omnigraph_helper = og.OmniGraphHelper()
    #     path = node.get_prim_path()
    #     prim = stage.GetPrimAtPath(path)
    #     return prim

    @staticmethod
    def create_node(node_path, node_type):
        stage = omni.usd.get_context().get_stage()
        omnigraph_helper = og.OmniGraphHelper()
        node_path = omni.usd.get_stage_next_free_path(stage, node_path, False)
        node = omnigraph_helper.create_node(node_path, node_type, allow_exists=True)
        return node


# TODO: Remove this
# CurveDeformerMenu._on_create_curve_clicked()
