# CHANGELOG

This document records all notable changes to ``omni.kit.window.modifier.titlebar`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

## [107.0.3] - 2026-04-10
### Changed
- Made extension cross-platform: builds and loads on Linux as a no-op (Windows-only functionality)
- Fixed missing semicolon in non-Windows C++ stub
- Added platform skip for Windows-only tests on Linux

## [107.0.2] - 2025-10-17
### Fixed
- OMPE-68374: Updated repository url

## [107.0.1] - 2025-06-04
### Changed
- Updated documentation with AI agent.

## [107.0.0] - 2025-01-06
### Changed
- udpate public api

## [105.2.16] - 2024-01-18
### Changed
- Re-enable the tests which were disabled by wrong
- Use the default application icon (which is the one display in windows task bar) instead of the another one.
  The default app icon is specified by omni.appwindow with this key:
     settings.app.window.iconPath
  The following settings key are obsoleted:
     settings.exts."omni.kit.window.modifier.titlebar".icon.file
     settings.exts."omni.kit.window.modifier.titlebar".icon.size
     settings.exts."omni.kit.window.modifier.titlebar".icon.use_size

## [105.2.15] - 2023-10-18
### Changed
- OMFP-3266: remove the warnings at startup. To mark the ext compiled with kit-sdk 105.2

## [105.1.14] - 2023-10-18
### Changed
- OM-110920: ETM failure for omni.kit.tool.markup on release/105.1

## [105.1.13] - 2023-10-17
### Changed
- OMFP-2285: Add tests to make the code-coverage up to 85%+

## [105.1.12] - 2023-10-09
### Changed
- OMFP-1890: Cease use of pip-install in test

## [105.1.11]
=============
### Changed
- Fix OM-106372

## [105.1.10]
=============
### Changed
- Using carb::windowing/omni.appwindow to get the window handle

## [105.1.9]
=============
### Changed
- Fix https://nvidia-omniverse.atlassian.net/browse/OM-99138

## [105.1.8]
=============
### Changed
- Mark this extension compatiable with all kit-105.x

## [105.1.7]
=============
### Changed
- Fix test issue for kit-105

## [105.1.6]
=============
### Changed
- bump version to republish


## [105.1.5] - 2023-04-14
=============
### Changed
- OM-86366: Fix the test issue when test on teamcity

## [105.1.4] - 2023-04-11
=============
### Changed
- OM-86366: Fix the hang issue when test with --no-window

## [105.1.3] - 2023-03-24
=============
### Changed
- OM-86366: Fix the flickering title when maximized in Code

## [105.1.2] - 2023-03-20
=============
### Changed
- OM-86283: Change the package attributes

## [105.1.1] - 2023-03-16
=============
### Changed
- OM-86283: Trigger a new build against kit-sdk-105, to make it work with python 3.10

## [104.1.1] - 2023-03-13
=============
### Changed
- OM-85508: Do not call tests for extension by default

## [104.1.0] - 2023-01-12
=============
### Changed
- split code to c++ and python parts for kit ABI compatiable

## [104.0.13] - 2022-10-06
=============
### Changed
- Using the `/exts/omni.kit.window.modifier.titlebar/icon/size` now actually sets the icon size.
### Added
- Added the `/exts/omni.kit.window.modifier.titlebar/icon/use_size` configuration to enable the above fix.

## [104.0.12] - 2022-10-06
=============
### Added
- Strip version at dash when build is external, ie. 2022.2.1-rc.9 -> 2022.2.1

## [104.0.11] - 2022-07-08
=============
### Added
- Make ext sensitive to internal-fields changed in titleFormatString.

## [104.0.10] - 2022-07-08
=============
### Added
- Add unicode file name support.

 ## [104.0.9] - 2022-06-18
=============
### Fixed
- Fix bug OM-53023

## [103.0.8] - 2022-06-15
=============
### Fixed
- Fix bug OM-53419

## [103.0.7] - 2022-04-06
=============
### Added
- Make changeWindowRegion, respondOnMouseUp, showFullPath re-configurable

## [103.0.6] - 2022-04-04
=============
### Added
- OM-44927: fix resize issue

## [103.0.5] - 2022-04-04
=============
### Added
- OM-44927: Add option for if change window region

## [103.0.4] - 2022-03-30
=============
### Changed
- Update repo_build and repo_licensing
- Change the denpendency to omni.kit.uiapp.

## [103.0.3] - 2022-02-17
=============
### Change
Add platform check on startup
Fix the wrong tip of color format in toml file

## [103.0.2] - 2022-02-14
=============
### Add
Change button action from mouse-down to mouse-up


## [103.0.1] - 2021-10-25
=============
### Added
- Add more colors/properties to be configurable
- Make some properties change-and-play on fly
   The following lines are examples:
   titleFormatString = "{text:OMNIVERSE, font_color=0xff00,bold=true, italic = true } {separator} Kit-Demo {verKey:/app/version, font_color=0xff00ff} {separator} {file}"
   # Format string support:
        {separator[,parameters]}
        {image:file_path}
        {file:file_path[,parameters]}
        {text:string[,parameters]}
        {version:version_file[,parameters]}
        {verKey:ver_key_file[,parameters]} # ver_key file should be in format of ver_str+build_number, only the ver_key is used
   # parameters: font_name=xxx
                 font_size=xxx
                 font_color=xxx
                 bold=true|false
                 italic=true|false
   # Color is in format of 0xBBGGRR
   showFileFullPath = false
   icon.file = "${app}/APP.ICO"
   icon.size = 32
   defaultFont.name = "Arial"
   defaultFont.size = 18
   defaultFont.color = 0xA02020
   separator.color = 0x20A020
   separator.width = 1
   windowBorder.color = 0x2020A0
   windowBorder.width = 3
   colors.caption = 0xA08080
   colors.client = 0x80A080
   colors.minmax = 0x8080A0
   colors.close = 0xA0A080
   colors.button = 0xA080A0

-----------
### Changed
-----------
### Removed

## [1.3.16] - 2021-06-03
=============
### Added
-----------
### Changed
   Polish the UI and improve the performance
-----------
### Removed
-----------

## [1.3.14] - 2021-06-03
=============
### Added
-----------
### Changed
   Improve performance to avoid flicker while the window is dragged, based on 1.2.12
-----------
### Removed
-----------

## [1.3.12] - 2021-06-02
=============
### Added
-----------
### Changed
   Improve performance to avoid flicker while the window is dragged.
-----------
### Removed
-----------

## [1.3.10] - 2021-05-31
=============

### Added
   * support version(build nember) from settings key in title string:
      [settings.exts."omni.kit.window.modifier.titlebar"]
      titleFormatString = "OMNIVERSE {separator} VIEW {verKey:/app/version, font_color=0xff00ff} {separator} {file}"
      # Here the version will be read from the settings at path /app/version
   * add alias for {version:...}: {verFile:...}
      [settings.exts."omni.kit.window.modifier.titlebar"]
      titleFormatString = "OMNIVERSE {separator} VIEW {verFile:c:/1.version.txt, font_color=0xff00ff} {separator} {file}"
      # Here the verFile is an alias of version.

### Changed
-----------
### Removed
-----------


## [1.3.8] - 2021-05-19
=============

### Added
------
### Changed
 Fix bug: System button blurry.
### Removed
-----------


## [1.3.6] - 2021-05-19
=============

### Added
------
### Changed
 Fix bug: "Move-to-New OS Window" was broken, fixed it in this version.
 The reason is to return correct code for message WM_NCACTIVE.
### Removed
-----------


## [1.3.4] - 2021-05-06
=============

### Added
------
### Changed
 Update kit version to 102.0+master.39484.eb376f1e
### Removed
-----------


## [1.2.4] - 2021-05-06
=============

### Added
------
 1. Configurable default font for title text.
 2. support version (build number) in a version file
 3. make the border width configurable
    usage: (sample)
      [settings.exts."omni.kit.window.modifier.titlebar"]
      titleFormatString = "OMNIVERSE {separator} VIEW {version:${app}/version.md, font_color=0xff00ff} {separator} {file}"
      #Color is in format of 0xBBGGRR
      showFileFullPath = false
      icon.file = "${app}/APP.ICO"
      icon.size = 32
      defaultFont.name = "Arial"
      defaultFont.size = 18
      defaultFont.color = 0xC0C0C0
      separator.color = 0x00B976
      separator.width = 1
      windowBorderColor = 0xA0A0A0
      ...
### Changed

### Removed
-----------

## [1.2.2] - 2021-04-29
=============

### Added
------
 1. Configurable separator width
    usage: add settings
    [settings.exts."omni.kit.window.modifier.titlebar"]
    ...
    separatorColor = 0x00B976
    separatorWidth = 1
    ...

### Changed

### Removed
-----------

## [1.2.1] - 2021-04-28
=============

### Added
------
 1. A very light separator line between the caption bar and the menu bar.
 2  When unloaded and main application is not shutting down, restore windows default
    caption bar and border immediately

### Changed
Fix bug:
 1. When loaded, force to extract the file name to show.
 3. Know bugs: sometime, the system menu buttons (minimize, maximize, close) disappear.

### Removed
-----------

## [1.2.0] - 2021-04-28
=============

### Added
------

### Changed
Fix bug:
 1. If window's RGN changed, the border is sometime blurry.
 2. For very long file name, the text will draw on the top of system buttons

### Removed
-----------


## [1.1.2] - 2021-04-20
=============

### Added
------

### Changed
Fix bug: For kit-sdk >= 101.0+master.37158.b5faff0b.teamcity, it needs delay start.
Do not know why, it seems that some kit compoments destroied the message hook. To delay start makes the workaround.
Add configurable border color.

### Removed
-----------

## [1.1.1] - 2021-04-19
=============

### Added
------

### Changed
Fix bug: icon/string/buttons alignment

### Removed
-----------

## [1.1.0] - 2021-04-19
=============

### Added
Add option to show file name only
------

### Changed
Improve configs, docs, make it ready to publidsh

### Removed
-----------

## [1.0.0] - 2021-04-19
=============
The initial version of the extension.
