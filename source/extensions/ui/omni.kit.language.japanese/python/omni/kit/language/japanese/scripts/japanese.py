import carb
import omni.ext

__all__ = ["JapaneseLanguageExtension"]


class JapaneseLanguageExtension(omni.ext.IExt):
    """
    Implementation of Japanese font
    """

    def on_startup(self, ext_id):
        super().__init__()

        font_size = carb.settings.get_settings().get("/app/font/size")
        extension_path = omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
        omni.kit.language.core.register_language(
            ("ja_JP", "Japanese", "日本語"),
            f"{extension_path}/data/fonts/NotoSansJP-SemiBold.ttf",
            1.2 if font_size == 14 or font_size == None else 1.0,
            [
                f"{extension_path}/data/regions/japanese.txt",
                f"{extension_path}/data/regions/japanese_extended.txt",
                f"{extension_path}/data/regions/japanese_extended2.txt",
                f"{extension_path}/data/regions/japanese_extended3.txt",
                f"{extension_path}/data/regions/japanese_extended4-1.txt",
            ],
            "いろはにほへと ちりぬるを わかよたれそ つねならむ うゐのおくやま けふこえて あさきゆめみし ゑひもせす",
            font_overresolution_size=66,
        )

    def on_shutdown(self):
        omni.kit.language.core.unregister_language("ja_JP")
