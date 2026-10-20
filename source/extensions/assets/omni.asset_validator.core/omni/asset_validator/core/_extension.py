# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from omni.asset_validator import (
    AlmostExtremeExtentChecker,
    AnchoredAssetPathsChecker,
    ArticulationChecker,
    ByteAlignmentChecker,
    CategoryRuleRegistry,
    ColliderChecker,
    CompressionChecker,
    ExtentsChecker,
    GaussianSplatSchemaChecker,
    IndexedPrimvarChecker,
    KindChecker,
    LayerSpecChecker,
    ManifoldChecker,
    MassChecker,
    MaterialOldMdlSchemaChecker,
    MaterialOutOfScopeChecker,
    MaterialPathChecker,
    MissingReferenceChecker,
    NormalMapTextureChecker,
    NormalsExistChecker,
    NormalsValidChecker,
    NormalsWindingsChecker,
    PhysicsJointChecker,
    PointsPrecisionErrorChecker,
    PointsPrecisionWarningChecker,
    PortableAssetPathChecker,
    PrimEncapsulationChecker,
    RequirementsRegistry,
    RigidBodyChecker,
    ShaderImplementationSourceChecker,
    SkelBindingAPIAppliedChecker,
    StageMetadataChecker,
    SubdivisionSchemeChecker,
    SupportedFileTypesChecker,
    TextureChecker,
    TypeChecker,
    UnicodeNameChecker,
    UnusedMeshTopologyChecker,
    UnusedPrimvarChecker,
    UsdAsciiPerformanceChecker,
    UsdDanglingMaterialBinding,
    UsdGeomSubsetChecker,
    UsdLuxSchemaChecker,
    UsdMaterialBindingApi,
    UsdzPackageValidator,
    UsdzUdimLimitationChecker,
    ValidateTopologyChecker,
    WeldChecker,
    ZeroAreaFaceChecker,
    register_capabilities,
    register_features,
    register_profiles,
    unregister_capabilities,
    unregister_features,
    unregister_profiles,
)
from omni.capabilities import Capabilities, Features, Profiles
from omni.ext import IExt
from pxr import Usd

from ._engine import ValidationRulesRegistry, registerRule
from ._omni_layout import OmniDefaultPrimChecker, OmniOrphanedPrimChecker
from ._omni_material_2211 import OmniMaterialUsdPreviewSurfaceChecker
from ._usd_skel import OmniSkelUpgradeChecker, is_omni_skel_upgrade_disabled


class CoreExtension(IExt):

    def on_startup(self, ext_id: str) -> None:
        ValidationRulesRegistry.init()
        register_capabilities(Capabilities)
        register_features(Features)
        register_profiles(Profiles)

        # AtomicAsset rules
        registerRule("AtomicAsset")(AnchoredAssetPathsChecker)
        registerRule("AtomicAsset")(SupportedFileTypesChecker)
        registerRule("AtomicAsset")(UsdzUdimLimitationChecker)

        # Basic rules
        registerRule("Basic", skip=UsdzPackageValidator.is_implemented())(ByteAlignmentChecker)
        registerRule("Basic", skip=UsdzPackageValidator.is_implemented())(CompressionChecker)
        registerRule("Basic", skip=not UsdzPackageValidator.is_implemented())(UsdzPackageValidator)
        registerRule("Basic")(MissingReferenceChecker)
        registerRule("Basic")(PortableAssetPathChecker)
        registerRule("Basic")(StageMetadataChecker)
        registerRule("Basic")(TextureChecker)
        registerRule("Basic")(PrimEncapsulationChecker)
        registerRule("Basic")(NormalMapTextureChecker)

        # Omni:Basic rules
        registerRule("Omni:Basic")(KindChecker)
        registerRule("Omni:Basic")(ExtentsChecker)
        registerRule("Omni:Basic")(TypeChecker)
        registerRule("Omni:Basic")(LayerSpecChecker)
        if Usd.GetVersion() >= (0, 24, 3):
            registerRule("Omni:Basic")(UnicodeNameChecker)

        # Usd:Performance rules
        registerRule("Usd:Performance")(AlmostExtremeExtentChecker)
        registerRule("Usd:Performance")(PointsPrecisionErrorChecker)
        registerRule("Usd:Performance")(PointsPrecisionWarningChecker)
        registerRule("Usd:Performance")(UsdAsciiPerformanceChecker)

        # Usd:Schema rules
        registerRule("Usd:Schema")(UsdDanglingMaterialBinding)
        registerRule("Usd:Schema")(UsdGeomSubsetChecker)
        registerRule("Usd:Schema")(UsdLuxSchemaChecker)
        registerRule("Usd:Schema")(UsdMaterialBindingApi)
        registerRule("Usd:Schema")(SkelBindingAPIAppliedChecker)

        # Omni:Geometry rules
        registerRule("Omni:Geometry")(IndexedPrimvarChecker)
        registerRule("Omni:Geometry")(ManifoldChecker)
        registerRule("Omni:Geometry")(NormalsExistChecker)
        registerRule("Omni:Geometry")(NormalsValidChecker)
        registerRule("Omni:Geometry")(NormalsWindingsChecker)
        registerRule("Omni:Geometry", skip=not GaussianSplatSchemaChecker.is_implemented())(GaussianSplatSchemaChecker)
        registerRule("Omni:Geometry")(SubdivisionSchemeChecker)
        registerRule("Omni:Geometry")(UnusedMeshTopologyChecker)
        registerRule("Omni:Geometry")(UnusedPrimvarChecker)
        registerRule("Omni:Geometry")(ValidateTopologyChecker)
        registerRule("Omni:Geometry")(WeldChecker)
        registerRule("Omni:Geometry")(ZeroAreaFaceChecker)

        # Omni:Material rules
        registerRule("Omni:Material")(MaterialPathChecker)
        registerRule("Omni:Material")(MaterialOutOfScopeChecker)
        registerRule("Omni:Material")(MaterialOldMdlSchemaChecker)
        registerRule("Omni:Material")(ShaderImplementationSourceChecker)
        registerRule("Omni:Material")(OmniMaterialUsdPreviewSurfaceChecker)

        # Omni:Layout rules
        registerRule("Omni:Layout")(OmniDefaultPrimChecker)
        registerRule("Omni:Layout")(OmniOrphanedPrimChecker)

        # Omni:Skel rules
        registerRule("Omni:Skel", skip=is_omni_skel_upgrade_disabled())(OmniSkelUpgradeChecker)

        # Usd:Physics rules
        registerRule("Usd:Physics")(RigidBodyChecker)
        registerRule("Usd:Physics")(ColliderChecker)
        registerRule("Usd:Physics")(PhysicsJointChecker)
        registerRule("Usd:Physics")(ArticulationChecker)
        registerRule("Usd:Physics")(MassChecker)

    def on_shutdown(self) -> None:
        unregister_profiles(Profiles)
        unregister_features(Features)
        unregister_capabilities(Capabilities)
        CategoryRuleRegistry().clear()
        RequirementsRegistry().clear()
