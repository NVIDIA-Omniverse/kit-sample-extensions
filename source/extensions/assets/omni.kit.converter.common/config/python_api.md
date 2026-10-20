# Public API for module omni.kit.converter.common:

## Classes

- class ICadExtBase(omni.ext.IExt)
  - DELEGATE: NoneType
  - FILTER_DATA: NoneType
  - def __init__(self)
  - def get_ext_name(self) -> str
  - def get_ext_path(self) -> Path
  - def get_ext_version(self) -> str
  - def get_filters(self) -> List[ConverterFilterData]

- class ICadCoreExtBase(omni.ext.IExt)
  - FILTER_DATA: NoneType
  - OPTIONS_CLS: NoneType
  - SERVICE_TITLE: NoneType
  - def get_converter_registry(self) -> Optional[ConverterRegistry]
  - def get_ext_name(self) -> str
  - def get_ext_path(self) -> Path
  - def get_ext_version(self) -> str
  - def get_filters(self) -> List[ConverterFilterData]

- class ConverterStatus(NamedTuple)
  - error_code: int
  - error_msg: str

- class ConverterFilterData
  - name: str
  - filter_regexes: List[str]
  - filter_descriptions: List[str]
  - priority: int

- class UsdSuffix(str, Enum)
  - USD: str
  - USDC: str
  - USDA: str

- class OmniClientWrapper
  - static async def exists(path)
  - static def exists_sync(path)
  - static async def write(path: str, content)
  - static async def copy(src_path: str, dest_path: str)
  - static def copy_sync(src_path: str, dest_path: str)
  - static async def read(src_path: str)
  - static async def create_folder(path)
  - static def create_folder_sync(path)

- class OmniUrl
  - def __init__(self, url: Union[str, Path], list_entry = None)
  - [property] def scheme(self)
  - def get_local_file(self) -> Path
  - async def get_local_file_async(self) -> tuple[omni.client.Result, Path]
  - def sync_stat(self)
  - [property] def stat(self)
  - [property] def exists(self)
  - [property] def writeable(self)
  - [property] def path(self)
  - [property] def parent_url(self) -> OmniUrl
  - [property] def name(self) -> str
  - [property] def stem(self) -> str
  - [property] def suffix(self) -> str
  - [property] def full_suffix(self) -> str
  - def url_with_path(self, path: Path) -> OmniUrl
  - def url_with_name(self, name: str) -> OmniUrl
  - def url_with_suffix(self, suffix: str) -> OmniUrl

- class ProgressStepType(Enum)
  - UNKNOWN: int
  - BEGIN: int
  - PROGRESS: int
  - END: int

- class ProgressLogConsumer
  - def __init__(self, log_prefix: str)
  - def extract_line(self, msg: str)

- class BackendLogConsumer
  - def __init__(self, log_prefix: str)
  - def should_process(self, msg: str) -> bool
  - def process_line(self, msg: str)

- class CoreExtLogConsumer
  - def __init__(self, source_ext_name: str)
  - def process_line(self, line: str) -> bool

## Functions

- def run_scene_opt(output_path: str, sceneOpGenerateUVs: bool, convertHidden: bool, sceneOpConfig: str = '', sceneOpMetersPerUnit: float = 0.0, sceneOpUpAxis: int = 0)
- async def copy_output_assets(source_path: str, output_path: str)
- def validate_file_path(file_path: str) -> Optional[str]
- def strip_file_regex(input_path: Path, file_regex_patterns) -> str
- def is_asset_supported(path: str, filters: typing.List[str]) -> bool
- def config_path_to_args(config_path: str) -> dict
- def dict_to_args(config_data: dict) -> dict
