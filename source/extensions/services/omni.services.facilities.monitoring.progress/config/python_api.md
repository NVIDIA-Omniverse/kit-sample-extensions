# Public API for module omni.services.facilities.monitoring.progress:

## Classes

- class ProgressStore(object)
  - def __init__(self)
  - def update_progress(self, current_step_index: int, total_step_count: int, progress: Optional[float] = None, status_message: Optional[str] = None, time_remaining: Optional[float] = None)
  - def get_progress(self) -> Dict

- class ProgressExtension(omni.ext.IExt)
  - def on_startup(self, ext_id)
  - def on_shutdown(self)

## Variables

- router: Unknown

## Other

- omni.ext: public module
- main: public module
