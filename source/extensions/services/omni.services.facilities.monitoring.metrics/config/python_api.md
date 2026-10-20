# Public API for module omni.services.facilities.monitoring.metrics:

## Classes

- class MetricsExtension(omni.ext.IExt)
  - def __init__(self)
  - def on_startup(self)
  - def on_shutdown(self)
  - async def push_metrics(self, gateway, job, registry, interval)

## Other

- asyncio: builtin module
- carb: public module
- carb.settings: public module
- omni.ext: public module
- prometheus_client: unknown module
- main: public module
