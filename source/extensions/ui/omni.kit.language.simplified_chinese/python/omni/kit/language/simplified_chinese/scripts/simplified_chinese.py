import carb
import omni.ext

__all__ = ["SimplifiedChineseLanguageExtension"]


class SimplifiedChineseLanguageExtension(omni.ext.IExt):
    """
    Implementation of Simplified Chinese font
    """

    def on_startup(self, ext_id):
        super().__init__()
        settings = carb.settings.get_settings()
        use_common_chinese = settings.get("/exts/omni.kit.language.simplified_chinese/use_common_chinese")
        # OMPE-101379: default to bounded Common_Chinese so the atlas fits D3D12's 16384px cap.
        if use_common_chinese is None:
            use_common_chinese = True
        use_vulkan = settings.get("/app/vulkan")
        # decide on font size.
        font_size = settings.get("/app/font/size")
        target_font_size = 1.2 if font_size == 14 or font_size == None else 1.0
        extension_path = omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
        font_overresolution_size = 66
        region_base = "Common_Chinese" if use_common_chinese else "Chinese"
        regions = [f"{extension_path}/data/regions/{region_base}.txt"] + [
            f"{extension_path}/data/regions/{region_base}_GBK_UTF8{i}.txt" for i in range(2, 10)
        ]
        if not use_vulkan:
            # OMPE-58932: when not using vulkan, the font texture is too large and over the limit of the direct3d12
            # so we use a smaller size  to reduce the font texture size
            # (or could use common chinese set, but 44 is enough for most cases)
            font_overresolution_size = 44

        omni.kit.language.core.register_language(
            ("zh-CN", "Chinese (simplified)", "简体字"),
            f"{extension_path}/data/fonts/NotoSansSC-SemiBold.ttf",
            target_font_size,
            regions,
            "君子不器 学而时习之、不亦说乎 己所不欲勿施于人 知之者不如好之者、好之者不如乐之者 巧言令色、鲜矣仁 人之过也、各于其党、观过、斯知仁矣",
            # full chinese font texture is too large, so we use a smaller size
            font_overresolution_size=font_overresolution_size,
        )

    def on_shutdown(self):
        omni.kit.language.core.unregister_language("zh-CN")
