from typing import Callable

__all__ = ["AssetConverterContext"]


class AssetConverterContext:
    ignore_materials = False  # Don't import/export materials
    ignore_animations = False  # Don't import/export animations
    ignore_camera = False  # Don't import/export cameras
    ignore_light = False  # Don't import/export lights
    single_mesh = False  # By default, instanced props will be export as single USD for reference. If
    # this flag is true, it will export all props into the same USD without instancing.
    smooth_normals = True  # Smoothing normals, which is only for assimp backend.
    export_preview_surface = False  # Imports material as UsdPreviewSurface instead of MDL for USD export
    support_point_instancer = False  # Deprecated
    embed_mdl_in_usd = True  # Deprecated.
    use_meter_as_world_unit = False  # Sets world units to meters, this will also scale asset if it's centimeters model.
    create_world_as_default_root_prim = True  # Creates /World as the root prim for Kit needs.
    embed_textures = True  # Embedding textures into output. This is only enabled for FBX and glTF export.
    convert_fbx_to_y_up = False  # Always use Y-up for fbx import.
    convert_fbx_to_z_up = False  # Always use Z-up for fbx import.
    keep_all_materials = False  # If it's to remove non-referenced materials.
    merge_all_meshes = False  # Merges all meshes to single one if it can.
    use_double_precision_to_usd_transform_op = False  # Uses double precision for all transform ops.
    ignore_pivots = False  # Don't export pivots if assets support that.
    disabling_instancing = False  # Don't export instancing assets with instanceable flag.
    export_hidden_props = False  # By default, only visible props will be exported from USD exporter.
    baking_scales = False  # Only for FBX. It's to bake scales into meshes.
    ignore_flip_rotations = False  # Don't ignore animation's flip rotation value.
    ignore_unbound_bones = False  # Only for FBX. Don't ignore unbound bones.
    bake_mdl_material = False  # Bake mdl material when export
    export_separate_gltf = False  # Export gltf with separate bin file if true, else export one standalone gltf.
    export_mdl_gltf_extension = False  # Only for glTF. Export materials as NV_materials_mdl extension materials.
    convert_stage_up_y = False  # Set stage up-axis to y-up.
    convert_stage_up_z = False  # Set stage up-axis to z-up.

    def to_dict(self):
        return {
            "ignore_materials": self.ignore_materials,
            "ignore_animations": self.ignore_animations,
            "ignore_camera": self.ignore_camera,
            "ignore_light": self.ignore_light,
            "single_mesh": self.single_mesh,
            "smooth_normals": self.smooth_normals,
            "export_preview_surface": self.export_preview_surface,
            "support_point_instancer": self.support_point_instancer,
            "embed_mdl_in_usd": self.embed_mdl_in_usd,
            "use_meter_as_world_unit": self.use_meter_as_world_unit,
            "create_world_as_default_root_prim": self.create_world_as_default_root_prim,
            "embed_textures": self.embed_textures,
            "convert_fbx_to_y_up": self.convert_fbx_to_y_up,
            "convert_fbx_to_z_up": self.convert_fbx_to_z_up,
            "keep_all_materials": self.keep_all_materials,
            "merge_all_meshes": self.merge_all_meshes,
            "use_double_precision_to_usd_transform_op": self.use_double_precision_to_usd_transform_op,
            "ignore_pivots": self.ignore_pivots,
            "disabling_instancing": self.disabling_instancing,
            "export_hidden_props": self.export_hidden_props,
            "baking_scales": self.baking_scales,
            "ignore_flip_rotations": self.ignore_flip_rotations,
            "ignore_unbound_bones": self.ignore_unbound_bones,
            "bake_material": self.bake_mdl_material,
            "export_separate_gltf": self.export_separate_gltf,
            "export_mdl_gltf_extension": self.export_mdl_gltf_extension,
            "convert_stage_up_y": self.convert_stage_up_y,
            "convert_stage_up_z": self.convert_stage_up_z,
        }
