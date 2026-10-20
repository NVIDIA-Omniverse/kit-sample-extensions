**********
CHANGELOG
**********

This project adheres to `Semantic Versioning <https://semver.org/>`_.

[1.0.23] - 2026-08-26
Changed
-------
- OMPE-80508: Import the renderer capture interface from `omni.kit.renderer.capture` instead of the deprecated `omni.kit.renderer_capture` module.

[1.0.22] - 2025-08-28
Changed
-------
- OMPE-47773: Exclude grpc error for all test passed with no other errors.

[1.0.21] - 2025-07-16
Changed
-------
- Replace omni.renderer_capture to omni.kit.renderer_capture

[1.0.20] - 2025-04-21
Fixed
-------
 - OMPE-44175: Fix test for OVC2.

[1.0.19] - 2025-01-09
Changed
-------
 - Update public api.

[1.0.18] - 2024-11-29
Fixed
-------
 - OMPE-27997 - update kit sdk to 107 and fix test.


[1.0.17] - 2024-06-10
Fixed
-------
 - OMPE-5189 - Added "/exts/omni.kit.viewport.navigation.capture/enable" to disable screenshot button when false.

[1.0.16] - 2023-11-01
Fixed
-------
 - OMFP-3325 - Open screenshot browser in windows or linux

[1.0.15] - 2023-10-17
Changed
-------
 - OMFP-2538 - Adding back right click, removing the Screenshot settings entry.

[1.0.14] - 2023-10-17
Changed
-------
 - OMFP-2880 - Add tests to improve coverage

[1.0.13] - 2023-10-17
Changed
-------
 - OMFP-2538 - Remove right click menu entirely.

 [1.0.12] - 2023-10-13
Changed
-------
 - OMFP-2399 - Show Capture button on OVC.

[1.0.11] - 2023-10-12
Changed
-------
 - OMFP-2483 - revert on_markup_active() using set_screenshot_type()

[1.0.10] - 2023-10-12
Changed
-------
 - clean up extension.toml to use valid toml syntax

[1.0.9] - 2023-10-10
Changed
-------
 - OMFP-1243 - add more tests for extension
 - update golden images

[1.0.8] - 2023-10-09
Changed
-------
 - OMFP-1994 - Making left click hold display menus

 [1.0.7] - 2023-10-05
Changed
-------
 - OMFP-1243 - revive capture tests and add test dependencies

[1.0.6] - 2023-10-04
Changed
------
- Add stdoutFailPatterns.exclude to ignore shader loading error

[1.0.5] - 2023-10-03
Changed
-------
- OMFP-637 - icon updates.


[1.0.4] - 2023-09-13
Changed
-------
- Code cleanup


[1.0.3] - 2023-07-12
Changed
-------
- OM-100915: Change default state from the fictitious "Capture" to "Screenshot"


[1.0.2] - 2023-05-10
Changed
-------
- OM-89917 - Disable Capture on cloud deployments.


[1.0.1] - 2023-02-02
Changed
-------
 - Updated pref settings in extension.toml to match capture


[1.0.0] - 2023-02-01
Changed
-------
 - Capture extension without ansel.
