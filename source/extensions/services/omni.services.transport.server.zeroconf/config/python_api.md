# Public API for module omni.services.transport.server.zeroconf:

## Classes

- class ZeroConf(omni.ext.IExt)
  - def __init__(self)
  - def on_startup(self)
  - def on_shutdown(self)
  - def add(self, service: str, port: int)
  - def remove(self, service: str, port: int)
  - class def ipAddresses(cls) -> list[str]
