# Public API for module omni.metrics.assembler.core:

## Classes

- class MetricsAssembler
  - def change_stage_units(self, arg0: int, arg1: UnitsInfo) -> bool
  - def check_layers(self, layer0Identifier: str, layer1Identifier: str, stage_id: int) -> dict
  - def check_stage(self, arg0: int) -> bool
  - def register_custom_callback(self, resolve_start_fn: typing.Callable[[int], None], resolve_end_fn: typing.Callable[[int], None], resolve_prim_fn: typing.Callable[[str, UnitsInfo, UnitsInfo], bool], resolve_attribute_fn: typing.Callable[[str, str, UnitsInfo, UnitsInfo, int, int], tuple], attribute_tokens: typing.List[str] = []) -> int
  - def register_custom_resolve_rule(self, attribute_name: str, meters_exponent: int, kilograms_exponent: int) -> int
  - def resolve_hierarchy(self, stage_id: int, prim_path: str) -> bool
  - def resolve_stage(self, arg0: int) -> bool
  - def set_resolve_layer(self, arg0: str)
  - def unregister_custom_callback(self, registry_id: int)
  - def unregister_custom_resolve_rule(self, arg0: int)

- class OmniUsdMetricsAssembler(omni.ext.IExt)
  - def __init__(self)
  - def on_startup(self)
  - def on_shutdown(self)

## Functions

- def acquire_metrics_assembler_interface(plugin_name: str = None, library_path: str = None) -> MetricsAssembler
- def get_metrics_assembler_interface() -> MetricsAssembler
- def release_metrics_assembler_interface(arg0: MetricsAssembler)
- def release_metrics_assembler_interface_scripting(arg0: MetricsAssembler)

## Other

- omni.ext: public module
