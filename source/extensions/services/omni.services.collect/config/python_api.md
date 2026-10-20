# Public API for module omni.services.collect:

## Classes

- class ServiceConvertAssetExtension(omni.ext.IExt)
  - def on_startup(self)
  - def on_shutdown(self)

## Other

- omni.ext: public module
- main: public module


# Public API for module omni.services.collect.services.collect:

## Classes

- class Collector
  - def __init__(self, usd_path: str, collect_dir: str, usd_only: bool = False, flat_collection: bool = False, material_only: bool = False, failure_options = CollectorFailureOptions.SILENT, skip_existing: bool = False, max_concurrent_tasks = 32, texture_option = FlatCollectionTextureOptions.BY_MDL, force_non_read_only = True, exclusion_rules = {}, default_prim_only = False, **kwargs)
  - def destroy(self)
  - [property] def target_folder(self) -> str
  - [property] def source_stage_url(self) -> str
  - [property] def collect_mapping_file_url(self)
  - def get_target_url(self, source_url: str) -> str
  - def get_source_target_url_mapping(self) -> Dict[str, str]
  - def is_copy_skipped(self, source_url) -> bool
  - async def open_or_create_layer(self, layer_path, clear = True)
  - async def add_copy_task(self, source: str, target: str, skip_if_existed = False)
  - async def add_write_task(self, target: str, content: Union[str, bytes])
  - async def wait_all_unfinished_tasks(self, all_completed = False)
  - def get_status(self) -> CollectorStatus
  - def is_finished(self)
  - def is_cancelled(self)
  - def cancel(self)
  - async def collect(self, progress_callback: Callable[[int, int], None] = None, finish_callback: Callable[[], None] = None) -> Tuple[bool, str]

- class MetricsFacility(base.Facility)
  - def __init__(self, service: str)
  - def gauge(self, name, documentation, **kwargs)
  - def histogram(self, name, documentation, **kwargs)
  - def counter(self, name, documentation, **kwargs)
  - def summaries(self, name, documentation, **kwargs)
  - def infos(self, name, documentation, **kwargs)
  - def enums(self, name, documentation, **kwargs)

- class ProgressFacility(base.Facility)
  - def __init__(self)
  - def stop(self)
  - def set_progress(self, current_step_index: int, total_step_count: int, progress: Optional[float] = None, status_message: Optional[str] = None, time_remaining: Optional[float] = None)

- class S3Collector(BaseUploadCollector)
  - def __init__(self, usd_path: str, collect_dir: str, usd_only: bool, flat_collection: bool, material_only: bool, s3_bucket: str, aws_region: str = None, aws_profile: str = None, aws_verify_ssl: Union[str, bool] = None, ignore_missing_assets: bool = True)

- class RequestCollectModel(pydantic.BaseModel)
  - usd_path: str
  - collect_dir: str
  - usd_only: bool
  - flat_collection: bool
  - material_only: bool

- class S3RequestCollectModel(RequestCollectModel)
  - aws_region: str
  - aws_profile: str
  - s3_bucket: str
  - ignore_missing_assets: bool

- class ProgressMonitor(object)
  - def __init__(self, progress_facility: ProgressFacility)
  - def progress(self, step, total_steps)
  - def finished(self)

## Functions

- async def asset_collect(req: RequestCollectModel, metrics: MetricsFacility = router.get_facility('metrics'), progress_facility: ProgressFacility = router.get_facility('progress'))
- async def asset_collect_s3(req: S3RequestCollectModel, metrics: MetricsFacility = router.get_facility('metrics'), progress_facility: ProgressFacility = router.get_facility('progress'))

## Variables

- router: Unknown

## Other

- os: builtin module
- carb: public module
- carb.settings: public module
- pydantic: unknown module
- routers: internal module
