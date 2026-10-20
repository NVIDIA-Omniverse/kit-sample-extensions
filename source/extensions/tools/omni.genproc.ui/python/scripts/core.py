import functools
from typing import Callable, List

import carb
import omni.graph.core as ogc
import omni.kit
import omni.usd
from pxr import Sdf, Usd, UsdGeom


class Core:
    def __init__(self):
        super().__init__()
        self.context = None
        self.stage = None
        self.selection = None
        self.sub_stage_update = None

    def on_startup(self):
        self.context = omni.usd.get_context()
        self.selection = self.context.get_selection()
        self.sub_stage_update = self.context.get_stage_event_stream().create_subscription_to_pop(self.on_stage_update)
        self.on_stage_update()

    def on_shutdown(self):
        self.sub_stage_update = None

    def on_stage_update(self, dt=None):
        self.stage = self.context.get_stage()

    def run_create_command(self, callback: Callable) -> None:
        omni.kit.commands.execute("CreateGenProcEntityCommand", callback=functools.partial(callback))

    ################################################################################
    # Create curve from xformable prims
    ################################################################################
    def curve_from_xformables(self, graph_path: str, xformable_paths: List[str]) -> List[str]:
        created_paths = []

        xformable_prims = [
            self.stage.GetPrimAtPath(path)
            for path in xformable_paths
            if self.stage.GetPrimAtPath(path) and self.stage.GetPrimAtPath(path).IsA(UsdGeom.Xformable)
        ]

        if graph_path == "":
            graph = self.create_compute_graph(created_paths)
            graph_path = graph.get_path_to_graph()
        else:
            graph = ogc.get_graph_by_path(graph_path)
            if not graph:
                carb.log_error("Invalid path provided for input graph.")
                return created_paths

        parent_path = graph.get_path_to_graph()

        # Import node(s)
        import_node_path = omni.usd.get_stage_next_free_path(self.stage, f"{parent_path}/import", False)
        callback = functools.partial(
            graph.create_node,
            import_node_path,
            "omni.graph.nodes.ReadPrimsV2",
            True,
        )
        self.create_node(import_node_path, callback, created_paths)
        import_node = self.stage.GetPrimAtPath(import_node_path)

        # Connect prims to import node
        for prim in xformable_prims:
            self.create_relationship(
                prim,
                import_node,
                property_name="inputs:prims",
            )

        # TransformsToCurve node
        transforms_to_curve_path = omni.usd.get_stage_next_free_path(
            self.stage, f"{parent_path}/transforms_to_curve", False
        )
        callback = functools.partial(
            graph.create_node,
            transforms_to_curve_path,
            "omni.genproc.core.TransformsToCurve",
            True,
        )
        self.create_node(transforms_to_curve_path, callback, created_paths)
        self.connect_bundle_attributes(
            graph, f"{import_node_path}.outputs:primsBundle", f"{transforms_to_curve_path}.inputs:transformBundle"
        )

        # Visualize result
        curve_visualizer_path = omni.usd.get_stage_next_free_path(self.stage, f"{parent_path}/curve_visualizer", False)
        callback = functools.partial(
            graph.create_node,
            curve_visualizer_path,
            "omni.scene.visualization.core.CurveVisualizer",
            True,
        )
        self.create_node(curve_visualizer_path, callback, created_paths)
        self.connect_bundle_attributes(
            graph, f"{transforms_to_curve_path}.outputs:curveBundle", f"{curve_visualizer_path}.inputs:curveBundle"
        )

        return created_paths

    ################################################################################
    # Extract data from curve
    ################################################################################
    def get_curve_data(self, graph_path: str, curve_paths: List[str]) -> List[str]:
        created_paths = []

        curve_prims = [
            self.stage.GetPrimAtPath(path)
            for path in curve_paths
            if self.stage.GetPrimAtPath(path) and self.stage.GetPrimAtPath(path).IsA(UsdGeom.BasisCurves)
        ]

        if len(curve_prims) == 0:
            carb.log_error("At least one BasisCurves prim must be provided.")
            return created_paths

        if graph_path == "":
            graph = self.create_compute_graph(created_paths)
            graph_path = graph.get_path_to_graph()
        else:
            graph = ogc.get_graph_by_path(graph_path)
            if not graph:
                carb.log_error("Invalid path provided for input graph.")
                return created_paths

        parent_path = graph.get_path_to_graph()

        # Import node(s)
        import_node_path = omni.usd.get_stage_next_free_path(self.stage, f"{parent_path}/import", False)
        callback = functools.partial(
            graph.create_node,
            import_node_path,
            "omni.graph.nodes.ReadPrimsV2",
            True,
        )
        self.create_node(import_node_path, callback, created_paths)
        import_node = self.stage.GetPrimAtPath(import_node_path)

        # Connect prims to import node
        for prim in curve_prims:
            self.create_relationship(
                prim,
                import_node,
                property_name="inputs:prims",
            )

        # GetCurveData node
        get_curve_data_path = omni.usd.get_stage_next_free_path(self.stage, f"{parent_path}/get_curve_data", False)
        callback = functools.partial(
            graph.create_node,
            get_curve_data_path,
            "omni.genproc.core.GetCurveData",
            True,
        )
        self.create_node(get_curve_data_path, callback, created_paths)
        self.connect_bundle_attributes(
            graph, f"{import_node_path}.outputs:primsBundle", f"{get_curve_data_path}.inputs:curvesBundle"
        )

        # Visualize result
        point_visualizer_path = omni.usd.get_stage_next_free_path(self.stage, f"{parent_path}/point_visualizer", False)
        callback = functools.partial(
            graph.create_node,
            point_visualizer_path,
            "omni.scene.visualization.core.PointVisualizer",
            True,
        )
        self.create_node(point_visualizer_path, callback, created_paths)
        graph.get_node(get_curve_data_path).get_attribute("outputs:points").connect(
            graph.get_node(point_visualizer_path).get_attribute("inputs:points"), True
        )
        graph.get_node(get_curve_data_path).get_attribute("outputs:tangents").connect(
            graph.get_node(point_visualizer_path).get_attribute("inputs:aims"), True
        )

        return created_paths

    ################################################################################
    # Tag curves with ramp
    ################################################################################
    def tag_curves_with_ramp(self, graph_path: str, curve_paths: List[str]) -> List[str]:
        created_paths = []

        curve_prims = [
            self.stage.GetPrimAtPath(path)
            for path in curve_paths
            if self.stage.GetPrimAtPath(path) and self.stage.GetPrimAtPath(path).IsA(UsdGeom.BasisCurves)
        ]

        if len(curve_prims) == 0:
            carb.log_error("At least one BasisCurves prim must be provided.")
            return created_paths

        if graph_path == "":
            graph = self.create_compute_graph(created_paths)
            graph_path = graph.get_path_to_graph()
        else:
            graph = ogc.get_graph_by_path(graph_path)
            if not graph:
                carb.log_error("Invalid path provided for input graph.")
                return created_paths

        parent_path = graph.get_path_to_graph()

        # Import node(s)
        import_node_path = omni.usd.get_stage_next_free_path(self.stage, f"{parent_path}/import", False)
        callback = functools.partial(
            graph.create_node,
            import_node_path,
            "omni.graph.nodes.ReadPrimsV2",
            True,
        )
        self.create_node(import_node_path, callback, created_paths)
        import_node = self.stage.GetPrimAtPath(import_node_path)

        # Connect prims to import node
        for prim in curve_prims:
            self.create_relationship(
                prim,
                import_node,
                property_name="inputs:prims",
            )

        # Tag node
        tag_curve_path = omni.usd.get_stage_next_free_path(self.stage, f"{parent_path}/tag_curves", False)
        callback = functools.partial(
            graph.create_node,
            tag_curve_path,
            "omni.genproc.core.TagPrimsFromRamp",
            True,
        )
        self.create_node(tag_curve_path, callback, created_paths)
        self.connect_bundle_attributes(
            graph, f"{import_node_path}.outputs:primsBundle", f"{tag_curve_path}.inputs:bundle"
        )

        # GetCurveData node
        get_curve_data_path = omni.usd.get_stage_next_free_path(self.stage, f"{parent_path}/get_curve_data", False)
        callback = functools.partial(
            graph.create_node,
            get_curve_data_path,
            "omni.genproc.core.GetCurveData",
            True,
        )
        self.create_node(get_curve_data_path, callback, created_paths)
        self.connect_bundle_attributes(
            graph, f"{tag_curve_path}.outputs:bundle", f"{get_curve_data_path}.inputs:curvesBundle"
        )

        # Visualize result
        point_visualizer_path = omni.usd.get_stage_next_free_path(self.stage, f"{parent_path}/point_visualizer", False)
        callback = functools.partial(
            graph.create_node,
            point_visualizer_path,
            "omni.scene.visualization.core.PointVisualizer",
            True,
        )
        self.create_node(point_visualizer_path, callback, created_paths)
        graph.get_node(get_curve_data_path).get_attribute("outputs:points").connect(
            graph.get_node(point_visualizer_path).get_attribute("inputs:points"), True
        )
        graph.get_node(get_curve_data_path).get_attribute("outputs:tangents").connect(
            graph.get_node(point_visualizer_path).get_attribute("inputs:aims"), True
        )
        graph.get_node(get_curve_data_path).get_attribute("outputs:tags").connect(
            graph.get_node(point_visualizer_path).get_attribute("inputs:tags"), True
        )

        return created_paths

    ################################################################################
    # Resample curves
    ################################################################################
    def resample_curves(self, graph_path: str, curve_paths: List[str]) -> List[str]:
        created_paths = []

        curve_prims = [
            self.stage.GetPrimAtPath(path)
            for path in curve_paths
            if self.stage.GetPrimAtPath(path) and self.stage.GetPrimAtPath(path).IsA(UsdGeom.BasisCurves)
        ]

        if len(curve_prims) == 0:
            carb.log_error("At least one BasisCurves prim must be provided.")
            return created_paths

        if graph_path == "":
            graph = self.create_compute_graph(created_paths)
            graph_path = graph.get_path_to_graph()
        else:
            graph = ogc.get_graph_by_path(graph_path)
            if not graph:
                carb.log_error("Invalid path provided for input graph.")
                return created_paths

        parent_path = graph.get_path_to_graph()

        # Import node(s)
        import_node_path = omni.usd.get_stage_next_free_path(self.stage, f"{parent_path}/import", False)
        callback = functools.partial(
            graph.create_node,
            import_node_path,
            "omni.graph.nodes.ReadPrimsV2",
            True,
        )
        self.create_node(import_node_path, callback, created_paths)
        import_node = self.stage.GetPrimAtPath(import_node_path)

        # Connect prims to import node
        for prim in curve_prims:
            self.create_relationship(
                prim,
                import_node,
                property_name="inputs:prims",
            )

        # Resample node
        resample_path = omni.usd.get_stage_next_free_path(self.stage, f"{parent_path}/resample_curves", False)
        callback = functools.partial(
            graph.create_node,
            resample_path,
            "omni.genproc.core.ResampleCurves",
            True,
        )
        self.create_node(resample_path, callback, created_paths)
        self.connect_bundle_attributes(
            graph, f"{import_node_path}.outputs:primsBundle", f"{resample_path}.inputs:curvesBundle"
        )

        # Visualize result
        curve_visualizer_path = omni.usd.get_stage_next_free_path(self.stage, f"{parent_path}/curve_visualizer", False)
        callback = functools.partial(
            graph.create_node,
            curve_visualizer_path,
            "omni.scene.visualization.core.CurveVisualizer",
            True,
        )
        self.create_node(curve_visualizer_path, callback, created_paths)
        self.connect_bundle_attributes(
            graph, f"{resample_path}.outputs:curvesBundle", f"{curve_visualizer_path}.inputs:curveBundle"
        )

        return created_paths

    ################################################################################
    # Utils
    ################################################################################
    def create_node(self, path: str, callback: Callable, created_paths: List[str]):
        new_node = False
        prim = self.stage.GetPrimAtPath(path)
        if not prim.IsValid():
            new_node = True
        result = callback()
        if new_node:
            created_paths.append(path)
        return result

    def create_compute_graph(self, created_paths=None):

        default_prim = self.stage.GetDefaultPrim()
        parent_path = f"{str(default_prim.GetPath())}/OmniGraph" if default_prim else "/OmniGraph"
        if not self.stage.GetPrimAtPath(parent_path):
            scope = self.stage.DefinePrim(parent_path, "Scope")
            if created_paths is not None:
                created_paths.append(parent_path)

        graph_path = Sdf.Path(f"{parent_path}/PushGraph").MakeAbsolutePath(Sdf.Path.absoluteRootPath)
        graph_path = omni.usd.get_stage_next_free_path(self.stage, graph_path, True)

        container_graphs = ogc.get_global_container_graphs()
        # FIXME: container_graphs[0] should be the simulation orchestration graph, but this may change in the future.
        container_graph = container_graphs[0]
        result, wrapper_node = ogc.cmds.CreateGraphAsNode(
            graph=container_graph,
            node_name=Sdf.Path(graph_path).name,
            graph_path=graph_path,
            evaluator_name="push",
            is_global_graph=True,
            backed_by_usd=True,
            fc_backing_type=ogc.GraphBackingType.GRAPH_BACKING_TYPE_FLATCACHE_SHARED,
            pipeline_stage=ogc.GraphPipelineStage.GRAPH_PIPELINE_STAGE_SIMULATION,
        )
        graph = wrapper_node.get_wrapped_graph()

        if created_paths is not None:
            created_paths.append(graph.get_path_to_graph())

        return graph

    def create_scope(self, name):
        scope = UsdGeom.Scope.Define(self.stage, name)
        return scope

    def create_point_instancer(self, name):
        prim = self.stage.DefinePrim(name, "PointInstancer")
        pointInstancer = UsdGeom.PointInstancer(prim)

        # OM-29517
        # UsdImagingPointInstancerAdapter requires point instancers to
        # have authored protoIndices and positions upon creation.
        # We can revisit this after we have replaced UsdImaging entirely
        # within OmniImagingDelegate.
        pointInstancer.CreateOrientationsAttr([])
        pointInstancer.CreatePositionsAttr([])
        pointInstancer.CreateProtoIndicesAttr([])
        pointInstancer.CreateScalesAttr([])

        pointInstancer.AddRotateXYZOp(UsdGeom.XformOp.PrecisionDouble)
        pointInstancer.AddScaleOp(UsdGeom.XformOp.PrecisionDouble)
        pointInstancer.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble)
        pointInstancer.CreateXformOpOrderAttr(["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"])

        prim.CreateAttribute("node:type", Sdf.ValueTypeNames.Token).Set("omni.graph.core.Prim")

        return pointInstancer

    def create_mesh(self, name):
        prim = self.stage.DefinePrim(name, "Mesh")
        mesh = UsdGeom.Mesh(prim)

        mesh.AddRotateXYZOp(UsdGeom.XformOp.PrecisionDouble)
        mesh.AddScaleOp(UsdGeom.XformOp.PrecisionDouble)
        mesh.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble)
        mesh.CreateXformOpOrderAttr(["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"])

        prim.CreateAttribute("node:type", Sdf.ValueTypeNames.Token).Set("omni.graph.core.Prim")

        return mesh

    def create_sprite(self, name):
        prim = self.stage.DefinePrim(name, "Mesh")
        sprite = UsdGeom.Mesh(prim)
        sprite.CreateSubdivisionSchemeAttr("none")
        sprite.CreateTriangleSubdivisionRuleAttr("none")
        sprite.CreateFaceVertexCountsAttr([3, 3])
        sprite.CreateFaceVertexIndicesAttr([0, 1, 2, 0, 2, 3])
        normals = sprite.CreateNormalsAttr([(0, 1, 0), (0, 1, 0), (0, 1, 0), (0, 1, 0), (0, 1, 0), (0, 1, 0)])
        sprite.SetNormalsInterpolation("faceVarying")
        sprite.CreatePointsAttr([(0.5, 0, -0.5), (-0.5, 0, -0.5), (-0.5, 0, 0.5), (0.5, 0, 0.5)])

        st = sprite.CreatePrimvar("primvars:st", Sdf.ValueTypeNames.Float2Array, "faceVarying")
        st.Set([(1, 1), (0, 1), (0, 0), (1, 1), (0, 0), (1, 0)])
        st.CreateIndicesAttr().Set([0, 1, 2, 3, 4, 5])
        st2 = sprite.CreatePrimvar("primvars:st2", Sdf.ValueTypeNames.Float2Array, "faceVarying")
        st2.Set([(1, 1), (1, 1), (1, 1), (1, 1), (1, 1), (1, 1)])
        st3 = sprite.CreatePrimvar("primvars:st3", Sdf.ValueTypeNames.Float2Array, "faceVarying")
        st3.Set([(1, 1), (1, 1), (1, 1), (1, 1), (1, 1), (1, 1)])

        sprite.AddRotateXYZOp(UsdGeom.XformOp.PrecisionDouble)
        sprite.AddScaleOp(UsdGeom.XformOp.PrecisionDouble)
        sprite.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble)
        sprite.CreateXformOpOrderAttr(["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"])

        prim.CreateAttribute("node:type", Sdf.ValueTypeNames.Token).Set("omni.graph.core.Prim")

        return sprite

    def get_compute_graph(self, selected_paths, create_new_graph=True, created_paths=None):
        """
        Returns the first ComputeGraph/OmniGraph found in selected_paths.
        If no graph is found and create_new_graph is true, a new graph will be created and its
        path appended to created_paths (if provided).
        """
        graph = None
        graph_paths = [
            path
            for path in selected_paths
            if self.stage.GetPrimAtPath(path).GetTypeName() in ["ComputeGraph", "OmniGraph"]
        ]

        if len(graph_paths) > 0:
            graph = ogc.get_graph_by_path(graph_paths[0])
            if len(graph_paths) > 1:
                carb.log_warn(
                    f"Multiple ComputeGraph/OmniGraph prims selected. Only the first will be used: {graph.get_path_to_graph()}"
                )
        elif create_new_graph:
            # If no graph was found in the selected prims, we'll make a new graph.
            graph_path = Sdf.Path("PushGraph").MakeAbsolutePath(Sdf.Path.absoluteRootPath)
            graph_path = omni.usd.get_stage_next_free_path(self.stage, graph_path, True)

            container_graphs = ogc.get_global_container_graphs()
            # FIXME: container_graphs[0] should be the simulation orchestration graph, but this may change in the future.
            container_graph = container_graphs[0]

            # FIXME 2: undo is broken here. Invoking menu options with an existing graph works fine with undo/redo,
            # but if a new graph is created then we can carb error messages upon undo...
            with omni.kit.undo.group():
                result, wrapper_node = ogc.cmds.CreateGraphAsNode(
                    graph=container_graph,
                    node_name=Sdf.Path(graph_path).name,
                    graph_path=graph_path,
                    evaluator_name="push",
                    is_global_graph=True,
                    backed_by_usd=True,
                    fc_backing_type=ogc.GraphBackingType.GRAPH_BACKING_TYPE_FLATCACHE_SHARED,
                    pipeline_stage=ogc.GraphPipelineStage.GRAPH_PIPELINE_STAGE_SIMULATION,
                )
            graph = wrapper_node.get_wrapped_graph()

            if created_paths is not None:
                created_paths.append(graph.get_path_to_graph())

            carb.log_info(
                f"No ComputeGraph/OmniGraph selected. A new graph has been created at {graph.get_path_to_graph()}"
            )

        return graph

    def get_node(self, graph, input):
        if graph.is_valid():
            if type(input) == Usd.Prim:
                return graph.get_node(input.GetPath().pathString)
            elif type(input) == str:
                return graph.get_node(input)
        return None

    def create_relationship(self, source_prim, target_prim, property_name):
        rel = target_prim.CreateRelationship(property_name)
        rel.AddTarget(source_prim.GetPath().pathString)
        return rel

    def connect_bundle_attributes(self, graph, source, target):
        # If the "source" path is of type /path/to/prim.inputs:attr_name we can say with high-enough
        # confidence that it represents OG node.attr and we can assemble a corresponding bundle_prim_path
        # from it.
        # Otherwise treat it as a /path/to/prim pointing to an USD prim in the stage.
        if "." in source:
            prim_path, attr_name = source.split(".")
            source = prim_path + "/" + attr_name.replace(":", "_")
        else:
            # THIS SHOULD BE DEPRECATED AT SOME POINT LATER ONCE WE GET OFF THE OGN PRIM WORKFLOW !!!

            # Create OgnPrim node for the given USD prim, if not there.
            if not self.get_node(graph, source).is_valid():
                ogc.cmds.CreateNode(graph=graph, node_path=source, node_type="omni.graph.core.Prim", create_usd=True)

        prim_path, attr_name = target.split(".")
        target = self.get_node(graph, prim_path).get_attribute(attr_name)
        if target.is_valid():
            ogc.cmds.ConnectPrim(attr=target, prim_path=source, is_bundle_connection=True)
