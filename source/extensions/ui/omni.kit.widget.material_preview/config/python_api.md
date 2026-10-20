# Public API for module omni.kit.widget.material_preview:

## Classes

- class MaterialPreviewProducer
  - def __init__(self, source_context_name: str = '', shader_path: Optional[Sdf.Path] = None, swatch_layer_path: Optional[str] = None, camera_path: Optional[Sdf.Path] = None, hydra_engine_name: str = 'rtx')
  - def initialize(self)
  - def destroy(self)
  - def set_on_baked_preview_changed_fn(self, callback_fn)
  - def set_on_drawable_changed_fn(self, callback_fn)
  - def set_material(self, shader_path: Sdf.Path)
  - [property] def material_path(self)
  - [material_path.setter] def material_path(self, path)
  - [property] def gpu_reference(self)
  - [property] def resolution(self)
  - [resolution.setter] def resolution(self, value)
  - [property] def paused(self)
  - [paused.setter] def paused(self, value)
  - [property] def camera_prim(self)
  - [property] def ready_for_capture(self) -> bool
  - async def get_raw_data_async(self) -> Tuple[List[int], int, int, int, int]
  - async def set_captured_data_async(self)
  - def set_captured_data(self)
  - def get_captured_raw_data(self) -> Optional[Tuple[List[int], int, int]]
  - def set_listen_root(self, root: Sdf.Path)
  - def clear(self)
  - def submit_layer(self, delta_layer: Sdf.Layer)
  - def submit_text(self, delta_text: str)
  - def submit_camera(self, camera: Sdf.Path)

- class UsdBakedPreview
  - ATTR_NAME: str
  - class PreviewType(Enum)
    - ZIP: int
  - def __init__(self, prim: Usd.Prim)
  - def get_baked_preview_data(self) -> Optional[Tuple[List[int], int, int]]
  - def set_baked_preview_data(self, data, width, height, format, data_type: PreviewType = PreviewType.ZIP)
  - def has_baked_preview_attr(self) -> Optional[bool]
  - def get_baked_preview_attr(self) -> Optional[Usd.Attribute]
  - def create_baked_preview_attr(self) -> Optional[Usd.Attribute]
