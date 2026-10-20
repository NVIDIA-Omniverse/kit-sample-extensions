# Public API for module omni.services.facilities.log:

## Classes

- class CarbLogFacility(_facilities.Facility)
  - def __init__(self)

- class Facility
  - def stop(self)

- class PythonLogFacility(Facility)
  - def __init__(self, logger_name: Optional[str] = None)
  - def stop(self)
  - def verbose(self, message: str)
  - def info(self, message: str)
  - def warning(self, message: str)
  - def error(self, message: str)
  - def fatal(self, message: str)
  - def get_logger(self) -> Logger

## Other

- carb: public module
- omni.services.facilities.base: public module
- Logger: unknown
- getLogger: unknown
- Any: unknown
- Callable: unknown
- Dict: unknown
- Optional: unknown
