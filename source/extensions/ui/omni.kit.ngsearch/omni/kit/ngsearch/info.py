import os
from typing import Any, Dict

import toml

bin_path = os.path.abspath(os.path.dirname(__file__))
ext_source_path = f"{bin_path}/../../.."


def get_package_info() -> Dict[str, Any]:
    return toml.load(f"{ext_source_path}/config/extension.toml", _dict=dict)["package"]
