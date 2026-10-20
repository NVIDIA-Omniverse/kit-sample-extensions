# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
__all__ = ["VisualSensorCapabilityChecker"]

from dataclasses import dataclass, field

from omni.asset_validator.core import (
    BaseRuleChecker,
    is_omni_path,
)
from pxr import Usd, UsdGeom, UsdShade

from ._rule_checker_utils import validate_stage_default_prim


@dataclass
class SimPbrAttributesInfo:
    opacity: bool = field(default=False)
    retroreflection: bool = field(default=False)
    emissive: bool = field(default=False)


class VisualSensorCapabilityChecker(BaseRuleChecker):
    """
    Validates the following component visual sensor requirements rules in the AV Sim Specification: Creators

    - **3.0.C0.00**:

      The ``defaultPrim`` for the asset must be Xformable.

    - **3.0.C0.02: Geometry for Glass**

      Objects that represent glass, transparent surfaces, retroreflective materials, and emissive elements must be created as their own separate geometry prims (no ``GeomSubsets`` allowed).

    - **3.0.C0.03: Material Assignment**

      Every geometry prim with a computed purpose of "default" or "render" should have at least one computed visual material binding with a material purpose of "full".
    """

    def CheckStage(self, stage: Usd.Stage):
        validate_stage_default_prim(self, stage)

    def CheckPrim(self, prim: Usd.Prim):
        """
        Overwrites BaseRuleChecker.CheckPrim.
        """
        # Skip Omniverse specific prims
        if is_omni_path(prim.GetPath()):
            return
        # Skips non-GPrims and "non-renderable" prims such as proxies
        # This also skips GeomSubsets, because they are not GPrims
        # We will inspect GeomSubsets later as we check the GPrim
        if not UsdGeom.Gprim(prim) or not self._has_default_or_renderable_purpose(prim):
            return
        self._check_materials(prim)

    def _check_materials(self, prim: Usd.Prim):
        """
        All defined Gprims with computed purpose of 'render' or 'default' must have a computed 'full' purposed material specified.
        This validator does not propose a fix.

        If a GPrim does not have GeomSubsets, the formalized rule described in the class doc applies to it
        If a GPrim has GeomSubsets with materials, the formalized rule applies to those materials as they
        override the GPrim's material.
        If a GPrim has GeomSubsets, but has no materials, the GeomSubsets with materials need to cover the entire mesh.
        Note: In practice only Meshes have GeomSubsets

        Geometry for Glass - Objects that represent glass, transparent surfaces, retroreflective materials,
        and emissive elements must be created as their own separate geometry prims
        """
        prim_material, _ = self._get_material(prim)

        mtl_binding_api: UsdShade.MaterialBindingAPI = UsdShade.MaterialBindingAPI(prim)
        geom_subsets: list[UsdGeom.Subset] = mtl_binding_api.GetMaterialBindSubsets() or []
        if not geom_subsets:
            self._check_material(prim, prim_material)
        else:
            # If the GPrim has materials, its geomsubsets that have no materials will inherit it,
            # while whose that have materials will override it. So we will check the GPrim's
            # materials for conformance only if there are geomsubsets that have no materials, or
            # if the geomsubsets do not make up the entire mesh.

            # Check the materials of each geomsubset
            geom_subsets_without_materials: list[UsdGeom.Subset] = []
            geom_subsets_with_materials: list[UsdGeom.Subset] = []

            for geom_subset in geom_subsets:
                geomsubset_material, _ = self._get_material(geom_subset)
                if geomsubset_material:
                    self._check_material(geom_subset, geomsubset_material)
                    self._check_opacity_retroreflection_emissive(geom_subset, geomsubset_material)
                    geom_subsets_with_materials.append(geom_subset)
                else:
                    geom_subsets_without_materials.append(geom_subset)

            # Check the materials on the prim
            if not self._geomsubsets_make_up_entire_mesh(prim, geom_subsets):
                self._check_material(prim, prim_material, additional_msg="There are faces without material")

            # If the prim has no materials, the geomsubsets with materials need to cover the entire mesh
            # otherwise there will be faces without materials.
            if not prim_material:
                for gs in geom_subsets_without_materials:
                    self._AddFailedCheck(
                        message=f"GeomSubset {gs.GetPrim().GetPath()} has no materials and the GPrim {prim.GetPath()} has no materials",
                        at=gs.GetPrim(),
                    )
            # If any geomsubsets using inherited material, check the inherited material has opacity, retroreflection and emissive.
            elif geom_subsets_without_materials:
                self._check_opacity_retroreflection_emissive(prim, prim_material)

    @staticmethod
    def _get_material(
        prim_or_geom_subset: Usd.Prim | UsdGeom.Subset,
    ) -> tuple[UsdShade.Material, Usd.Relationship]:
        """Returns the computed "full" purpose material and the relationship of the prim/geomSubset."""
        return UsdShade.MaterialBindingAPI(prim_or_geom_subset).ComputeBoundMaterial(
            materialPurpose=UsdShade.Tokens.full
        )

    @staticmethod
    def _is_input_attr_enabled(shader: UsdShade.Shader, attr_name: str) -> bool:
        """Check if the given input of the given shader is enabled in any time samples."""
        attr_shader_input = shader.GetInput(attr_name)
        if not attr_shader_input:
            return False
        attr = attr_shader_input.GetAttr()
        time_samples = attr.GetTimeSamples() or [Usd.TimeCode.EarliestTime()]
        return any(attr.Get(time) for time in time_samples)

    @staticmethod
    def _get_mdl_surface_shader(material: UsdShade.Material) -> UsdShade.Shader | None:
        # An MDL is authored to either the mdl render context OR if and only if the mdl render context is unauthored,
        # the universal render context
        surface_output = material.GetSurfaceOutput("mdl") or material.GetSurfaceOutput()
        if not surface_output:
            return
        connection_source = surface_output.GetConnectedSource()
        if not connection_source:
            return

        shader = UsdShade.Shader(connection_source[0])
        return shader if shader.GetSourceAsset("mdl") and shader.GetSourceAsset("mdl").path.endswith(".mdl") else None

    @staticmethod
    def _get_usd_preview_surface_shader(material: UsdShade.Material) -> UsdShade.Shader | None:
        surface_output = material.GetSurfaceOutput()
        if not surface_output:
            return
        connection_source = surface_output.GetConnectedSource()
        if not connection_source:
            return

        shader = UsdShade.Shader(connection_source[0])
        return shader if shader.GetIdAttr().Get() == "UsdPreviewSurface" else None

    def _get_sim_pbr_shader_info(self, material: UsdShade.Material) -> SimPbrAttributesInfo:
        """Check the surface shader of the given material if its a sim pbr shader (SimPBR, SimPBR_Translucent, SimGlassPBR)
        and has opacity, retroreflection, emissive enabled."""

        sim_pbr_attribute_info = SimPbrAttributesInfo()
        shader = self._get_mdl_surface_shader(material)
        if not shader:
            return sim_pbr_attribute_info

        if shader.GetSourceAsset("mdl").path not in (
            "OmniGlass.mdl",
            "OmniPBR.mdl",
            "SimPBR.mdl",
            "SimPBR_Translucent.mdl",
        ):
            return sim_pbr_attribute_info

        sim_pbr_attribute_info.opacity = self._is_input_attr_enabled(shader, "enable_opacity")
        sim_pbr_attribute_info.retroreflection = self._is_input_attr_enabled(shader, "enable_retroreflection")
        sim_pbr_attribute_info.emissive = self._is_input_attr_enabled(shader, "enable_emission")
        return sim_pbr_attribute_info

    def _check_material(
        self,
        prim_or_schema_base: Usd.Prim | Usd.SchemaBase,
        material: UsdShade.Material,
        additional_msg: str = "",
    ):
        """Add failure if given 'material' is not valid."""
        prim: Usd.Prim = prim_or_schema_base.GetPrim()
        if not material:
            self._AddFailedCheck(
                message=f"No materials found on prim {prim.GetPath()}. {additional_msg}",
                at=prim,
            )
            return

        mdl_shader = self._get_mdl_surface_shader(material)
        ups_shader = self._get_usd_preview_surface_shader(material)
        if not mdl_shader and not ups_shader:
            self._AddFailedCheck(
                message=(
                    "SimReady requires that the surface shader is MDL (in either the material's universal or MDL render context) or "
                    "UsdPreviewSurface (in the material's universal render context only)."
                ),
                at=material.GetPrim(),
            )
            return

    def _check_opacity_retroreflection_emissive(
        self, prim_or_schema_base: Usd.Prim | Usd.SchemaBase, material: UsdShade.Material
    ):
        """Add failure if given 'material' has opacity, retroreflection or emissive enabled."""
        prim: Usd.Prim = prim_or_schema_base.GetPrim()
        sim_pbr_shader_info = self._get_sim_pbr_shader_info(material)
        if any((sim_pbr_shader_info.opacity, sim_pbr_shader_info.retroreflection, sim_pbr_shader_info.emissive)):
            message = (
                f"{'opacity ' if sim_pbr_shader_info.opacity else ''}"
                f"{'retroreflection ' if sim_pbr_shader_info.retroreflection else ''}"
                f"{'emissive ' if sim_pbr_shader_info.emissive else ''}"
            )
            message = (
                f"AVSimReady asset requires geomSubset '{prim.GetPath()}' with the computed material '{material.GetPath()}' "
                f"that has {message}enabled to be separate Gprims."
            )
            self._AddFailedCheck(message=message, at=prim)

    def _geomsubsets_make_up_entire_mesh(self, prim: Usd.Prim, geom_subsets: list[UsdGeom.Subset]) -> bool:
        """
        Returns True if the GeomSubsets of the prim make up the entire mesh, i.e.
        if the sorted face ids of the geomsubsets == range(0, numfaces of the mesh)
        """
        if not geom_subsets:
            return False
        mesh: UsdGeom.Mesh = UsdGeom.Mesh(prim)
        if not mesh:
            return False
        # Create a list with a boolean for each face of the mesh
        # If a face is used by a geomsubset, the corresponding index in the list is set to True
        # TODO: We need to likely do some thinking about time varying-ness for this.
        mesh_face_count = mesh.GetFaceCount(timeCode=Usd.TimeCode.Default())
        indices_used = [False] * mesh_face_count
        for geom_subset in geom_subsets:
            indices_attr = geom_subset.GetIndicesAttr()

            if indices_attr.GetTimeSamples():
                self._AddFailedCheck(
                    message=f"GeomSubset {geom_subset.GetPrim().GetPath()} has time sampled indices. Validation not supported.",
                    at=geom_subset.GetPrim(),
                )
                return False

            if indices_attr:
                for index in indices_attr.Get():
                    try:
                        indices_used[index] = True
                    except IndexError:
                        return False
        # Unless all faces are used by the geomsubsets, return False
        return all(indices_used)

    @staticmethod
    def _has_default_or_renderable_purpose(prim: Usd.Prim) -> bool:
        """Returns True if the prim is Imageable with default or renderable purpose."""
        if not (imageable := UsdGeom.Imageable(prim)):
            return False
        purpose = imageable.ComputePurpose()
        return purpose in (UsdGeom.Tokens.default_, UsdGeom.Tokens.render)
