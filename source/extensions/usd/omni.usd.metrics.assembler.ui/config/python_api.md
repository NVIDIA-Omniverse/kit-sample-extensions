# Public API for module omni.metrics.assembler.ui:

## Classes

- class MetricsAssemblerManager
  - def __init__(self)
  - def on_shutdown(self)
  - def on_reset(self)
  - def remove_ref_layer(self)
  - def get_metrics_assembler_change_listener(self)
  - def stage_closed(self)
  - def stage_opened(self, stage: Usd.Stage)
  - def prim_move_callback(self, info: dict)
  - def prim_copy_callback(self, info: dict)
  - def create_pre_do_callback(self, info: dict)
  - def set_resolve_layer(self, layer: Sdf.Layer)
  - def get_resolve_layer(self)
  - def create_post_do_callback(self, info: dict)
  - def metrics_assembler_check_reference_payload(self, stage: Usd.Stage, path_to: Sdf.Path, url: str)
  - def add_reference_pre_do_callback(self, info: dict)
  - def add_payload_pre_do_callback(self, info: dict)
  - def add_reference_post_do_callback(self, info: dict)
  - def add_payload_post_do_callback(self, info: dict)
  - def check_units_divergency(self, stage: Usd.Stage, url: str)

- class MetricsAssemblerUI(omni.ext.IExt)
  - def __init__(self)
  - def on_startup(self, ext_id)
  - def on_shutdown(self)

## Functions

- def get_eventdispatcher() -> IEventDispatcher
- def get_per_viewport_setting_path(viewport_id: str, setting_name: str) -> str
- def get_viewport_defaults_setting_path(setting_name: str) -> str

## Variables

- METRICS_ASSEMBLER_HUD_SETTING_SUFFIX: str

## Other

- carb.settings: public module
- omni.ext: public module
- omni.usd: public module
