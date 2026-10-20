"""Traditional Chinese language extension that registers Traditional Chinese font support and language settings for Omniverse Kit applications."""

import carb
import omni.ext

__all__ = ["TraditionalChineseLanguageExtension"]


class TraditionalChineseLanguageExtension(omni.ext.IExt):
    """Implementation of Traditional Chinese font"""

    def on_startup(self, ext_id):
        """Initializes the Traditional Chinese language extension by registering the Traditional Chinese language with the Omniverse language system.

        Args:
            ext_id (str): Extension identifier for the startup process.
        """
        super().__init__()

        # decide on font size.
        font_size = carb.settings.get_settings().get("/app/font/size")
        extension_path = omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
        omni.kit.language.core.register_language(
            ("zh-TW", "Chinese (Traditional)", "繁体字"),
            f"{extension_path}/data/fonts/NotoSansTC-SemiBold.ttf",
            1.2 if font_size == 14 or font_size == None else 1.0,
            [
                f"{extension_path}/data/regions/TC_Big5_UTF8.txt",
                f"{extension_path}/data/regions/TC_Big5_UTF82.txt",
                f"{extension_path}/data/regions/TC_Big5_UTF83.txt",
                f"{extension_path}/data/regions/TC_Big5_UTF84.txt",
                f"{extension_path}/data/regions/TC_Big5_UTF85.txt",
                f"{extension_path}/data/regions/TC_Big5_UTF86.txt",
            ],
            "君子不器，學而時習之？不亦說乎，己所不欲勿施於人，知之者不如好者，好之者不如樂之者，巧言令色，鮮矣仁，人之過也，各於其黨，觀過斯知仁矣",
            font_overresolution_size=66,
        )

    def on_shutdown(self):
        """Cleans up the Traditional Chinese language extension by unregistering the language from the Omniverse language system."""
        omni.kit.language.core.unregister_language("zh-CN")
