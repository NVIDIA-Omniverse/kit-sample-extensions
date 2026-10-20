# Public API for module omni.services.render:

## Classes

- class CarbLogFacility(_facilities.Facility)
  - def __init__(self)

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

- class ServiceRenderExtension(omni.ext.IExt)
  - def on_startup(self, ext_id: str)
  - def on_shutdown(self)

## Functions

- def deregister_router(router: routers.ServiceAPIRouter, prefix: str = None)
- def register_router(router: routers.ServiceAPIRouter, **kwargs: Optional[Any])

## Variables

- router: Unknown

## Other

- omni.ext: public module
