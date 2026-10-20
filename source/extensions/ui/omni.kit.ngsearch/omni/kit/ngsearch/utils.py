from contextlib import contextmanager
from enum import Enum
from time import time
from typing import Optional

import carb


class LogLevel(str, Enum):
    info = "info"
    debug = "debug"
    error = "error"
    warning = "warning"


def log_message(message: str, level: Optional[LogLevel] = None):
    if level is None or level == LogLevel.info:
        carb.log_info(message)
    elif level == LogLevel.debug:
        carb.log_verbose(message)
    elif level == LogLevel.error:
        carb.log_error(message)
    elif level == LogLevel.warning:
        carb.log_warn(message)
    else:
        carb.log_warn(f"Unknown log level: {level}")
        carb.log_info(message)


@contextmanager
def timer(message: Optional[str] = None, level: Optional[LogLevel] = None):
    start = time()
    try:
        yield
    finally:
        if message is not None:
            log_message(message=f"{message} in {time() - start:.03}s", level=level)
        else:
            log_message(message=f"Elapsed {time() - start:.03}s", level=level)
