# Omniverse Services Log Facilities [omni.services.facilities.log]

## About

Omniverse Services Log Facilities, exposing foundations for Facilities offering logging capabilities including timestamps, severity, as well as contextual information.

## Available Log Facilities

The following Log Facilities are available by default in this extension, allowing Service authors to benefit from documented, tested and maintained APIs that are used in production.

In order to use these Facilities as part of extensions, Service authors may wish to do so using the following pattern:

```python
import omni.ext

from omni.services.core.main import deregister_router, register_router
from omni.services.facilities.log import PythonLogFacility

from .services.render import router


class DemoExtension(omni.ext.IExt):
    """Sample extension demonstrating registration of a Log Facility."""

    def on_startup(self, ext_id: str) -> None:
        # Instantiate an instance of the Python Log Facility to be used by the
        # Service implemented in the imported `router`:
        log_facility = PythonLogFacility()
        # Register the Python Log Facility on the router, to make it available
        # to endpoints defined by the Service:
        router.register_facility(name="log", facility_inst=log_facility)
        # Register the router implementing the Service to the application:
        register_router(router=router, prefix="/demo", tags=["demo"])

    def on_shutdown(self) -> None:
        # When disabling the extension, deregister the router from the
        # application:
        deregister_router(router=router, prefix="/demo")
```

### Python Log Facility (`omni.services.facilities.log.PythonLogFacility`)

Facility using the native Python `logging` module in order to record messages to the application log.

Omniverse best practices recommend using this approach for Python logging, as Omniverse applications respect the verbosity level provided to the `logging` module in order to manage the flow of messages streamed to the log and displayed to the User. Omniverse applications additionally map these calls back to the equivalent Carbonite APIs, making it suitable for existing implementation already leveraging `carb.log_*(message)` events for internal logic.

|`PythonLogFacility` API|Equivalent Carbonite API|
|---|---|
|`PythonLogFacility.verbose("message")`|`carb.log_verbose("message")`|
|`PythonLogFacility.info("message")`|`carb.log_info("message")`|
|`PythonLogFacility.warning("message")`|`carb.log_warn("message")`|
|`PythonLogFacility.error("message")`|`carb.log_error("message")`|
|`PythonLogFacility.fatal("message")`|`carb.log_fatal("message")`|

### Carbonite Log Facility (`omni.services.facilities.log.CarbLogFacility`)

Facility using Carbonite log features in order to record messages to the application log.

Supports the following APIs, mapped to the equivalent `carb.log_*("message")` Python code:

|`CarbLogFacility` API|Equivalent Carbonite API|
|---|---|
|`CarbLogFacility.debug("message")`|`carb.log_verbose("message")`|
|`CarbLogFacility.info("message")`|`carb.log_info("message")`|
|`CarbLogFacility.warning("message")`|`carb.log_warn("message")`|
|`CarbLogFacility.error("message")`|`carb.log_error("message")`|
|`CarbLogFacility.exception("message")`|`carb.log_error("message")`|
