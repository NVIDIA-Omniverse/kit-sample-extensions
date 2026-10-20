import functools
from ctypes import alignment

import carb
import carb.events
import omni.curve.manipulator
import omni.kit
import omni.ramp
import omni.ui as ui
from pxr import Gf, Sdf, Usd, UsdGeom


class Windows:
    def __init__(self, core):
        self._core = core
        self._curve_event_sub = None

    def __del__(self):
        self._curve_event_sub = None

    ################################################################################
    # Utils
    ################################################################################
    def populate_field_with_graph(self, field):
        """Populate a string field with the first graph among the selected prims"""
        paths = self._core.selection.get_selected_prim_paths()

        graph_paths = [
            path
            for path in paths
            if self._core.stage.GetPrimAtPath(path).GetTypeName() in ["ComputeGraph", "OmniGraph"]
        ]

        if len(graph_paths) == 0:
            field.model.set_value("")
        else:
            field.model.set_value(graph_paths[0])

    def populate_field_with_xformables(self, field):
        """Populate a string field with the paths of selected Xformable prims"""
        paths = self._core.selection.get_selected_prim_paths()

        xformable_prims = [
            path
            for path in paths
            if self._core.stage.GetPrimAtPath(path) and self._core.stage.GetPrimAtPath(path).IsA(UsdGeom.Xformable)
        ]

        field.model.set_value(", ".join(xformable_prims))

    def populate_field_with_basis_curves(self, field):
        """Populate a string field with the paths of selected BasisCurves prims"""
        paths = self._core.selection.get_selected_prim_paths()

        curve_prims = [
            path
            for path in paths
            if self._core.stage.GetPrimAtPath(path) and self._core.stage.GetPrimAtPath(path).IsA(UsdGeom.BasisCurves)
        ]

        field.model.set_value(", ".join(curve_prims))

    def populate_field_with_point_based(self, field):
        """Populate a string field with the paths of selected PointBased prims"""
        paths = self._core.selection.get_selected_prim_paths()

        # The section prims could be curves or other types of geometry.
        section_prims = [
            path
            for path in paths
            if self._core.stage.GetPrimAtPath(path) and self._core.stage.GetPrimAtPath(path).IsA(UsdGeom.PointBased)
        ]

        field.model.set_value(", ".join(section_prims))

    def populate_field_with_mesh(self, field):
        """Populate a string field with the paths of selected Mesh prims"""
        paths = self._core.selection.get_selected_prim_paths()

        mesh_prims = [
            path
            for path in paths
            if self._core.stage.GetPrimAtPath(path) and self._core.stage.GetPrimAtPath(path).IsA(UsdGeom.Mesh)
        ]

        field.model.set_value(", ".join(mesh_prims))

    def populate_field_with_mesh_curve(self, field):
        """Populate a string field with the path of first selected BasisCurves or Mesh prim"""
        for path in self._core.selection.get_selected_prim_paths():
            prim = self._core.stage.GetPrimAtPath(path)
            if prim and (prim.IsA(UsdGeom.Mesh) or prim.IsA(UsdGeom.BasisCurves)):
                field.model.set_value(path)
                return

    ################################################################################
    # Create curve from xformable prims
    ################################################################################
    def curve_from_xformables_clicked(self):
        def on_ok():
            graph = graph_field.model.get_value_as_string()
            xformables = xformables_field.model.get_value_as_string()

            graph = graph.strip()
            xformables = [xformable.strip() for xformable in xformables.split(",")]

            self._core.run_create_command(
                functools.partial(self._core.curve_from_xformables, graph_path=graph, xformable_paths=xformables)
            )

            window.visible = False

        def on_cancel():
            window.visible = False

        flags = ui.WINDOW_FLAGS_NO_SCROLLBAR
        window = ui.Window("Curve from Xformables", width=350, height=250, flags=flags)
        with window.frame:
            with ui.VStack(name="root", style={"VStack::root": {"margin": 10}}, height=0, spacing=10):
                with ui.VStack(name="graph selection", height=0, spacing=5):
                    ui.Label("Graph (Empty to Create New Graph):", alignment=ui.Alignment.LEFT)
                    with ui.HStack():
                        graph_field = ui.StringField()
                        ui.Button(
                            "<",
                            width=25,
                            height=25,
                            clicked_fn=functools.partial(self.populate_field_with_graph, graph_field),
                        )
                ui.Spacer()
                with ui.VStack(name="xformables selection", height=0, spacing=5):
                    ui.Label("Xformable Prims:", alignment=ui.Alignment.LEFT)
                    with ui.HStack():
                        xformables_field = ui.StringField()
                        ui.Button(
                            "<",
                            width=25,
                            height=25,
                            clicked_fn=functools.partial(self.populate_field_with_xformables, xformables_field),
                        )
                ui.Spacer()
                with ui.HStack():
                    ui.Spacer()
                    ui.Button("Ok", width=100, height=25, clicked_fn=on_ok, identifier="btn_ok")
                    ui.Spacer()
                    ui.Button("Cancel", width=100, height=25, clicked_fn=on_cancel)
                    ui.Spacer()

        # initial field values
        self.populate_field_with_graph(graph_field)
        self.populate_field_with_xformables(xformables_field)

    ################################################################################
    # Extract data from curve
    ################################################################################
    def get_curve_data_clicked(self):
        def on_ok():
            graph = graph_field.model.get_value_as_string()
            curves = curves_field.model.get_value_as_string()

            graph = graph.strip()
            curves = [curve.strip() for curve in curves.split(",")]

            self._core.run_create_command(
                functools.partial(self._core.get_curve_data, graph_path=graph, curve_paths=curves)
            )

            window.visible = False

        def on_cancel():
            window.visible = False

        flags = ui.WINDOW_FLAGS_NO_SCROLLBAR
        window = ui.Window("Get Curve Data", width=350, height=250, flags=flags)
        with window.frame:
            with ui.VStack(name="root", style={"VStack::root": {"margin": 10}}, height=0, spacing=10):
                with ui.VStack(name="graph selection", height=0, spacing=5):
                    ui.Label("Graph (Empty to Create New Graph):", alignment=ui.Alignment.LEFT)
                    with ui.HStack():
                        graph_field = ui.StringField()
                        ui.Button(
                            "<",
                            width=25,
                            height=25,
                            clicked_fn=functools.partial(self.populate_field_with_graph, graph_field),
                        )
                ui.Spacer()
                with ui.VStack(name="curves selection", height=0, spacing=5):
                    ui.Label("Curves:", alignment=ui.Alignment.LEFT)
                    with ui.HStack():
                        curves_field = ui.StringField()
                        ui.Button(
                            "<",
                            width=25,
                            height=25,
                            clicked_fn=functools.partial(self.populate_field_with_basis_curves, curves_field),
                        )
                ui.Spacer()
                with ui.HStack():
                    ui.Spacer()
                    ui.Button("Ok", width=100, height=25, clicked_fn=on_ok, identifier="btn_ok")
                    ui.Spacer()
                    ui.Button("Cancel", width=100, height=25, clicked_fn=on_cancel)
                    ui.Spacer()

        # initial field values
        self.populate_field_with_graph(graph_field)
        self.populate_field_with_basis_curves(curves_field)

    ################################################################################
    # Tag curves with ramp
    ################################################################################
    def tag_curves_with_ramp_clicked(self):
        def on_ok():
            graph = graph_field.model.get_value_as_string()
            curves = curves_field.model.get_value_as_string()

            graph = graph.strip()
            curves = [curve.strip() for curve in curves.split(",")]

            self._core.run_create_command(
                functools.partial(self._core.tag_curves_with_ramp, graph_path=graph, curve_paths=curves)
            )

            window.visible = False

        def on_cancel():
            window.visible = False

        flags = ui.WINDOW_FLAGS_NO_SCROLLBAR
        window = ui.Window("Tag Curves with Ramp", width=350, height=250, flags=flags)
        with window.frame:
            with ui.VStack(name="root", style={"VStack::root": {"margin": 10}}, height=0, spacing=10):
                with ui.VStack(name="graph selection", height=0, spacing=5):
                    ui.Label("Graph (Empty to Create New Graph):", alignment=ui.Alignment.LEFT)
                    with ui.HStack():
                        graph_field = ui.StringField()
                        ui.Button(
                            "<",
                            width=25,
                            height=25,
                            clicked_fn=functools.partial(self.populate_field_with_graph, graph_field),
                        )
                ui.Spacer()
                with ui.VStack(name="curves selection", height=0, spacing=5):
                    ui.Label("Curves:", alignment=ui.Alignment.LEFT)
                    with ui.HStack():
                        curves_field = ui.StringField()
                        ui.Button(
                            "<",
                            width=25,
                            height=25,
                            clicked_fn=functools.partial(self.populate_field_with_basis_curves, curves_field),
                        )
                ui.Spacer()
                with ui.HStack():
                    ui.Spacer()
                    ui.Button("Ok", width=100, height=25, clicked_fn=on_ok, identifier="btn_ok")
                    ui.Spacer()
                    ui.Button("Cancel", width=100, height=25, clicked_fn=on_cancel)
                    ui.Spacer()

        # initial field values
        self.populate_field_with_graph(graph_field)
        self.populate_field_with_basis_curves(curves_field)

    ################################################################################
    # Resample curves
    ################################################################################
    def resample_curves_clicked(self):
        def on_ok():
            graph = graph_field.model.get_value_as_string()
            curves = curves_field.model.get_value_as_string()

            graph = graph.strip()
            curves = [curve.strip() for curve in curves.split(",")]

            self._core.run_create_command(
                functools.partial(self._core.resample_curves, graph_path=graph, curve_paths=curves)
            )

            window.visible = False

        def on_cancel():
            window.visible = False

        flags = ui.WINDOW_FLAGS_NO_SCROLLBAR
        window = ui.Window("Resample Curves", width=350, height=250, flags=flags)
        with window.frame:
            with ui.VStack(name="root", style={"VStack::root": {"margin": 10}}, height=0, spacing=10):
                with ui.VStack(name="graph selection", height=0, spacing=5):
                    ui.Label("Graph (Empty to Create New Graph):", alignment=ui.Alignment.LEFT)
                    with ui.HStack():
                        graph_field = ui.StringField()
                        ui.Button(
                            "<",
                            width=25,
                            height=25,
                            clicked_fn=functools.partial(self.populate_field_with_graph, graph_field),
                        )
                ui.Spacer()
                with ui.VStack(name="curves selection", height=0, spacing=5):
                    ui.Label("Curves:", alignment=ui.Alignment.LEFT)
                    with ui.HStack():
                        curves_field = ui.StringField()
                        ui.Button(
                            "<",
                            width=25,
                            height=25,
                            clicked_fn=functools.partial(self.populate_field_with_basis_curves, curves_field),
                        )
                ui.Spacer()
                with ui.HStack():
                    ui.Spacer()
                    ui.Button("Ok", width=100, height=25, clicked_fn=on_ok, identifier="btn_ok")
                    ui.Spacer()
                    ui.Button("Cancel", width=100, height=25, clicked_fn=on_cancel)
                    ui.Spacer()

        # initial field values
        self.populate_field_with_graph(graph_field)
        self.populate_field_with_basis_curves(curves_field)
