# Public API for module omni.kit.environment.core:

## Classes

- class SunstudyPlayer
  - def __init__(self)
  - def destroy(self)
  - [property] def latitude(self) -> float
  - [latitude.setter] def latitude(self, value: float)
  - [property] def longitude(self) -> float
  - [longitude.setter] def longitude(self, value: float)
  - [property] def north_orientation(self) -> float
  - [north_orientation.setter] def north_orientation(self, value: float)
  - [property] def current_time(self) -> float
  - [current_time.setter] def current_time(self, value: float)
  - [property] def start_time(self) -> float
  - [start_time.setter] def start_time(self, value: float)
  - [property] def end_time(self) -> float
  - [end_time.setter] def end_time(self, value: float)
  - [property] def current_date(self) -> str
  - [current_date.setter] def current_date(self, value: str)
  - def start(self) -> bool
  - def stop(self)
  - def update_fix_timezone(self, need_fix_timezone: bool)

- class SunstudySkyType
  - NONE: str
  - DYNAMIC: str
  - STATIC: str

- class PlayButton(SettingButton)
  - def __init__(self, player: SunstudyPlayer, style = PLAY_STYLES, show_notification = True, **kwargs)

- class PlayRateButton(SettingButton)
  - def __init__(self, style = PLAY_STYLES, **kwargs)

- class PlayLoopButton(SettingButton)
  - def __init__(self, style = PLAY_STYLES, **kwargs)

- class SunstudyTimeSlider(TimeSliderBar)
  - def __init__(self, on_datetime_changed_fn: Callable[[str], None] = None, style: Dict = {})
  - def destroy(self)

- class CityComboBox(ui.ComboBox)
  - def __init__(self, **kwargs)

- class CityModel(ui.AbstractItemModel)
  - def __init__(self)
  - [property] def current_index(self) -> int
  - [current_index.setter] def current_index(self, value: int)
  - def set_location(self, longitude: float, latitude: float)
  - def get_item_value_model(self, item: Optional[LocationItem] = None, column_id = 0) -> ui.AbstractValueModel
  - def get_item_children(self, item = None) -> List[LocationItem]
  - def get_item_value_model_count(self, item = None) -> int

- class Clock
  - def __init__(self, model: ui.AbstractValueModel)
  - def on_update(self, dt)

- class ResetButton
  - def __init__(self, model: BaseValueModel)

- class UsdModelBuilder
  - def __init__(self)
  - def destroy(self)
  - def create_property_value_model(self, property_path: str, value_type: Sdf.ValueTypeName = Sdf.ValueTypeNames.String, default: Any = '', min: Union[int, float, None] = None, max: Union[int, float, None] = None, default_prim_type: Optional[str] = None) -> PropertyValueModel
  - def create_prim_value_model(self, prim_path: str) -> PrimValueModel
  - def register_prim_callback(self, prim_path: str, on_prim_changed_fn: Callable[[Usd.Stage, str], None])
  - def start(self, stage: Usd.Stage)
  - def stop(self)

- class PropertyValueModel(BaseValueModel)
  - def __init__(self, property_path: str, stage: Usd.Stage, value_type: Sdf.ValueTypeName = Sdf.ValueTypeNames.String, default: Any = '', min: Union[int, float, None] = None, max: Union[int, float, None] = None, default_prim_type: Optional[str] = None)
  - def destroy(self)
  - def set_value(self, value: Any)
  - def get_value_as_string(self) -> str
  - def get_value_as_float(self) -> float
  - def get_value_as_bool(self) -> bool
  - def get_value_as_int(self) -> int
  - def on_property_changed(self, stage: Usd.Stage)

- class SettingModel(BaseValueModel)
  - def __init__(self, setting_path: str, draggable: bool = False)
  - def destroy(self)
  - def begin_edit(self)
  - def end_edit(self)
  - def get_value_as_string(self) -> str
  - def get_value_as_float(self) -> float
  - def get_value_as_bool(self) -> bool
  - def get_value_as_int(self) -> int
  - def set_value(self, value: Any)

- class SceneTemplateHelper
  - def __init__(self, context_name: str = '')
  - def add_on_apply_scene_template_fn(self, on_apply_scene_template_fn: Callable[[str], None])
  - def get_scene_template_url(self, stage: Usd.Stage = None) -> str
  - def save_scene_template_url(self, url: str, stage: Usd.Stage = None)
  - def get_scene_template_layer(self, stage: Usd.Stage = None) -> Sdf.Layer
  - def get_edit_context(self, stage: Optional[Usd.Stage] = None) -> Usd.EditContext
  - def save(self, url: Optional[str] = None, on_save_done: Callable = None) -> bool
  - def save_as(self, on_save_done: Callable = None)
  - def apply_scene_template(self, url) -> str
  - def remove_current_scene_template(self)

- class SkyHelper
  - def __init__(self)
  - def destroy(self)
  - static def get_env_file_type(url: str) -> Optional[SkyType]
  - static def find_sky(root_path: str = ENVIRONMENT_PRIM_ROOT) -> Tuple[Optional[str], Optional[str]]
  - static def create_hdri_sky(url: str, sky_path: str = SKY_PRIM_PATH) -> str
  - static def create_dynamic_sky(url: str, sky_path = SKY_PRIM_PATH) -> str

- class SkyType
  - HDRI: str
  - DYNAMIC: str
  - SCENE: str

- class EnvironmentProperties
  - LATITUDE: Unknown
  - LONGITUDE: Unknown
  - NORTH_ORIENTATION: Unknown
  - CUMULUS_ENABLED: Unknown
  - CLOUD_COVERAGE: Unknown
  - HAZE: Unknown
  - TIME_START: Unknown
  - TIME_END: Unknown
  - TIME_CURRENT: Unknown
  - DATE: Unknown
  - GROUND_SIZE: Unknown
  - GROUND_TYPE: Unknown
  - GROUND_MATERIAL_PATH: Unknown
  - GROUND_MATERIAL_STRENGTH: Unknown
  - SCENE_TEMPLATE: Unknown

- class EnvironmentSettings
  - ROOT: str
  - ENV_ROOT: Unknown
  - ENV_AUTO: Unknown
  - ENV_DEFAULT: Unknown
  - GROUND_ROOT: Unknown
  - GROUND_ENABLE: Unknown
  - GROUND_MATERIAL: Unknown
  - GROUND_SUB_MATERIAL: Unknown
  - SHOW_LIGHT_WARNING: Unknown

- class PlaySettings
  - ROOT: str
  - ENABLE: Unknown
  - PLAYING: Unknown
  - RATE: Unknown
  - LOOP: Unknown
  - CURRENT_SKY_PATH: Unknown
  - CURRENT_SKY_TYPE: Unknown

- class GroundSettings
  - ROOT: str
  - PATH: Unknown

- class GroundType
  - OFF: str
  - ON: str
  - SHADOWS: str

- class GroundHelper
  - def __init__(self)
  - def destroy(self)
  - def find_ground(self, root_path: str = ENVIRONMENT_PRIM_ROOT) -> Optional[Usd.Prim]
  - [property] def ground_prim(self) -> Optional[Usd.Prim]
  - [ground_prim.setter] def ground_prim(self, prim: Optional[Usd.Prim])
  - [property] def ground_material(self) -> Optional[str]
  - def update_ground_material(self, material_path: str)

## Functions

- def get_sunstudy_player() -> SunstudyPlayer
- def import_environment(type: SkyType, url: str) -> str

## Variables

- ENVIRONMENT_PRIM_ROOT: str
- ENVIRONMENT_MATERIALS_ROOT: Unknown
- GROUND_DEFAULT_SIZE: int
