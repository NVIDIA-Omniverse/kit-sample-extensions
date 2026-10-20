from pathlib import Path

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("icons")

UI_STYLE = {
    "Menu.Button.Image::Waypoint": {"image_url": f"{ICON_PATH}/Waypoint.svg"},
    "Menu.Button.Image::Waypoint:checked": {"color": 0xFFFFC734},
    "Menu.Button.Image::Waypoint:selected": {"color": 0xFFFFC734},
}
