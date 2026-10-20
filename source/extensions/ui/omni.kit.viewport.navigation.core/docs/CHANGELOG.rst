**********
CHANGELOG
**********

This project adheres to `Semantic Versioning <https://semver.org/>`_.

[1.0.31] - 2024-01-09
Changed
------
- Update public api.

[1.0.30] - 2024-12-11
Changed
------
- OMPE-30520: Don't build the navigation bar if there is no button on it.

[1.0.29] - 2023-10-30
Changed
------
- identifier for navbar to accommodate integration testing

[1.0.28] - 2023-10-30
Fixed
------
- Fix a error when open timeline bar before navigation bar

[1.0.27] - 2023-10-23
Fixed
------
- Republish to fix warnings

[1.0.26] - 2023-10-19
Fixed
------
- The position of the navigation bar shouldn't affect the window size.

[1.0.25] - 2023-10-19
Changed
------
- Added optional hotkey to toggle between navigation operations.

[1.0.24] - 2023-10-16
Changed
------
- Nav bar visibility fixes.

[1.0.23] - 2023-10-13
Changed
------
- OMFP-2430 - Prevent spurious left-click actions when the user is executing a right-click action.

[1.0.22] - 2023-10-13
Changed
------
- Nav bar saves its width for external use

[1.0.21] - 2023-10-12
Changed
------
- OMFP-2271: Increase Code Coverage of omni.kit.viewport.navigation.core

[1.0.20] - 2023-10-10
Changed
------
- Add subscription to "modal_tool_active" setting to manage nav bar visibility

[1.0.19] - 2023-10-10
Changed
------
- Vertical offset of the navigation bar considers an extra setting.

[1.0.18] - 2023-10-09
Changed
------
- OMFP-1994 - Left click hold & right click both show the context menu.

[1.0.17] - 2023-10-04
Changed
------
- Add stdoutFailPatterns.exclude to ignore shader loading error

[1.0.16] - 2023-09-13
========================
Changed
-----
- Code cleanup

[1.0.15] - 2023-08-08
========================
Fixed
-----
- OM-102605 - Disabling the teleport tool while hovering over the navigation bar.

[1.0.14] - 2023-07-13
Changed
-------
- OM-101734: Exposed a label property so the display name of a button can be changed if needed.

[1.0.13] - 2023-03-07
Fixed
-------
- OM-84675: Fix the tooltips missing in USD Explorer for it create the tooltip more than once.

[1.0.12] - 2023-02-28
Added
-------
- Added an isVisible setting and a subscription to watch it. This allows the visibility of the bar to be controlled by other UI elements.

[1.0.11] - 2023-02-22
Changed
-------
- Changed button label string manipulation from .capitalize() to .title() to handle multi-word labels appropriately.

[1.0.10] - 2023-02-03
Changed
-------
- Changed a failing try: without an except type to a suppress(ModuleNotFoundError) to handle if turntable is not included.

[1.0.9] - 2022-12-15
Changed
-------
- Adding a highlight rectangle that uses both the default rectangle style, and the button style

[1.0.8] - 2022-12-15
Changed
-------
- OM-76364: The capture button label now updates on button mode change.

[1.0.7] - 2022-12-14
Changed
------
- Exposing a style property for ViewportNavigationButton

[1.0.6] - 2022-11-29
Changed
------
- Disable golden test.

[1.0.5] - 2022-11-15
Changed
------
- OM-70677: User Friendly Navigation Bar.

[1.0.4] - 2022-11-08
Changed
------
- OM-71225: Keep button widget checked sync with the button state when the whole menubar redraw.

[1.0.3] - 2022-10-31
Changed
------
- Move unused settings.
- Improve nvigation button show window function.

[1.0.2] - 2022-10-26
Changed
------
- Improve show/hide logic.

[1.0.1] - 2022-10-25
Added
------
- Add some useful interface for tooltip.
- Add get navigation bar interface for extension.

[1.0.0] - 2022-10-20
Added
------
- The very initial version
