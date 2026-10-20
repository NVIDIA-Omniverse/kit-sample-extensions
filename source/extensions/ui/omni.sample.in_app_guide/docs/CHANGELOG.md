# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.2.1] - 2025-10-22

### Added

- Better preview.png
- `CUSTOMIZE.md` gives a more indepth on how the extension works

### Updated

- Redefining public API
- style.py now uses cl, fl, and url
- Shortened the icon urls to the unresolved token string
- Extension now extends `MenuHelperExtension`
- GuideStepWindow ui is draw using `self.frame.set_build_fn`

### Removed

- Repository tag in extension.toml


## [1.2.0] - 2025-10-14

### Added

- Tests that accommodate Menu Items
- Few more checks when calling `destroy` on `GuideStepWindow`
- `ActionType` enum for type-safe reveal action types (EXPAND, SCROLL, CLICK)
- Updated Window resize event to use new Event 2.0 System
- Updated DocStrings

### Fixed

- Memory leak in action registration by using weakref to prevent circular references
- Incorrect module path in extension cleanup (removed duplicate `.utils` in menu utils import)

### Removed

- Remove deprecated `guide_data_107.json` and `guide_data_106.json` files


## [1.1.0] - 2025-06-29

### Added

- `MenuGuideStep`, used to select UI elements in the Main Menu Bar
- When the Application window resizes it will also redraw the Guide Window and reposition it
- Unit tests were added
- Added test dependencies

### Changed

- `_GuideStep` is now `GuideStep` to help with code cleanup and prevent long list of `Union[WindowGuideStep, WidgetGuideStep, MenuGuideStep]` everytime a new `GuideStep` is created


## [1.0.0] - 2025-04-29

Initial version.