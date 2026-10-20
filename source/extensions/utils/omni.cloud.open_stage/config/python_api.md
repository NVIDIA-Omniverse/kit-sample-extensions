# Public API for module omni.cloud.open_stage:

## Classes

- class CloudOpenExtension(omni.ext.IExt)
  - def on_startup(self, ext_id)
  - def on_shutdown(self)

## Functions

- def get_session_status() -> dict
- async def open_stage_async(path: str)
- async def get_endpoint_performance()
