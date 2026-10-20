# Public API for module omni.asset_validator.core:

## Classes

- class AlmostExtremeExtentChecker(BaseBoundsChecker)
  - BOUNDS_LIMIT: BoundsLimit

- class AnchoredAssetPathsChecker(BaseRuleChecker)
  - def __init__(self, verbose: bool, consumerLevelChecks: bool, assetLevelChecks: bool)
  - def CheckStage(self, stage)
  - def CheckLayer(self, layer)

- class ArticulationChecker(BaseRuleCheckerWCache)
  - class def validator_name(cls) -> str

- class AssetFix(Protocol)

- class AssetFormat(Protocol)
  - def supports(self, asset_path: str) -> bool
  - def get_dependencies(self, asset_path: str, uri_resolver: UriResolver) -> list[str]

- class AssetFormatRegistry
  - def __init__(self)
  - def event_stream(self) -> EventStream
  - def add(self, fmt_class: type[AssetFormat])
  - def remove(self, fmt_class: type[AssetFormat])
  - def clear(self)
  - def find(self, asset_path: str) -> AssetFormat | None
  - def add_callback(self, callback: Callable[[], None]) -> EventListener

- class AssetLocatedCallback(Protocol)

- class AssetProgress
  - asset: str
  - progress: float
  - results: Results | None

- class AssetProgressCallback(Protocol)

- class AssetValidatedCallback(Protocol)

- class AttributeId(PropertyId)
  - class def from_(cls, attr: Usd.Attribute) -> AttributeId

- class BaseRuleChecker
  - def __init__(self, verbose: bool = False, consumerLevelChecks: bool = False, assetLevelChecks: bool = True, *args, **kwargs)
  - def GetIssues(self) -> Sequence[Issue]
  - [property] def parameters(self) -> ParameterMapping
  - class def GetDescription(cls)
  - def CheckStage(self, usdStage)
  - def CheckDiagnostics(self, diagnostics)
  - def CheckUnresolvedPaths(self, unresolvedPaths)
  - def CheckDependencies(self, usdStage, layerDeps, assetDeps)
  - def CheckLayer(self, layer)
  - def CheckZipFile(self, zipFile, packagePath)
  - def CheckFormatDependency(self, dependency: FormatDependency)
  - def CheckPrim(self, prim)
  - def ResetCaches(self)

- class ByteAlignmentChecker(BaseRuleChecker)
  - def __init__(self, verbose, consumerLevelChecks, assetLevelChecks)
  - def CheckZipFile(self, zipFile, packagePath)

- class CapabilityProtocol(Protocol)
  - id: str
  - version: str
  - path: str
  - requirements: list[RequirementProtocol | RequirementRefProtocol]

- class CapabilityRegistry(VersionedRegistry[Capability])
  - def __init__(self)
  - def create_key(self, value: Capability) -> IdVersion
  - [property] def capabilities(self) -> list[Capability]
  - [property] def latest_capabilities(self) -> list[Capability]
  - def get_requirements(self, capability: Capability) -> list[Requirement | RequirementRefProtocol]
  - def remove(self, capability: Capability)
  - def get_capability_ids(self) -> list[str]
  - def add_capability(self, capability: Capability)
  - def find_capability(self, id: str, version: str | None = None) -> Capability | None

- class ColliderChecker(BaseRuleCheckerWCache)
  - class def validator_name(cls) -> str

- class CompressionChecker(BaseRuleChecker)
  - def __init__(self, verbose, consumerLevelChecks, assetLevelChecks)
  - def CheckZipFile(self, zipFile, packagePath)

- class CoreExtension(IExt)
  - def on_startup(self, ext_id: str)
  - def on_shutdown(self)

- class EditTargetId(Identifier[Sdf.Layer | Sdf.Spec])
  - layer_id: LayerId
  - path: Sdf.Path | None
  - composed: PrimId | PropertyId | None
  - class def from_(cls, obj: Sdf.Layer | Sdf.Spec) -> EditTargetId
  - def restore(self, stage: Usd.Stage) -> Sdf.Layer | Sdf.Spec | None
  - def get_spec_ids(self) -> list[EditTargetId]
  - def as_str(self) -> str

- class EditTargetIdList(Sequence[EditTargetId])
  - [property] def spec_ids(self) -> list[SpecId]
  - class def from_(cls, obj) -> EditTargetIdList

- class ExtentsChecker(BaseRuleChecker)
  - def __init__(self, verbose: bool, consumerLevelChecks: bool, assetLevelChecks: bool)
  - def CheckPrim(self, prim: Usd.Prim)
  - def ResetCaches(self)

- class FeatureProtocol(Protocol)
  - id: str
  - version: str
  - path: str
  - requirements: list[RequirementProtocol | RequirementRefProtocol]
  - dependencies: list[FeatureProtocol | FeatureRefProtocol]
  - custom_data: dict[str, Any]

- class FeatureRegistry(VersionedRegistry[Feature])
  - def __init__(self)
  - def create_key(self, value: Feature) -> IdVersion
  - [property] def features(self) -> list[Feature]
  - [property] def latest_features(self) -> list[Feature]
  - def get_requirements(self, feature: Feature | FeatureRefProtocol) -> list[Requirement | RequirementRefProtocol]
  - def remove(self, feature: Feature)

- class FixResult
  - issue: Issue
  - status: FixStatus
  - exception: Exception | None

- class FixStatus(Enum)
  - NO_LOCATION: int
  - NO_SUGGESTION: int
  - FAILURE: int
  - SUCCESS: int
  - NO_LAYER: int
  - INVALID_LOCATION: int

- class FormatDependency
  - path: str
  - uri_resolver: UriResolver
  - root_asset_path: str

- class FormatDependencyId(Identifier[FormatDependency])
  - path: str
  - root_asset_path: str
  - class def from_(cls, dep: FormatDependency) -> FormatDependencyId
  - def restore(self, stage: Usd.Stage | None = None) -> FormatDependency

- class GaussianSplatSchemaChecker(BaseRuleChecker)
  - static def is_implemented() -> bool
  - def CheckPrim(self, prim: Usd.Prim)

- class IdVersion
  - id: str
  - version: SemVer

- class Identifier(Generic[AtType])
  - class def from_(cls, obj: AtType) -> Identifier[AtType]
  - def restore(self, stage: Usd.Stage) -> AtType
  - def as_str(self) -> str
  - def get_layer_ids(self) -> list[LayerId]
  - def get_spec_ids(self) -> list[SpecId]

- class IndexedPrimvarChecker(BaseRuleChecker)
  - def CheckPrim(self, prim: Usd.Prim)

- class Issue
  - message: str | None
  - severity: IssueSeverity | None
  - rule: RuleType | None
  - at: AtType | Identifier[AtType] | list[AtType] | list[Identifier[AtType]] | None
  - suggestion: Suggestion | None
  - suggestions: tuple[Suggestion, Ellipsis]
  - asset: StageId | None
  - code: str | None
  - requirement: Requirement | RequirementRefProtocol | None
  - class def from_message(cls, severity: IssueSeverity, message: str) -> Issue
  - class def from_(cls, severity: IssueSeverity, rule: RuleType, message: str) -> Issue
  - class def none(cls) -> Issue
  - [property] def tags(self) -> tuple[str, ...] | None
  - def fix_sites_for(self, suggestion: Suggestion | None = None) -> list[EditTargetId]
  - [property] def all_fix_sites(self) -> list[EditTargetId]
  - [property] def default_fix_site(self) -> EditTargetId | None

- class IssueFixer
  - asset: AssetType
  - layers: set[Sdf.Layer]
  - lock: threading.Lock
  - def apply(self, issue: Issue, at: EditTargetId | None = None, suggestion: Suggestion | None = None) -> FixResult
  - def fix(self, issues: list[Issue]) -> Sequence[FixResult]
  - def fix_at(self, issues: list[Issue], layer: Sdf.Layer) -> Sequence[FixResult]
  - [property] def fixed_layers(self) -> list[Sdf.Layer]
  - def save(self)

- class IssueGroupBy(Protocol)

- class IssueGroupsBy
  - class def asset(cls) -> IssueGroupBy
  - class def rule(cls) -> IssueGroupBy
  - class def rule_name(cls) -> IssueGroupBy
  - class def severity(cls) -> IssueGroupBy
  - class def message(cls) -> IssueGroupBy
  - class def code(cls) -> IssueGroupBy
  - class def requirement(cls) -> IssueGroupBy

- class IssueJSONEncoder(json.JSONEncoder)
  - def __init__(self, rules: list[BaseRuleChecker] | None = None, metadata: ValidationContext | None = None, *args, **kwargs)
  - def default(self, o: Any) -> Any

- class IssuePredicate(Protocol)

- class IssuePredicates
  - static def Any() -> IssuePredicate
  - static def IsFailure() -> IssuePredicate
  - static def IsWarning() -> IssuePredicate
  - static def IsError() -> IssuePredicate
  - static def IsInfo() -> IssuePredicate
  - static def IsSuccess() -> IssuePredicate
  - static def ContainsMessage(text: str) -> IssuePredicate
  - static def IsRule(rule: str | RuleType) -> IssuePredicate
  - static def HasLocation() -> IssuePredicate
  - static def HasFix() -> IssuePredicate
  - static def HasRootLayer() -> IssuePredicate
  - static def And(*predicates) -> IssuePredicate
  - static def Or(*predicates) -> IssuePredicate
  - static def Not(predicate: IssuePredicate) -> IssuePredicate
  - static def HasCode() -> IssuePredicate
  - static def MatchesCode(code: str) -> IssuePredicate
  - static def MatchesAnyCode(codes: Sequence[str]) -> IssuePredicate
  - static def MatchesToken(token: str) -> IssuePredicate
  - static def HasTag(tag: str) -> IssuePredicate

- class IssueSeverity(Enum)
  - ERROR: int
  - FAILURE: int
  - WARNING: int
  - INFO: int
  - NONE: int

- class IssuesList(Sequence[Issue])
  - issues: list[Issue]
  - success: list[Issue]
  - name: Any | None
  - def filter_by(self, predicate: IssuePredicate | None = None) -> IssuesList
  - def count_if(self, predicate: IssuePredicate | None = None) -> int
  - def group_by(self, group_by: IssueGroupBy | None = None) -> list[IssuesList]
  - def merge(self, other: IssuesList) -> IssuesList

- class KindChecker(BaseRuleChecker)
  - def __init__(self, verbose, consumerLevelChecks, assetLevelChecks)
  - def CheckPrim(self, prim)
  - class def fix_ancestors_kind_with_components(cls, _: Usd.Stage, prim: Usd.Prim)
  - class def fix_ancestors_empty_kind(cls, _: Usd.Stage, prim: Usd.Prim)
  - def ResetCaches(self)

- class LayerId(Identifier[Sdf.Layer])
  - identifier: str
  - class def from_(cls, layer: Sdf.Layer) -> LayerId
  - def restore(self, stage: Usd.Stage) -> Sdf.Layer
  - def get_spec_ids(self) -> list[SpecId]
  - def as_str(self)

- class LayerSpecChecker(BaseRuleChecker)
  - def __init__(self, verbose: bool, consumerLevelChecks: bool, assetLevelChecks: bool)
  - class def fix_unsupported_fields_callback(cls, stage: Usd.Stage, spec: Sdf.Spec)
  - class def fix_timesamples_callback(cls, stage: Usd.Stage, spec: Sdf.Spec)
  - static def fix_time_varying_relationship_callback(stage: Usd.Stage, spec: Sdf.AttributeSpec)
  - def CheckLayer(self, layer: Sdf.Layer)

- class ManifoldChecker(BaseRuleChecker)
  - def CheckPrim(self, prim: Usd.Prim)

- class MassChecker(BaseRuleChecker)
  - def CheckPrim(self, usd_prim: Usd.Prim)

- class MaterialOldMdlSchemaChecker(BaseRuleChecker)
  - static def update_deprecated_mdl_schema(_: Usd.Stage, prim: Usd.Prim)
  - def CheckPrim(self, prim)

- class MaterialOutOfScopeChecker(BaseRuleChecker)
  - def CheckPrim(self, prim: Usd.Prim)

- class MaterialPathChecker(BaseRuleChecker)
  - def __init__(self, verbose: bool, consumerLevelChecks: bool, assetLevelChecks: bool)
  - def CheckUnresolvedPaths(self, unresolvedPaths)
  - def CheckDependencies(self, usdStage, layerDeps, assetDeps)
  - class def fix_path_callback(cls, stage: Usd.Stage, attribute: Usd.Attribute)
  - def CheckPrim(self, prim)

- class MissingReferenceChecker(BaseRuleChecker)
  - def __init__(self, verbose, consumerLevelChecks, assetLevelChecks)
  - def CheckStage(self, stage: Usd.Stage)
  - def CheckDiagnostics(self, diagnostics)
  - def CheckUnresolvedPaths(self, unresolvedPaths)

- class NormalMapTextureChecker(BaseRuleChecker)
  - NORMAL_MAP_SOURCE_COLOR_SPACE: str
  - NORMAL_MAP_SCALE: Gf.Vec4f
  - NORMAL_MAP_BIAS: Gf.Vec4f
  - def __init__(self, verbose, consumerLevelChecks, assetLevelChecks)
  - def CheckPrim(self, prim)

- class NormalsExistChecker(BaseRuleChecker)
  - class def set_to_none(cls, _: Usd.Stage, mesh: UsdGeom.Mesh)
  - class def remove_non_primvar_normals(cls, _: Usd.Stage, mesh: UsdGeom.Mesh)
  - def CheckPrim(self, prim: Usd.Prim)

- class NormalsValidChecker(BaseRuleChecker)
  - UNIT_LENGTH_TOLERANCE: float
  - def CheckPrim(self, prim: Usd.Prim)

- class NormalsWindingsChecker(BaseRuleChecker)
  - def CheckPrim(self, prim: Usd.Prim)

- class OmniComplianceChecker(ComplianceChecker)

- class OmniDefaultPrimChecker(DefaultPrimChecker)

- class OmniMaterialUsdPreviewSurfaceChecker(MaterialUsdPreviewSurfaceChecker)
  - INPUTS_TO_SKIP: List

- class OmniOrphanedPrimChecker(DanglingOverPrimChecker)

- class OmniSkelUpgradeChecker(BaseRuleChecker)
  - NV_SKINNING_METHOD: str
  - NV_SKINNING_BLEND_WEIGHTS: str
  - STOCK_SKINNING_METHOD: str
  - NV_STOCK_SKINNING_METHOD_MAP: Dict
  - OMNI_SKINNING_BLEND_WEIGHT_SCHEMA: str
  - OMNI_SKINNING_BLEND_WEIGHT_ATTR: str
  - def __init__(self, verbose, consumerLevelChecks, assetLevelChecks)
  - def migrate_skinning_method(self, stage: Usd.Stage, prim: Usd.Prim)
  - def migrate_weighted_blend_schema(self, stage: Usd.Stage, prim: Usd.Prim)
  - def remove_nv_skinning_method(self, stage: Usd.Stage, prim: Usd.Prim)
  - def CheckPrim(self, prim: Usd.Prim)

- class Parameter(Protocol)
  - display_name: str
  - type: ParameterType
  - assigned_value: int | bool | float | str | None
  - enum_values: tuple[str, ...] | None

- class ParameterMapping(UserDict)
  - def __init__(self, parameters: Iterable[Parameter] | None = None)
  - def add(self, parameter: Parameter)
  - def keys(self) -> list[str]
  - def values(self) -> list[Parameter]
  - def items(self) -> list[tuple[str, Parameter]]

- class ParameterType(str, Enum)
  - INT: str
  - BOOL: str
  - FLOAT: str
  - ENUM: str

- class PhysicsJointChecker(UsdValidatorAdapter)
  - class def validator_name(cls) -> str

- class PointsPrecisionErrorChecker(PointsPrecisionChecker)
  - PRECISION_LIMIT: PrecisionLimit
  - SEVERITY: IssueSeverity

- class PointsPrecisionWarningChecker(PointsPrecisionChecker)
  - PRECISION_LIMIT: PrecisionLimit
  - SEVERITY: IssueSeverity

- class PortableAssetPathChecker(BaseRuleChecker)
  - def CheckLayer(self, layer: Sdf.Layer)

- class PrimEncapsulationChecker(BaseRuleChecker)
  - def __init__(self, verbose, consumerLevelChecks, assetLevelChecks)
  - def CheckPrim(self, prim)
  - def ResetCaches(self)

- class PrimId(Identifier[Usd.Prim], VariantIdMixin)
  - stage_id: StageId
  - path: Sdf.Path
  - spec_ids: SpecIdList
  - variant_selection_path: Sdf.Path
  - class def from_(cls, prim: Usd.Prim) -> PrimId
  - def restore(self, stage: Usd.Stage) -> Usd.Prim
  - def as_str(self) -> str
  - def get_spec_ids(self) -> list[SpecId]

- class ProfileProtocol(Protocol)
  - id: str
  - version: str
  - path: str
  - features: list[FeatureProtocol]
  - capabilities: list[CapabilityProtocol]
  - profile_features: list[ProfileFeatureProtocol]

- class ProfileRegistry(VersionedRegistry[Profile])
  - def __init__(self)
  - def create_key(self, value: Profile) -> IdVersion
  - [property] def profiles(self) -> list[Profile]
  - def get_requirements(self, profile: Profile) -> list[Requirement | RequirementRefProtocol]
  - def remove(self, profile: Profile)
  - def add_profile(self, profile: Profile)
  - def find_profile(self, id: str, version: str | None = None) -> Profile | None

- class PropertyId(Identifier[Usd.Attribute], VariantIdMixin)
  - prim_id: PrimId
  - path: Sdf.Path
  - [property] def variant_selection_path(self)
  - class def from_(cls, prop: Usd.Property) -> PropertyId
  - def restore(self, stage: Usd.Stage) -> Usd.Property
  - [property] def name(self) -> str
  - [property] def stage_id(self) -> StageId
  - def as_str(self) -> str
  - def get_spec_ids(self) -> list[SpecId]

- class RepeatedValuesSet
  - def __init__(self, values: VtArray[ScalarType])

- class RequirementProtocol(Protocol)
  - code: str
  - version: str | None
  - display_name: str | None
  - message: str | None
  - path: str | None
  - compatibility: str | None
  - validator: str | None
  - tags: tuple[str, Ellipsis]
  - parameters: tuple[Parameter, Ellipsis]
  - examples: tuple[Example, Ellipsis]

- class RequirementRefProtocol(Protocol)
  - code: str
  - version: str | None

- class RequirementsRegistry(VersionedRegistry[Requirement])
  - def __init__(self)
  - def create_key(self, value: Requirement | RequirementRefProtocol) -> IdVersion
  - [property] def requirements(self) -> list[Requirement]
  - [property] def latest_requirements(self) -> list[Requirement]
  - [property] def rules(self)
  - def clear(self)
  - def get_requirements(self, rule: type[BaseRuleChecker]) -> list[Requirement | RequirementRefProtocol]
  - def resolve_requirement(self, requirement: Requirement | RequirementRefProtocol) -> Requirement | RequirementRefProtocol
  - def resolve_requirements(self, requirements: list[Requirement | RequirementRefProtocol]) -> list[Requirement | RequirementRefProtocol]
  - def get_validator(self, requirement: Requirement | RequirementRefProtocol) -> type[BaseRuleChecker] | None
  - def get_validators(self, requirements: list[Requirement | RequirementRefProtocol]) -> list[type[BaseRuleChecker]]
  - def is_implemented(self, requirement: Requirement | RequirementRefProtocol) -> bool
  - def all_implemented(self, requirements: list[Requirement | RequirementRefProtocol]) -> bool
  - def is_registered(self, rule: type[BaseRuleChecker], requirement: Requirement | RequirementRefProtocol) -> bool
  - def find_requirement(self, code: str, version: str | None = None) -> Requirement | None

- class Results(Sequence[Issue])
  - asset: str
  - issues: list[Issue] | IssuesList
  - context: ValidationContext | None
  - class def create(cls, asset: Usd.Stage | str, issues: Sequence[Issue]) -> Results
  - def filter_by(self, predicate: IssuePredicate) -> Results

- class ResultsList(Sequence[Results])
  - results: list[Results]
  - context: ValidationContext | None
  - def issues(self) -> IssuesList

- class RigidBodyChecker(BaseRuleCheckerWCache)
  - class def validator_name(cls) -> str

- class SchemaBaseId(Identifier[Usd.SchemaBase], VariantIdMixin)
  - prim_id: PrimId
  - schema_class: Any
  - instance_name: str | None
  - [property] def variant_selection_path(self)
  - class def from_(cls, instance: Usd.SchemaBase) -> SchemaBaseId
  - [property] def path(self) -> Sdf.Path
  - def restore(self, stage: Usd.Stage) -> Any
  - def get_spec_ids(self) -> list[SpecId]
  - def as_str(self) -> str

- class SemVer
  - LATEST: ClassVar[str]
  - DEFAULT: ClassVar[str]
  - major: int
  - minor: int
  - patch: int
  - prerelease: str | None
  - build: str | None
  - def __init__(self, major: int | str | None = None, minor: int | None = None, patch: int | None = None, prerelease: str | None = None, build: str | None = None)
  - def is_compatible(self, required_version: SemVer) -> bool

- class ShaderImplementationSourceChecker(BaseRuleChecker)
  - def CheckPrim(self, prim)

- class SkelBindingAPIAppliedChecker(BaseRuleChecker)
  - def __init__(self, verbose, consumerLevelChecks, assetLevelChecks)
  - class def apply_api(cls, _: Usd.Stage, prim: Usd.Prim)
  - def CheckPrim(self, prim: Usd.Prim)

- class StageId(Identifier[Usd.Stage])
  - root_layer: LayerId
  - class def from_(cls, stage: Usd.Stage) -> StageId
  - [property] def identifier(self) -> str
  - [property] def stage_id(self) -> StageId
  - def restore(self, stage: Usd.Stage) -> Usd.Stage
  - def as_str(self) -> str
  - def get_spec_ids(self) -> list[SpecId]

- class StageMetadataChecker(BaseRuleChecker)
  - def __init__(self, verbose, consumerLevelChecks, assetLevelChecks)
  - def CheckStage(self, usdStage)

- class SubdivisionSchemeChecker(BaseRuleChecker)
  - class def set_to_none(cls, _: Usd.Stage, mesh: UsdGeom.Mesh)
  - class def set_to_catmull_clark(cls, _: Usd.Stage, mesh: UsdGeom.Mesh)
  - def CheckPrim(self, prim: Usd.Prim)

- class Suggestion
  - callable: AssetFix
  - message: str
  - at: AtType | list[AtType] | list[EditTargetId] | None

- class SupportedFileTypesChecker(BaseRuleChecker)
  - def __init__(self, verbose: bool, consumerLevelChecks: bool, assetLevelChecks: bool)
  - def CheckZipFile(self, zip_file: Usd.ZipFile, package_path: str)
  - def CheckUnresolvedPaths(self, unresolvedPaths: list[str])
  - def CheckDependencies(self, _, layer_deps: list[Sdf.Layer], asset_deps: list[str])

- class TextureChecker(BaseRuleChecker)
  - def __init__(self, verbose, consumerLevelChecks, assetLevelChecks)
  - def CheckStage(self, usdStage)
  - def CheckPrim(self, prim)

- class TypeChecker(BaseRuleChecker)
  - def CheckPrim(self, prim)

- class UnicodeNameChecker(BaseRuleChecker)
  - def CheckStage(self, usdStage: Usd.Stage)
  - def CheckPrim(self, prim: Usd.Prim)
  - def CheckLayer(self, layer)

- class UnusedMeshTopologyChecker(BaseRuleChecker)
  - class def remove_unreferenced_points(cls, _: Usd.Stage, prim: Usd.Prim)
  - def CheckPrim(self, prim: Usd.Prim)

- class UnusedPrimvarChecker(BaseRuleChecker)
  - def CheckPrim(self, prim: Usd.Prim)
  - static def remove_unreferenced_values(_: Usd.Stage, attr: Usd.Attribute)

- class UsdAsciiPerformanceChecker(BaseRuleChecker)
  - def __init__(self, verbose: bool, consumerLevelChecks: bool, assetLevelChecks: bool)
  - def CheckLayer(self, layer: Sdf.Layer)

- class UsdDanglingMaterialBinding(BaseRuleChecker)
  - class def apply_dangling_material_binding_fix(cls, _: Usd.Stage, prim)
  - def CheckPrim(self, prim)

- class UsdGeomSubsetChecker(BaseRuleChecker)
  - class def apply_family_name_fix(cls, _: Usd.Stage, subset: UsdGeom.Subset)
  - def CheckPrim(self, prim)

- class UsdLuxSchemaChecker(BaseRuleChecker)
  - LUX_ATTRIBUTES: set[str]
  - class def fix_attribute_name(cls, _: Usd.Stage, attribute: Usd.Attribute)
  - def CheckPrim(self, prim)

- class UsdMaterialBindingApi(BaseRuleChecker)
  - class def apply_material_binding_api_fix(cls, _: Usd.Stage, prim)
  - def CheckPrim(self, prim)

- class UsdValidatorAdapter(BaseRuleChecker)
  - class def validator_name(cls) -> str
  - class def is_implemented(cls) -> bool
  - class def GetDescription(cls) -> str
  - def base_validator(self) -> ValidatorProtocol | None
  - def CheckStage(self, stage: Usd.Stage)
  - def CheckLayer(self, layer: Sdf.Layer)
  - def CheckPrim(self, prim: Usd.Prim)

- class UsdzPackageValidator(UsdValidatorAdapter)
  - class def validator_name(cls) -> str

- class UsdzUdimLimitationChecker(BaseRuleChecker)
  - def __init__(self, verbose: bool, consumerLevelChecks: bool, assetLevelChecks: bool)
  - def CheckPrim(self, prim: Usd.Prim)

- class UserParameter(Parameter)
  - parameter: Parameter
  - assigned_value: int | bool | float | str | None
  - [property] def display_name(self) -> str
  - [property] def type(self) -> ParameterType
  - [property] def enum_values(self) -> tuple[str, ...] | None

- class ValidateTopologyChecker(BaseRuleChecker)
  - def validate(self, mesh: UsdGeom.Mesh)
  - def CheckPrim(self, prim: Usd.Prim)

- class ValidationEngine(_ValidationEngine)
  - def __init__(self)
  - [property] def initialized_rules(self) -> list[type[BaseRuleChecker]]

- class ValidationRulesRegistry
  - static def init()
  - static def categories(enabledOnly: bool = False) -> tuple[str, Ellipsis]
  - static def rules(category: str, enabledOnly: bool = False) -> tuple[type[BaseRuleChecker], Ellipsis]
  - static def registerRule(rule: type[BaseRuleChecker], category: str)
  - static def deregisterRule(rule: type[BaseRuleChecker])
  - static def rule(name: str) -> type[BaseRuleChecker] | None
  - static def category(rule: type[BaseRuleChecker]) -> str
  - static def add_registry_rule_callback(callback: Callable[[], None]) -> EventListener

- class ValidationStats(_Stats)
  - def __init__(self)
  - def time_rule(self, rule: _RuleType) -> _TimeStat
  - def count_rule_severity(self, rule: _RuleType, severity: Enum)
  - def count_issues(self, issues)
  - def merge(self, stats: ValidationStats)
  - def get_rule_times(self) -> list[tuple[_RuleType, float]]
  - def total_time(self) -> float
  - def get_rule_severity_counts(self) -> list[tuple[_RuleType, Enum, int]]
  - def get_severity_count(self, severity: Enum) -> int

- class VariantIdMixin
  - [property] def variant_selection_path(self) -> Sdf.Path
  - static def get_variant_selection_path(prim: Usd.Prim) -> Sdf.Path
  - def restore_variant_selection(self, stage: Usd.Stage)

- class WeldChecker(BaseRuleChecker)
  - def validate_mesh(self, mesh: UsdGeom.Mesh)
  - def CheckPrim(self, prim: Usd.Prim)

- class ZeroAreaFaceChecker(BaseRuleChecker)
  - def validate_mesh(self, mesh: UsdGeom.Mesh)
  - def CheckPrim(self, prim: Usd.Prim)

## Functions

- def AuthoringLayers(at: AtType | list[AtType]) -> list[Sdf.Layer]
- def add_registry_asset_format_callback(callback: Callable[[], None]) -> EventListener
- def add_registry_capability_callback(callback: Callable[[], None]) -> EventListener
- def add_registry_feature_callback(callback: Callable[[], None]) -> EventListener
- def add_registry_profile_callback(callback: Callable[[], None]) -> EventListener
- def add_registry_requirement_callback(callback: Callable[[], None]) -> EventListener
- def add_registry_rule_callback(callback: Callable[[], None]) -> EventListener
- def create_validation_parser() -> argparse.ArgumentParser
- def export_json_file(json_output_path: str | pathlib.Path, entry: Results | ResultsList | IssuesList | Issue | Suggestion, metadata: ValidationContext | None = None)
- def get_version()
- def is_omni_path(path: Sdf.Path) -> bool
- def is_omni_skel_upgrade_disabled() -> bool
- def normalize_url(path_or_url: str) -> str
- def registerRule(category: str, skip: bool = False, overwrite: type[BaseRuleChecker] | None = None) -> Callable[[type[BaseRuleChecker]], type[BaseRuleChecker]]
- def register_capabilities(capabilities: Iterable[Capability]) -> bool
- def register_capability(capability: Capability)
- def register_feature(feature: Feature)
- def register_features(features: Iterable[Feature]) -> bool
- def register_format() -> Callable[[type[AssetFormat]], type[AssetFormat]]
- def register_profile(profile: Profile)
- def register_profiles(profiles: Iterable[Profile]) -> bool
- def register_requirements(*requirements: Requirement | RequirementRefProtocol) -> Callable[[type[BaseRuleChecker]], type[BaseRuleChecker]]
- def to_identifier(value: AtType | None) -> Identifier[AtType] | None
- def to_identifiers(value: list[AtType] | None) -> list[Identifier[AtType]] | None
- def unregister_capabilities(capabilities: Iterable[Capability]) -> bool
- def unregister_capability(capability: Capability)
- def unregister_feature(feature: Feature)
- def unregister_features(features: Iterable[Feature]) -> bool
- def unregister_format(fmt_class: type[AssetFormat])
- def unregister_profile(profile: Profile)
- def unregister_profiles(profiles: Iterable[Profile]) -> bool
- def unregister_requirements(rule: type[BaseRuleChecker])
- def unregister_rule(rule: type[BaseRuleChecker])

## Variables

- AssetType: Unknown
- AtType: Unknown
- Capability: CapabilityProtocol
- Feature: FeatureProtocol
- IssueCSVData: ColumnCSVTable
- Profile: ProfileProtocol
- Requirement: RequirementProtocol
- SpecId: EditTargetId
- SpecIdList: EditTargetIdList
- ValidationArgsExec: ValidationNamespaceExec

# Public API for module omni.asset_validator.simready:

## Classes

- class AssetOriginPositioningChecker(BaseAssetOriginPositioningChecker)

- class ContainsMeshChecker(BaseContainsMeshChecker)

- class GroundTruthCapabilityChecker(BaseRuleChecker)
  - QCODE_RE: Unknown
  - SEMANTIC_INSTANCE_NAME: str
  - def __init__(self, verbose, consumerLevelChecks, assetLevelChecks)
  - def CheckStage(self, stage: Usd.Stage)
  - def CheckPrim(self, prim: Usd.Prim)
  - def ResetCaches(self)

- class HierarchyHasRootChecker(BaseHierarchyHasRootChecker)

- class MetersPerUnit1Checker(BaseUnitsInMetersChecker)

- class NonVisualSensorCapabilityChecker(BaseRuleChecker)
  - ATTRIBUTE_RULES: Dict
  - def __init__(self, verbose, consumerLevelChecks, assetLevelChecks)
  - def CheckStage(self, stage: Usd.Stage)
  - def CheckPrim(self, prim: Usd.Prim)
  - def checkMaterial(self, material: UsdShade.Material)
  - def ResetCaches(self)

- class PhysxArticulationChecker(BaseRuleChecker)
  - def CheckPrim(self, usd_prim: Usd.Prim)

- class PhysxRigidBodyChecker(BaseRuleChecker)
  - def __init__(self, verbose: bool, consumerLevelChecks: bool, assetLevelChecks: bool)
  - def ResetCaches(self)
  - def CheckPrim(self, usd_prim: Usd.Prim)

- class RootPrimXformableChecker(BaseRootPrimXformableChecker)

- class UpAxisZChecker(BaseUpAxisZChecker)

- class VisualSensorCapabilityChecker(BaseRuleChecker)
  - def CheckStage(self, stage: Usd.Stage)
  - def CheckPrim(self, prim: Usd.Prim)
