# CHANGELOG

This document records all notable changes to ``omni.explore.main.menubar`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

[1.1.0] - 2026-04-07
Changed
-------
- Updated to Events 2.0 (carb.eventdispatcher)

[1.0.39] - 2025-04-19
Changed
-------
- OMPE-44173: Use rtx instead of pxr for tests, otherwise it will failed in OVC2.

[1.0.38] - 2024-09-26
Changed
-------
OMPE-22769: Adjusting menubar offset to account for the help menu defaulting to 99.

[1.0.37] - 2024-08-29
Changed
-------
OMPE-20037: Hide viewport window in test for UI comparison

[1.0.36] - 2024-04-10
Changed
-------
- Migrated from omni.kit.usd_presenter.render -> omni.kit.usd_explorer.render.

[1.0.35] - 2024-04-10
Changed
-------
- Renamed "usd_presenter" -> "usd_explorer"

[1.0.34] - 2023-10-27
Changed
------
- OMFP-3290: enable save button in review mode

[1.0.33] - 2023-10-25
Fixed
------
- OMFP-2113: disable selection outline in Comment mode (make it work across extension reload, added unit test)

[1.0.32] - 2023-10-20
Changed
------
- OMFP-2744: hover styling should work for default system menus

[1.0.31] - 2023-10-19
Changed
------
- Added tests

[1.0.30] - 2023-10-13
Changed
------
- OMFP-2504 - Sharing the live session if one is active.


[1.0.29] - 2023-10-12
Changed
------
- OMFP-2471 - Rename 'Comment' -> 'Review' and 'Modify' -> 'Layout'

[1.0.28] - 2023-10-12

Changed
------

- OMFP-2471 - Rename 'Comment' -> 'Review' and 'Modify' -> 'Layout'


[1.0.27] - 2023-10-07

Changed
------

- Disable selection outline in Comment mode

[1.0.26] - 2023-10-06

Changed
------

- Share button is disabled for local stages.
- Open button opens the open file dialog instead of the removed welcome screen.

[1.0.25] - 2023-10-04

Changed
------

- Removed all icons in Modify mode.
- Fixed icon and button alignment.

[1.0.24] - 2023-10-04

Changed
------

- OMFP-1799 - Inclusion of Present mode is now a defaulted True option


[1.0.23] - 2023-10-03

Changed
------

- OMFP-612 & 631 Cleaned up mode switching code.


[1.0.22] - 2023-10-03

Changed
------

- OMFP-612 Disabled viewport selection while in present mode


[1.0.21] - 2023-10-03

Changed
------

- OMFP-631 Disabled viewport selection while in comment mode


[1.0.20] - 2023-10-03

Changed
------

- Alignment fixes.

[1.0.19] - 2023-10-02

Changed
------

- Added new buttons to main menubar.

[1.0.18] - 2023-09-01

Changed
------

- Added bool setting to disable the application mode switches completely.

[1.0.17] - 2023-07-25

Changed
------

- OM-100908 Changed the Iray warning from a MessageDialog to a notfication pop up.


[1.0.16] - 2023-07-25

Changed
------

- OM-100908 Warn the user about switching to Iray and the potential resource and performance hit. Improved tooltips.


[1.0.15] - 2023-06-09

Changed
------

- OM-97354 - Using the omni.kit.viewport.menubar.render renderer switching code.


[1.0.14] - 2023-06-09

Changed
------

- OM-97354 - Ensuring both rendermode settings; rtx/rendermode and rtx/iray/rendermode are set appropriately on mode change


[1.0.13] - 2023-05-19

Changed
------

- OM-76204 - The control now listens for an event emitted from the Render Settings dialog so the Draft / Preview / Photo control can be updated.


[1.0.12] - 2023-05-10

Changed
------

- If the user selects the currently active application mode the _set_mode() fn will early out.


[1.0.11] - 2023-05-08

Changed
------

- Improving which settings are changed when different presets are selected.


[1.0.10] - 2023-04-19

Changed
------

- Really mapping "Photo" mode to the iRay renderer.


[1.0.9] - 2023-04-18

Changed
------

- Mapping "Photo" mode to the iRay renderer


[1.0.8] - 2023-04-04

Changed
------

- rename "view" -> "usd-presenter"


[1.0.7] - 2023-03-20

Changed
------

- OM-87676: Fix issue for python 3.10

[1.0.6] - 2023-03-20

Changed
------

- OM-83698 Added Identifiers and accessors for Application Control Mode and Render Control Mode buttons


[1.0.5] - 2023-03-07
========================

Changed
------

- OM-83898 Changing to Present mode on file load is now optional


[1.0.4] - 2023-02-24
========================

Changed
------

- Added setting to control display of Modify mode.


[1.0.3] - 2023-02-24
========================

Changed
------

- Migrated out to the view repo


[1.0.2] - 2023-02-20
========================

Changed
------

- Don't allow to reload render settings outside except from UI.


[1.0.1] - 2022-07-25
========================

Changed
------

- Remove live and cache status to use menu bar from omni.kit.widget.live.
- Port Avatar status to menu 2.0 and move it to omni.kit.usd_explorer.menubar.avatar.


[1.0.0] - 2022-07-07
========================

Changed
------
- First version
