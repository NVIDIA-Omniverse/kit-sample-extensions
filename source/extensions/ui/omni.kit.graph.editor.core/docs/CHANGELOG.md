# Changelog

Omniverse Kit MDL UsdShade Editor

## [1.5.8] - 2026-02-24
### Fixed
- revert changes in 1.5.7
- Same as version 1.5.4

## [1.5.7] - 2026-02-20
### Fixed
- OMPE-55422: Add stacking order argument to CreateUsdUIBackdropCommand

## [1.5.6] - 2026-02-19
### Fixed
- Same as version 1.5.4

## [1.5.5] - 2026-02-19
### Fixed
- Skip: bad publish

## [1.5.4] - 2025-10-17
### Fixed
- OMPE-68374: Updated repository url

## [1.5.3] - 2024-03-20
### Fixed
- _clear_graph_view() could be called after the view was destroyed.

## [1.5.2] - 2024-02-28
### Fixed
- Wait to call Frame.clear() to prevent for clearing parent frame crash.

## [1.5.1] - 2023-04-04
### Fixed
- Add ability to pass style_type_name_override to items used in GraphEditorCoreWidget `__on_build_toolbar` function.

## [1.5.0] - 2023-03-29
### Added
- Moved _get_graph_view_hovered_position() here from Material Graph's GraphWidget class

## [1.4.7] - 2022-10-17
### Fixed
- Increase test wait frames

## [1.4.6] - 2022-10-14
### Fixed
- 1.4.4's change blocks the catalog's treeview selection callback

## [1.4.5] - 2022-10-13
### Added
- allow the graph catalog search field to interpret the widget style, so overriden class can change the search field style

## [1.4.4] - 2022-10-10
### Added
- the ability to click anywhere in the session widget to collapse/expand the catalog treeview

## [1.4.3] - 2022-09-22
### Fixed
- Increase test wait frames

## [1.4.2] - 2022-09-13
### Fixed
- Update golden image for test

## [1.4.1] - 2022-08-24
### Changed
- More test coverage to surpass 75% coverage

## [1.4.0] - 2022-07-04
### Changed
- Changed the catalog list item description to use elided text
- Re-parented the catalog list item title tooltip to the whole list item

## [1.3.3] - 2022-05-17
### Fixed
- Fixed poor node description formatting due to text box sizing

## [1.3.2] - 2022-04-29
### Fixed
- Changed breadcrumbs build in ctor instead calling set_build_fn to void ui.Frame popping issue.

## [1.3.1] - 2022-03-30
### Changed
- update repo_build and repo-licensing

## [1.3.0] - 2022-03-18
### Changed
- make `_tree_view` and `_on_build` accessible from GraphEdiotrCoreCatalog so that users can access the e.g. treeview selection and other property.

## [1.2.0] - 2022-02-23
### Changed
- Allow the creation of spacers in the toolbar

## [1.1.0] - 2022-01-31
- Tweak the catalog delegate to allow inherited class better override

## [1.0.7] - 2022-01-18
- A couple of tree view style tweaks and add icon_model check for tree view widget
- Add tests

## [1.0.6] - 2021-12-16
- Added label, tooltip and enabled support on toolbar

## [1.0.5] - 2021-12-14
### Changed
- Make the catalog tooltip word wrapped shorter

## [1.0.4] - 2021-12-10
### Added
- Add style as a property for graph widget

## [1.0.3] - 2021-12-06
### Added
- Make the catalog tooltip word wrapped
- Some tree delegate style changes to make the switch delegates working for the graph demo

## [1.0.2] - 2021-11-29
### Added
- Added graph toolbar so that users can build customized toolbar
- Added `on_key_pressed` for key pressed call backs

## [1.0.1] - 2021-10-18
### Changed
- Test related changes
- OmniSurfaceBlendBase

## [1.0.0] - 2021-06-04
### Added
- Initial commit, used in Material Editor
