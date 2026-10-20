from pathlib import Path

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("icons")

UI_STYLE = {
    "Menu.Button.Image::Markup": {"image_url": f"{ICON_PATH}/Markup.svg"},
    "Menu.Button.Image::Markup:checked": {"color": 0xFFFFC734},
    "Menu.Button.Image::Markup:selected": {"color": 0xFFFFC734},
}
