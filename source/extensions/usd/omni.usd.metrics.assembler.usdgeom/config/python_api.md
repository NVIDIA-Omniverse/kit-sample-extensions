# Public API for module omni.metrics.assembler.usdgeom:

## Classes

- class CameraRuleRegistry
  - def __init__(self)
  - def register(self)
  - def unregister(self)

- class OmniUsdMetricsAssemblerUsdGeom(omni.ext.IExt)
  - def __init__(self)
  - def on_startup(self, ext_id)
  - def on_shutdown(self)

## Variables

- CAMERA_SCENE_UNIT_ATTRIBUTES: List[Tuple[str, int, int]]

## Other

- omni.ext: public module
