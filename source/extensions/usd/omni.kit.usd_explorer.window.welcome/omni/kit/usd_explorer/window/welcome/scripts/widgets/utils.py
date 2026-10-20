import os
from pathlib import Path

import carb


def is_server_file(file_path):
    return file_path.startswith("omniverse:")


def get_icon_path(icon_file):
    icon_folder = os.path.abspath(
        carb.tokens.get_tokens_interface().resolve("${omni.kit.usd_explorer.window.welcome}/icons")
    )
    icon_folder = Path(icon_folder)
    if Path.exists(icon_folder):
        return icon_folder.joinpath(icon_file).as_posix()
    carb.log_error(f"Can not find icon path for {icon_file}")
    return ""
