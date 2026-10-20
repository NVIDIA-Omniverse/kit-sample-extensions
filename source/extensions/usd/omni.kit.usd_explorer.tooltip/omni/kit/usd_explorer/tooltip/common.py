from pathlib import Path

import carb.tokens

DATA_PATH = Path(carb.tokens.get_tokens_interface().resolve("${omni.kit.usd_explorer.tooltip}/data"))
ICON_PATH = DATA_PATH.joinpath("icons")


def get_icon_path(file):
    return f"{ICON_PATH}/{file}"
