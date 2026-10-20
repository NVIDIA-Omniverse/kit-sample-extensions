# Public API for module omni.kit.language.core:

## Classes

- class LanguageExtension(omni.ext.IExt)
  - def __init__(self)
  - def on_startup(self, ext_id)
  - def on_shutdown(self)
  - def get_locale_id(self) -> str
  - def switch_language(self) -> bool
  - def register_language(self, locale_info: tuple, font_path: str, font_scale: float, regions: list[str], pangram: str, font_overresolution_size: float = None) -> bool
  - def unregister_language(self, locale_id: str) -> bool
  - def get_language_info(self, locale_id) -> dict
  - def get_locales(self) -> list[str]
  - def has_font_changed(self, locale_id: str) -> bool

## Functions

- def register_language(locale_info: tuple, font_path: str, font_scale: float, regions: list[str], pangram: str, font_overresolution_size: float = None) -> bool
- def unregister_language(locale_id: str) -> bool
- def get_locale_id() -> str
- def get_default_locale_id() -> str
- def get_language_info(locale_id) -> dict
- def get_locales() -> list[str]
- def has_font_changed(locale_id: str) -> bool
