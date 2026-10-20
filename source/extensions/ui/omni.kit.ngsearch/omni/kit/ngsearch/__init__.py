from typing import Any, Dict

from .extension import NGSearchExtension
from .info import get_package_info

__package_info__: Dict[str, Any] = get_package_info()
__version__ = __package_info__["version"]

__all__ = ["NGSearchExtension"]
