# Public API for module omni.asset_validator.ui:

## Classes

- class ApplicationModel
  - uri_model: UriModel
  - stage_model: StageModel
  - prims_model: PrimsModel
  - mode_model: ModeModel
  - categories_model: CategoriesModel
  - capabilities_model: CapabilitiesModel
  - features_model: FeaturesModel
  - profiles_model: ProfilesModel
  - parameters_model: ParametersModel
  - options_mode_model: OptionModeModel
  - settings_model: SettingsModel
  - filters_model: FiltersModel
  - group_by_model: GroupByModel
  - results_model: ResultsModel
  - [property] def uri(self) -> str
  - [uri.setter] def uri(self, value: str)
  - [property] def stage(self) -> Usd.Stage
  - [stage.setter] def stage(self, value: Usd.Stage)
  - [property] def prims(self) -> list[Sdf.Path]
  - [prims.setter] def prims(self, value: list[Sdf.Path])
  - [property] def mode(self) -> AssetMode
  - [mode.setter] def mode(self, value: AssetMode)
  - [property] def asset(self) -> AssetType
  - [asset.setter] def asset(self, value: AssetType)
  - def reset_asset(self)
  - [property] def options_mode(self) -> OptionMode
  - [options_mode.setter] def options_mode(self, mode: OptionMode)
  - [property] def group_by(self) -> IssueGroupBy
  - def create_engine(self) -> ValidationEngine
  - [property] def results(self) -> ResultsModel
  - def reset_selection(self)
  - def add_task(self, task: asyncio.Task)
  - def has_tasks(self) -> bool
  - async def wait_tasks(self)
  - class def get(cls) -> ApplicationModel
  - class def create(cls) -> ApplicationModel

- class AssetMode(IntEnum)
  - Uri: int
  - Stage: int
  - Prims: int

- class PublicExtension(omni.ext.IExt)
  - def on_startup(self, ext_id)
  - def on_shutdown(self)
  - def show(self)
  - def hide(self)
  - def visible(self) -> bool
  - [property] def variants(self) -> bool
  - [variants.setter] def variants(self, flag: bool)
  - [property] def instance_prototypes(self) -> bool
  - [instance_prototypes.setter] def instance_prototypes(self, flag: bool)
  - [property] def autovalidate(self) -> bool
  - [autovalidate.setter] def autovalidate(self, flag: bool)
  - [property] def issueOnRootOnly(self) -> bool
  - [issueOnRootOnly.setter] def issueOnRootOnly(self, flag: bool)
  - [property] def selectedIssues(self) -> list[omni.asset_validator.core.Issue]
  - def enableRule(self, Rule: omni.asset_validator.core.BaseRuleChecker)
  - def disableRule(self, Rule: omni.asset_validator.core.BaseRuleChecker)
  - def enabled(self, Rule: omni.asset_validator.core.BaseRuleChecker) -> bool
  - def reset(self, resetAssets: bool = False, resetRules: bool = False)
  - def getAssetMode(self) -> AssetMode
  - def setAssetMode(self, mode: AssetMode)
  - def getAssetUri(self) -> str
  - def setAssetUri(self, asset: str)
  - def getStage(self) -> Usd.Stage
  - def setStage(self, stage: Usd.Stage)
  - async def validate_async(self) -> list[omni.asset_validator.core.Results]
  - def selectIssue(self, issue: omni.asset_validator.core.Issue) -> bool
  - async def fix(self)
  - async def fixAndSave(self)
  - async def fixIssue(self, issue: omni.asset_validator.core.Issue)
  - async def fixAndSaveIssue(self, issue: omni.asset_validator.core.Issue)

## Functions

- def get_instance() -> PublicExtension
