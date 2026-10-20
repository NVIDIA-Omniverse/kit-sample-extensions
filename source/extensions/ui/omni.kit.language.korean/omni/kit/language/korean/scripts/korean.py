"""Provides Korean language support for the Omniverse Kit SDK through font registration and text rendering configuration."""

import carb
import omni.ext

__all__ = ["KoreanLanguageExtension"]


class KoreanLanguageExtension(omni.ext.IExt):
    """Implementation of Korean font support for the Omniverse Kit SDK.

    This extension registers Korean language support with custom fonts and text regions,
    enabling Korean text rendering throughout the application interface.
    """

    def on_startup(self, ext_id):
        """Initializes the Korean language extension by registering Korean language support.

        Registers Korean language with font configuration, scaling factors, and character regions
        for proper text rendering in the application.

        Args:
            ext_id (str): Extension identifier for the Korean language extension.
        """
        super().__init__()

        # decide on font size.
        font_size = carb.settings.get_settings().get("/app/font/size")
        extension_path = omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
        omni.kit.language.core.register_language(
            ("ko-KR", "Korean", "한국어"),
            f"{extension_path}/data/fonts/NotoSansKR-SemiBold.ttf",
            1.2 if font_size == 14 or font_size == None else 1.0,
            [
                f"{extension_path}/data/regions/Korean.txt",
                f"{extension_path}/data/regions/Korean_2.txt",
            ],
            "다람쥐 헌 쳇바퀴에 타고파",
            font_overresolution_size=66,
        )

    def on_shutdown(self):
        """Shuts down the Korean language extension by unregistering Korean language support.

        Removes Korean language registration from the language core system.
        """
        omni.kit.language.core.unregister_language("ko-KR")
