# Overview

## Omniverse Language & Font extension [omni.kit.language.core]

This extension has support for changing font.

```python
omni.kit.language.core.register_language(("ja_JP", "Japanese", "日本語"),
                                         f"{extension_path}/data/fonts/NotoSansJP-SemiBold.ttf",
                                         1.2,
                                         [ f"{extension_path}/data/regions/japanese.txt", f"{extension_path}/data/regions/japanese_extended.txt" ],
                                         "いろはにほへと ちりぬるを わかよたれそ つねならむ うゐのおくやま けふこえて あさきゆめみし ゑひもせす",
                                         font_overresolution_size=66)
```

## Change locale_id from python

You can set current locale_id via setting "/persistent/app/locale_id", EG.

```python
carb.settings.get_settings().set("/persistent/app/locale_id", "de_DE")
```

But you will have to re-start kit or set in .kit file as this has to be used before the font is loaded.


## Change locale_id from .kit file

You can force current locale_id via setting "persistent.app.locale_id", EG.

```
[settings.persistent]
app.locale_id = "ja_JP"
```

NOTE: This will be changeable in Language Preferences but .kit file will always reset the value when kit restarts.


## Add language from .kit file

```
[[settings.exts."omni.kit.language.core".language]]
name = "Japanese"
locale_info = ["ja_JP", "Japanese", "日本語"]
font_path = "${fonts}/NotoSansJP-SemiBold.ttf"
font_scale = 1.2
regions = ["${kit}/exts/omni.kit.renderer.imgui/data/regions/japanese.txt", "${kit}/exts/omni.kit.renderer.imgui/data/regions/japanese_extended.txt"]
pangram = "いろはにほへと ちりぬるを わかよたれそ つねならむ うゐのおくやま けふこえて あさきゆめみし ゑひもせす"
```

NOTE: For this to work, font and region paths have to be resolvable by kit. Which is why ${fonts} and ${kit} are used.
Also note that NotoSansJP-SemiBold.ttf isn't in currently in font resources and is shown for demonstration only, although it can be added.
