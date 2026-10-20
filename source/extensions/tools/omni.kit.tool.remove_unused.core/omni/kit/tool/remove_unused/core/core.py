# * Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
# *
# * NVIDIA CORPORATION and its licensors retain all intellectual property
# * and proprietary rights in and to this software, related documentation
# * and any modifications thereto.  Any use, reproduction, disclosure or
# * distribution of this software and related documentation without an express
# * license agreement from NVIDIA CORPORATION is strictly prohibited.

import omni.usd
from pxr import Usd, UsdGeom, UsdShade


class RemoveUnusedCore:
    @classmethod
    def find_and_delete_mats(cls, stage):
        delete_list = cls.get_excess_materials(stage)
        cls.delete_mats(delete_list)

    @staticmethod
    def get_excess_materials(stage):
        bound_list = set()
        stage_list = set()

        def collect_relationship_targets(layer, prim_spec):
            all_material_relationship_targets = set()
            # Update relationships
            for relationship in prim_spec.relationships:
                for target in relationship.targetPathList.GetAddedOrExplicitItems():
                    target_prim = stage.GetPrimAtPath(target)
                    if target_prim and target_prim.IsA(UsdShade.Material):
                        bound_list.add(target.pathString)
            for child in prim_spec.nameChildren:
                collect_relationship_targets(layer, child)

        layer_stack = stage.GetLayerStack()
        for layer in layer_stack:
            collect_relationship_targets(layer, layer.pseudoRoot)

        for prim in stage.Traverse():
            can_remove = not omni.usd.check_ancestral(prim)
            if can_remove:
                if prim.IsA(UsdShade.Material):
                    stage_list.add(str(prim.GetPath()))

        diff = list(stage_list - bound_list)

        diff.sort()

        return diff

    @staticmethod
    def delete_mats(mat_list):
        omni.kit.commands.execute("DeletePrims", paths=mat_list)
