# Public API for module omni.scene.optimizer.core:

## Classes

- class ISceneOptimizer
  - def delete_prims(self, arg0: object, arg1: typing.List[str])
  - def deregister_operation(self, arg0: str)
  - def execute_operation(self, arg0: str, arg1: object, arg2: str) -> tuple
  - def get_operation_arguments(self, arg0: str) -> list
  - def get_operation_author(self, arg0: str) -> str
  - def get_operation_description(self, arg0: str) -> str
  - def get_operation_display_group(self, arg0: str) -> str
  - def get_operation_display_name(self, arg0: str) -> str
  - def get_operation_supports_analysis(self, arg0: str) -> bool
  - def get_operation_version(self, arg0: str) -> usd_optimize.impl.core._usd_optimize_impl_core.UsdOptimizePluginVersion
  - def get_operation_visible(self, arg0: str) -> bool
  - def get_operations(self) -> list
  - def json_parser(self, arg0: object, arg1: str) -> bool
  - def load_plugins(self)
  - def load_plugins_from_path(self, arg0: str)
  - def map_config(self, arg0: str) -> str
  - def path_resolver(self, arg0: object, arg1: typing.List[str], arg2: bool) -> list

## Functions

- def acquire_interface(plugin_name: str = None, library_path: str = None) -> ISceneOptimizer
- def release_interface(arg0: ISceneOptimizer)

## Variables

- SceneOptimizerCore: UsdOptimizeCore
- SOPluginVersion: UsdOptimizePluginVersion

## Other

- os: builtin module
- sys: builtin module
- UNKNOWN_MODULE_DEFS: unknown
