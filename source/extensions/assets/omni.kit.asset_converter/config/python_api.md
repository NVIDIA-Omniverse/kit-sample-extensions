# Public API for module omni.kit.asset_converter:

## Classes

- class AssetConverterContext
  - ignore_materials: bool
  - ignore_animations: bool
  - ignore_camera: bool
  - ignore_light: bool
  - single_mesh: bool
  - smooth_normals: bool
  - export_preview_surface: bool
  - support_point_instancer: bool
  - embed_mdl_in_usd: bool
  - use_meter_as_world_unit: bool
  - create_world_as_default_root_prim: bool
  - embed_textures: bool
  - convert_fbx_to_y_up: bool
  - convert_fbx_to_z_up: bool
  - keep_all_materials: bool
  - merge_all_meshes: bool
  - use_double_precision_to_usd_transform_op: bool
  - ignore_pivots: bool
  - disabling_instancing: bool
  - export_hidden_props: bool
  - baking_scales: bool
  - ignore_flip_rotations: bool
  - ignore_unbound_bones: bool
  - bake_mdl_material: bool
  - export_separate_gltf: bool
  - export_mdl_gltf_extension: bool
  - convert_stage_up_y: bool
  - convert_stage_up_z: bool
  - def to_dict(self)

- class AssetImporterExtension(omni.ext.IExt)
  - def on_startup(self)
  - def on_shutdown(self)
  - def create_converter_task(self, import_path: str, output_path: str, progress_callback: Callable[[int], int] = None, asset_converter_context: AssetConverterContext = AssetConverterContext(), material_loader = None, close_stage_and_reopen_if_opened: bool = False)

- class OmniClientWrapper
  - static async def exists(path)
  - static def exists_sync(path)
  - static def parent(path: str) -> str
  - static def writeable(path: str)
  - static async def writeable_async(path: str) -> bool
  - static async def write(path: str, content)
  - static async def copy(src_path: str, dest_path: str)
  - static async def read(src_path: str)
  - static async def create_folder(path)

## Functions

- def get_instance()

# Public API for module asset_converter_native_bindings:

## Classes

- class OmniAssetConverter
  - def __init__(self, in_file, out_file, progress_callback = None, ignore_material = False, ignore_animation = False, single_mesh = False, smooth_normals = False, ignore_cameras = False, preview_surface = False, support_point_instancer = False, as_shapenet = False, embed_mdl_in_usd = True, use_meter_as_world_unit = False, create_world_as_default_root_prim = True, ignore_lights = False, embed_textures = False, material_loader = None, convert_fbx_to_y_up = False, convert_fbx_to_z_up = False, keep_all_materials = False, merge_all_meshes = False, use_double_precision_to_usd_transform_op = False, ignore_pivots = False, disable_instancing = False, export_hidden_props = False, baking_scales = False, ignore_flip_rotations = False, ignore_unbound_bones = False, export_embedded_gltf = False, import_gltf_mdl_extension = False, convert_stage_up_default = False, convert_stage_up_y = False, convert_stage_up_z = False)
  - static def major_version() -> int
  - static def minor_version() -> int
  - class def set_cache_folder(cls, cache_folder)
  - class def set_log_callback(cls, callback)
  - class def set_progress_callback(cls, callback)
  - class def set_file_callback(cls, mkdir_callback, binary_write_callback, file_exists_callback, read_callback, layer_write_callback = None, file_copy_callback = None)
  - class def set_material_loader(cls, material_loader)
  - class def set_neuraylib_callback(cls, get_neuray_api_callback, create_mdl_module_callback, destroy_mdl_module_callback, create_temporary_db_scope_callback, destroy_temporary_db_scope_callback, create_reading_transaction_callback, unmangle_uri_callback, resolve_tiled_resource_uri_callback)
  - class def populate_all_materials(cls, asset_path)
  - class def shutdown(cls)
  - def get_status(self)
  - def get_detailed_error(self)
  - def cancel(self)
