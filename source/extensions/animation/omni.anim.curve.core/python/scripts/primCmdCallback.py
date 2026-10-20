import functools
import weakref

import omni.graph.core as og
import omni.kit.commands as kit_cmds
import omni.usd
from pxr import Sdf, Usd

from . import utils


class PrimCmdCallback:
    def __init__(self):
        self._callback_ids = []
        callback_id = kit_cmds.register_callback(
            "CopyPrim",
            kit_cmds.POST_DO_CALLBACK,
            functools.partial(__class__._on_copy_prim_cmd_do, weakref.proxy(self)),
        )
        self._callback_ids.append(callback_id)
        callback_id = kit_cmds.register_callback(
            "DeletePrims",
            kit_cmds.POST_DO_CALLBACK,
            functools.partial(__class__._on_delete_prim_cmd_do, weakref.proxy(self)),
        )
        self._callback_ids.append(callback_id)

    def __del__(self):
        for id in self._callback_ids:
            kit_cmds.unregister_callback(id)

    def _on_delete_prim_cmd_do(self, info):
        # Delete curve node and animation if target prim is deleted
        stage = omni.usd.get_context().get_stage()

        graphs = set()

        node_paths = utils.get_curve_plugin().get_curve_nodes(None)
        for node_path in node_paths:
            node_prim = stage.GetPrimAtPath(node_path)
            if not node_prim:
                continue

            # Check if the node is connected to any other nodes.
            node = og.get_node_by_path(node_path)
            if node is None:  # When timeline extension is disabled, we can't get timeline node.
                continue

            attrs = node.get_attributes()
            is_connected = False

            for attr in attrs:
                if attr.get_upstream_connection_count() + attr.get_downstream_connection_count() > 0:
                    is_connected = True
                    break

            if is_connected:
                continue

            # Check if target prim is deleted
            prim_is_deleted = False

            def get_rel_path(input_name: str):
                rel = node_prim.GetRelationship("inputs:" + input_name)
                if not rel:
                    return None

                paths = rel.GetTargets()
                if not paths:
                    return None

                return paths[0]

            for name in ["Prim"]:
                path = get_rel_path(name)
                if path is None:
                    continue

                if stage.GetPrimAtPath(path):
                    continue

                for delete_path in info["paths"]:
                    if path.HasPrefix(delete_path):
                        prim_is_deleted = True
                        break

            if not prim_is_deleted:
                continue

            graph = node.get_graph()
            graphs.add(graph)

            kit_cmds.execute("DeletePrims", paths=[node.get_prim_path()])

        # Remove empty graphs
        for graph in graphs:
            if not graph:
                continue

            prim = stage.GetPrimAtPath(graph.get_path_to_graph())
            if not prim:
                continue

            if not prim.GetAllChildren():
                kit_cmds.execute("DeletePrims", paths=[prim.GetPath()])

    def _on_copy_prim_cmd_do(self, info):
        # Duplicate animation when target prims are duplicated
        stage = omni.usd.get_context().get_stage()

        path_from = info["path_from"]
        path_to = info["path_to"]

        for prim in Usd.PrimRange(stage.GetPrimAtPath(path_from)):
            # Check if it contains animation
            curve_prims = utils.get_curve_prims(prim)
            if not curve_prims:
                continue

            # Duplicate curve node
            for curve_prim in curve_prims:
                node_paths = utils.get_curve_plugin().get_curve_nodes(prim.GetPath().pathString)
                if not node_paths:
                    continue

                # Duplicate curve nodes and redirect relationships
                dup_prim_path = prim.GetPath().ReplacePrefix(path_from, path_to)

                for node_path in node_paths:
                    if Sdf.Path(node_path).HasPrefix(path_from):  # Skip the node if it's already duplicated.
                        continue

                    dup_node_path = omni.usd.get_stage_next_free_path(stage, node_path, False)

                    kit_cmds.execute("CopyPrim", path_from=node_path, path_to=dup_node_path)

                    prim_rel = stage.GetRelationshipAtPath(dup_node_path + ".inputs:Prim")

                    kit_cmds.execute("SetRelationshipTargets", relationship=prim_rel, targets=[dup_prim_path])
