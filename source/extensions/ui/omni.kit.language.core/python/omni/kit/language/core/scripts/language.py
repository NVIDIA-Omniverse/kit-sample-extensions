"""
Font & Language support class
"""

import locale

import carb

# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import omni.ext

__all__ = [
    "LanguageExtension",
    "register_language",
    "unregister_language",
    "get_locale_id",
    "get_default_locale_id",
    "get_language_info",
    "get_locales",
    "has_font_changed",
]
_extension_instance = None


# see https://www.ibm.com/docs/en/rational-soft-arch/9.6.1?topic=overview-locales-code-pages-supported


class LanguageExtension(omni.ext.IExt):
    """
    Font & Language support class
    """

    def __init__(self):
        super().__init__()
        global _extension_instance
        _extension_instance = self

        self._preferences_page = None
        self._registered_languages = {
            "en_US": {
                "language_name": "English",
                "language_name_localized": "English",
                "pangram": "The quick brown fox jumps over the lazy dog",
                "font_path": None,
                "font_scale": 1.0,
                "regions": None,
                "font_overresolution_size": None,
            }
        }

    def on_startup(self, ext_id):
        # setup locale settings
        settings = carb.settings.get_settings()
        current_locale = locale.getdefaultlocale()[0]
        settings.set("/app/locale_id", current_locale)
        current_default_locale = settings.get("/persistent/app/locale_id")
        settings.set("/app/locale_id_default", current_default_locale if current_default_locale else current_locale)
        settings.set_default("/persistent/app/locale_id", current_locale)

        # add preferences window watcher
        manager = omni.kit.app.get_app().get_extension_manager()
        self._hooks = []
        self._hooks.append(
            manager.subscribe_to_extension_enable(
                on_enable_fn=lambda _: self._register_page(),
                on_disable_fn=lambda _: self._unregister_page(),
                ext_name="omni.kit.window.preferences",
                hook_name="omni.kit.language.core omni.kit.window.preferences listener",
            )
        )

        # check .kit settings for languages
        settings_dict = carb.settings.get_settings().get_settings_dictionary("")
        if (
            "ext" in settings_dict
            and "omni.kit.language.core" in settings_dict["exts"]
            and "language" in settings_dict["exts"]["omni.kit.language.core"]
        ):
            lang_dict = settings_dict["exts"]["omni.kit.language.core"]
            lang_list = lang_dict["language"]
            for lang_dict in lang_list if isinstance(lang_list, list) else [lang_list]:
                self.register_language(
                    tuple(lang_dict["locale_info"]),
                    lang_dict["font_path"],
                    lang_dict["font_scale"],
                    lang_dict["regions"],
                    lang_dict["pangram"],
                    lang_dict.get("font_overresolution_size", None),
                )

    def on_shutdown(self):
        global _extension_instance
        _extension_instance = None

        self._unregister_page()

    def _register_page(self):
        from omni.kit.window.preferences import register_page

        from .pages.language_page import LanguagePreferences

        self._preferences_page = register_page(LanguagePreferences())

    def _unregister_page(self):
        if self._preferences_page:
            import omni.kit.window.preferences

            omni.kit.window.preferences.unregister_page(self._preferences_page)
            self._preferences_page = None

    def get_locale_id(self) -> str:
        settings = carb.settings.get_settings()
        return settings.get("/persistent/app/locale_id")

    def switch_language(self) -> bool:
        current_language = self.get_locale_id()
        if current_language in self._registered_languages:
            language_data = self._registered_languages[current_language]
            settings = carb.settings.get_settings()

            # set font path
            if language_data["font_path"]:
                settings.set("/app/font/customFontPath", language_data["font_path"])

            # set customRegionFiles
            custom_region_files = settings.get("/app/font/customRegionFiles")
            if not custom_region_files:
                custom_region_files = []
            if language_data["regions"]:
                for region in language_data["regions"]:
                    custom_region_files.append(region)
            settings.set("/app/font/customRegionFiles", custom_region_files)

            ## set font size
            settings.set("/app/font/scale", language_data["font_scale"])
            if language_data["font_overresolution_size"]:
                settings.set("/app/font/overresolutionSize", language_data["font_overresolution_size"])

            return True
        return False

    def register_language(
        self,
        locale_info: tuple,
        font_path: str,
        font_scale: float,
        regions: list[str],
        pangram: str,
        font_overresolution_size: float = None,
    ) -> bool:
        """
        Registers a new language. (Currently on has font support)

        This function added a new language to the pool of known languages and then
        attempts to switch to the new language if current locale_id matches given locale_id.

        Args:
            locale_info (tuple): contains locale_id, language name and localized language name.
            font_path (str):  path to a font file that will be used instead of default font.
            font_scale (float): additional scaling to font.
            regions (list[str]): list of region files that contain the characters to be used. See kit/source/extensions/omni.kit.renderer.imgui/data/regions/ for an example.
            pangram (str): string containing all the letters in the alphabet. EG. "The quick brown fox jumps over the lazy dog".
            font_overresolution_size (float): override largest font size from default 100. Useful for large font ranges.

        Returns:
            True on success or False in error.
        """
        if not locale_info or not isinstance(locale_info, tuple):
            carb.log_error(
                "register_language: locale_info is not valid. Should be tuple containing locale_id, language name and localized language name."
            )
            return False

        if locale_info[0] in self._registered_languages:
            carb.log_error(f"register_language: locale {locale_info[0]} already in use")
            return False

        self._registered_languages[locale_info[0]] = {
            "language_name": locale_info[1],
            "language_name_localized": locale_info[2],
            "pangram": pangram,
            "font_path": font_path,
            "font_scale": font_scale,
            "regions": regions,
            "font_overresolution_size": font_overresolution_size,
        }
        self.switch_language()
        return True

    def unregister_language(self, locale_id: str) -> bool:
        """
        Unregisters a new language.

        This function removed a language to the pool of known languages.

        Args:
            locale_id (str): EG. "en_US"

        Returns:
            True on success or False on failure.
        """
        if locale_id in self._registered_languages:
            del self._registered_languages[locale_id]
            return True
        return False

    def get_language_info(self, locale_id) -> dict:
        """
        Get registered information about language.

        Args:
            locale_id (str): EG. "en_US"
        Returns:
            locale info dictionary (dict)
        """
        if locale_id in self._registered_languages:
            return self._registered_languages[locale_id]
        return None

    def get_locales(self) -> list[str]:
        """
        Get list of registered locale names.

        Returns:
            list of known locales (list[str])
        """
        return self._registered_languages.keys()

    def has_font_changed(self, locale_id: str) -> bool:
        """
        Compares default_locale_id with locale_id and returns True/False.

        Args:
            locale_id (str): EG. "en_US"
        Returns:
            True is locale info is different to current locale info (bool)
        """
        default_info = get_language_info(get_default_locale_id())
        new_info = get_language_info(locale_id)
        if not default_info or not new_info:
            return True
        if (
            default_info["font_path"] == new_info["font_path"]
            and default_info["font_scale"] == new_info["font_scale"]
            and default_info["regions"] == new_info["regions"]
        ):
            return False
        return True


def get_locale_id() -> str:
    """
    Get current locale name. EG. "en_US"

    Returns:
        locale name (str)
    """
    if _extension_instance:
        return _extension_instance.get_locale_id()


def get_default_locale_id() -> str:
    """
    Get the locale name that kit used when started. EG. "en_US"

    Returns:
        locale name (str)
    """
    return carb.settings.get_settings().get("/app/locale_id_default")


def register_language(
    locale_info: tuple,
    font_path: str,
    font_scale: float,
    regions: list[str],
    pangram: str,
    font_overresolution_size: float = None,
) -> bool:
    """
    Registers a new language.

    This function added a new language to the pool of known languages and then
    attempts to switch to the new language if current locale_id matches given locale_id.

    Args:
        locale_info (tuple): contains locale_id, language name and localized language name.
        font_path (str):  path to a font file that will be used instead of default font.
        font_scale (float): additional scaling to font.
        regions (list[str]): list of region files that contain the characters to be used. See kit/source/extensions/omni.kit.renderer.imgui/data/regions/ for an example.
        pangram (str): string containing all the letters in the alphabet. EG. "The quick brown fox jumps over the lazy dog".
        font_overresolution_size (float): override largest font size from default 100. Useful for large font ranges.

    Returns:
            True on success or False in error.
    """
    if _extension_instance:
        return _extension_instance.register_language(
            locale_info, font_path, font_scale, regions, pangram, font_overresolution_size
        )


def unregister_language(locale_id: str) -> bool:
    """
    Unregisters a new language.

    This function removed a language to the pool of known languages.

    Args:
        locale_id (str): EG. "en_US"

    Returns:
        True on success or False on failure.
    """
    if _extension_instance:
        return _extension_instance.unregister_language(locale_id)


def get_language_info(locale_id) -> dict:
    """
    Get registered information about language.

    Args:
        locale_id (str): EG. "en_US"
    Returns:
        locale info dictionary (dict)
    """
    if _extension_instance:
        return _extension_instance.get_language_info(locale_id)


def get_locales() -> list[str]:
    """
    Get list of registered locale names.

    Returns:
        list of known locales (list[str])
    """
    if _extension_instance:
        return _extension_instance.get_locales()


def has_font_changed(locale_id: str) -> bool:
    """
    Compares default_locale_id with locale_id and returns True/False.

    Args:
        locale_id (str): EG. "en_US"
    Returns:
        True is locale info is different to current locale info (bool)
    """
    if _extension_instance:
        return _extension_instance.has_font_changed(locale_id)
