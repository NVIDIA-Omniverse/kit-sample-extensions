# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [2.0.2] - 2025-08-06
### CHANGED
- Changed modifying semantics from Usd to Sdf API

## [2.0.1] - 2025-05-20
### CHANGED
- Wrapped modifications, additions, and removals of semantics in an Sdf.ChangeBlock

### FIXED
- Fixed typeName error by creating the labels attribute before trying to set it

## [2.0.0] - 2025-04-24
### CHANGED
- Updated to support new UsdSemantics schema

## [0.4.0] - 2025-03-05
### CHANGED
- Update to kit 107

## [0.3.10] - 2024-11-26
### CHANGED
- added 'ticked' to menu window

## [0.3.9] - 2024-10-22
### CHANGED
- moved "omni.kit.test" dependency to test

## [0.3.8] - 2024-09-03
### CHANGED
- semantics import fix: `from pxr import Semantics` to `import Semantics`

## [0.3.7] - 2024-08-30
### FIXED
- added async version for `_build_window_ui` to avoid the `[Warning] [omni.ui] Container::addChild attempting to add a child during a draw callback` warning

## [0.3.6] - 2024-04-22
### FIXED
- Fix implicit dependency on semantics usd schema, make it explicit

## [0.3.5] - 2024-03-08
### ADDED
- Added `hideWindowOnStartup` setting

## [0.3.4] - 2023-06-06
### FIXED
- Fix issue with inherited semantics being displayed in editor

## [0.3.3] - 2023-01-13
### CHANGED
- Changed menu to new API

## [0.3.2] - 2022-12-06
### FIXED
- Menu toggle value when user closes the window

## [0.3.1] - 2022-11-30
### CHANGED
- Toggle menu entry
- Default prim types

## [0.3.0] - 2022-10-12
### ADDED
- Automatic labeling functionalities using prim names

## [0.2.3] - 2022-08-14
### FIXED
- Automatically applying semantics should not fail anymore

## [0.2.2] - 2021-08-10
### CHANGED
- Remove actually deletes the semantic instance from the prim
- Instead of an incremental semantic instance name, generate a random ID

## [0.2.1] - 2021-08-07
### FIXED
- Extension shuts down cleanly now
- semantic properties are checked to make sure they can be processed

### CHANGED
- Missing extension dependencies
- Cleanup subscriber on shutdown

## [0.2.0] - 2021-05-19
### ADDED
- Allow multiple semantic instances
- Function to clear type and data from semantic instances

### CHANGED
- Updated extension to latest Kit SDK
- Updated UI
- Updated docs

## [0.1.3] - 2021-05-13
### CHANGED
- Cropped preview image
- Fixed import in test
- 'Synthetic Data' menu created

## [0.1.2] - 2021-03-02
### REMOVED
- remove omni.kit.editor dependency

## [0.1.1] - 2021-02-25
### ADDED
- icon and preview
- readme

## [0.1.0] - 2020-07-21
### ADDED
- Initial setup

### CHANGED
- Modifyed example kit extension

### REMOVED
- example.cpp_ext
- example.mixed_ext
