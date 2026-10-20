# Public API for module omni.kit.manipulator.creo_camera:

## Classes

- class CreoCameraManipulatorExtension(omni.ext.IExt)
  - def __init__(self)
  - def on_startup(self, ext_id)
  - def on_shutdown(self)

## Functions

- def get_active_viewport_window(window_name: str = None, usd_context_name: str = '', **kwargs)
- def CreoCameraFactory(desc: dict) -> CreoCameraManipulator

## Variables

- RegisterScene: Unknown

## Other

- omni.ext: public module
