# Omniverse Language & Font extension [omni.kit.language.core]

This extension has support for changing font.

```python
omni.kit.language.core.register_language(("ja_JP", "Japanese", "日本語"),
                                         f"{extension_path}/data/fonts/NotoSansJP-SemiBold.ttf",
                                         1.2,
                                         [ f"{extension_path}/data/regions/japanese.txt", f"{extension_path}/data/regions/japanese_extended.txt" ],
                                         "いろはにほへと ちりぬるを わかよたれそ つねならむ うゐのおくやま けふこえて あさきゆめみし ゑひもせす",
                                         font_overresolution_size=66)
```
