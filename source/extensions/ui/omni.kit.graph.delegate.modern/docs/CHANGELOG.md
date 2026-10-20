# Changelog

Modern Delegate for Graph View

## [1.10.15] - 2026-02-24
### Changed
- Revert changes in 1.10.14
- Same as version 1.10.11

## [1.10.14] - 2026-02-20
### Changed
- GraphNodeDelegateFull.[build_tooltip|build_port_input|build_port_output] are now classmethods.
- item arg added to GraphNodeDelegateFull.build_tooltip method
- GraphNodeDelegateFull.[build_port_input|build_port_output] - pass style arg when creating ports.
- Add header/right extension hook and node background/icon style override hooks for derived delegates.
- Improve backdrop editing behavior with edit guards and double-click handling updates.

## [1.10.13] - 2026-02-19
### Fixed
- Same as version 1.10.11

## [1.10.12] - 2026-02-19
### Fixed
- Skip: bad publish

## [1.10.11] - 2025-10-17
### Fixed
- OMPE-68374: Updated repository url

## [1.10.10] - 2025-09-03
### Changed
- OMPE-64395: omni.kit.graph.delegate.modern needs ui.Menu & ui.Separator to use menu_compatibility=False

## [1.10.9] - 2025-09-03
### Changed
- Update test to always hide the main menubar to avoid golden image test failures.

## [1.10.8] - 2024-11-28
### Changed
- Increase the test waiting time for icon loading

## [1.10.7] - 2024-10-28
### Changed
- Changed support_level to Sample

## [1.10.6] - 2024-02-13
### Fixed
- Fixed Note editable text field so it shows up correctly in rasterizing mode.

## [1.10.5] - 2024-01-29
### Fixed
- Updated golden image for test note color to fix ETM failure.

## [1.10.4] - 2024-01-18
### Fixed
- Added golden img threshold to cover subpixel differences in connection curve widths.

## [1.10.3] - 2024-01-10
### Changed
- Fix ETM test failure

## [1.10.2] - 2024-01-03
### Changed
- Added wait time to a test to make it less flaky

## [1.10.1] - 2023-11-28
### Added
- Added tests to increase the code coverage
- Fix error when double click compound node which is on a backdrop node

## [1.10.0] - 2023-11-09
### Changed
Added foreground optional arg to connection method, for curve anchor drawing

## [1.9.2] - 2023-11-03
### Fixed
- Fix precedence bug with conditional expr. Needed to add parentheses.

## [1.9.1] - 2023-08-02
### Fixed
- Handle right aligned labels properly when checking if mouse is over the text in the label

## [1.9.0] - 2023-06-07
### Changed
- Port name edit fields are only enabled if mouse is over the text in the label

## [1.8.0] - 2023-06-12
### Added
- Added OmniNote support in OG, and tests for OmniNotes

## [1.7.0] - 2023-06-07
### Added
- Ability to double click and edit port names by passing in an optional can edit function

## [1.6.6] - 2023-05-08
### Fixed
- Added bigger margin for long port names

## [1.6.5] - 2022-11-24
### Fixed
- icon size does not consider sub-ports been expanded (OM-74025)

## [1.6.4] - 2022-10-20
### Fixed
- branch alignment for input group port which has both input and output subport (OM-64722)

## [1.6.3] - 2022-10-17
### Fixed
- Output group branch delegate is not aligned (OM-64722)
- Increase the golden image comparison threshold for the test to fix ETM failure (OM-65919)

## [1.6.2] - 2022-10-12
### Added
- Tooltips for expansion widget in the node header

## [1.6.1] - 2022-08-23
### Changed
- Updated golden images for 104 changes

## [1.6.0] - 2022-05-23
### Changed
- Export BackdropDelegate

## [1.5.1] - 2022-05-17
### Added
- Description field and update callback for backdrop delegate

## [1.5.0] - 2022-04-01
### Changed
- Return a value from all functions that build a node widget

## [1.4.3] - 2022-03-30
### Changed
update repo_build and repo-licensing

## [1.4.2] - 2022-03-29
### Fixed
- typo in BACKGROUND_RADIUS constant

## [1.4.1] - 2022-03-14
### Fixed
- adding "Graph.Connection.Making" style for half connection, so that it's not flashing between color and gray.

## [1.4.0] - 2022-02-24
### Changed
- Modifed return type of method _connection()_ and _build\_connection()_ from _GraphNodeDelegateFull_. It now returns a tuple of the bezier curve widget, freeline widget and its container widget.

## [1.3.0] - 2022-02-14
### Changed
- Open switch_expansion and build_collapse to be overridable

## [1.2.3] - 2022-01-17
### Changed
- Conform backdrop size unit

## [1.2.2] - 2022-01-14
### Changed
- Fix backdrop tooltip

## [1.2.1] - 2022-01-14
### Changed
- Fix connection artifact for halfway connections

## [1.2.0] - 2022-01-12
### Changed
- fix the port text where the text is very long
- add `build_port` method so that derived delegate can easily override the name of the port

## [1.1.0] - 2022-01-10
### Changed
- 1.0.11 introduced changes which were not backward-compatible, so I'm incrementing the minor version number so that dependent extensions will force this one to update.

## [1.0.11] - 2021-12-20
### Changed
- Fix tooltip triggering area at different zoom levels
- Updating tooltip with the tooltip change from ImGui::BeginTooltip to ImGui::BeginTooltipEx

## [1.0.10] - 2021-12-20
### Changed
- fixed the closed state port color
- separate the connection, port_input and port_output function, so that we can override the style in derived class

## [1.0.9] - 2021-12-20
### Changed
- fixed backdrop node background shape and margin

## [1.0.8] - 2021-12-16
### Changed
- fixed possible error when nodes are set to closed state

## [1.0.7] - 2021-12-14
### Changed
- added `prepare_draw` attribute check to maintain the compatibility with kit
- fixed entering compound crash

## [1.0.6] - 2021-12-14
### Changed
- Added double click the node label to rename the node
- Added port on node header when nodes are closed
- added `prepare_draw` for icons and port images, so that the icons have a high resolution

## [1.0.5] - 2021-12-10
### Changed
- Fixed the backdrop delegate: remove the expansion state and icon, add the color picker
- Fixed the compound node

## [1.0.4] - 2021-12-06
### Changed
- Some style changes to make the switch delegates working for the graph demo
- Fixed the backdrop delegate

## [1.0.3] - 2021-11-23
### Fixed
- Fixed the selection nodes background
- Moved the execution pin delegate to omni.graph.window.action

## [1.0.2] - 2021-11-22
### Added
- Added tooltips for nodes and ports
- Return widget from connection, node_backgroun and node_header
- Remove the hard coded port and node color dicts

## [1.0.1] - 2021-11-18
### Fixed
- Removing the content clipping which causes the node can't be moved

## [1.0.0] - 2021-11-12
### Added
- Initial commit
