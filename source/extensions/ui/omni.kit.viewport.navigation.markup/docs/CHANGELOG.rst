**********
CHANGELOG
**********

This project adheres to `Semantic Versioning <https://semver.org/>`_.

[1.1.2] - 2026-10-15
Changed
------
- Kit 111 EA1 tests only: the test process no longer fails on the published libraries' string-write refusal lines (OVStage "existing attribute ... has a different type", then ``pump_apply_usd_changes failed (12)`` and ``PUMP apply_usd_changes ... failed``). Every test passes; the libraries fix is #2840. Remove the exclusions for EA2.

[1.1.1] - 2026-08-12
Changed
------
- Scheduled coroutines with ``omni.kit.async_engine.run_coroutine`` instead of ``asyncio.ensure_future``, which guarantees they run on the main thread.

[1.1.0] - 2026-03-31
Changed
------
- Fully updated to Events 2.0

[1.0.31] - 2025-01-09
Changed
------
- Update public api.

[1.0.30] - 2023-10-23
Changed
-------
 - OMFP-2942: Add test for nav bar visibility after exiting markup.

[1.0.29] - 2023-10-20
Changed
-------
 - Updating golden image, as the upstream package changed the UI.

[1.0.28] - 2023-10-18
Changed
-------
 - Updating golden image, as the upstream package changed the UI.

[1.0.27] - 2023-10-12
Changed
-------
 - replace dependencies."filter:platform"."windows-x86_64" to "filter:platform"."windows-x86_64".dependencies for toml validity

[1.0.26] - 2023-10-10
Changed
------
- OMFP-2205 - Toggle buttons on nav bar and viewport menubar should affect the same window's vis.

[1.0.25] - 2023-10-09
Changed
------
- OMFP-1969 - Adjusting unsubscribing logic, seemed to produce weirdness.

[1.0.24] - 2023-10-09
Changed
------
- OMFP-1969 - Added unsubscribing logic, hopefully reducing errors.

[1.0.23] - 2023-10-05
Changed
------
- OMFP-1969 - Syncing the button state to the window visibility.

[1.0.23] - 2023-10-05
Changed
------
- OMFP-1969 - Only display the list view on left click.


[1.0.22] - 2023-10-05
Changed
------
- OMFP-1969 Remove right click feature. Have left click start markup editing and display the list window.


[1.0.21] - 2023-10-05
Changed
------
- OMFP-1942 - Removing triangle on button.


[1.0.20] - 2023-10-04
Changed
------
- Add stdoutFailPatterns.exclude to ignore shader loading error

[1.0.19] - 2023-10-03
Changed
-------
- OMFP-637 - Icon updates.

[1.0.18] - 2023-09-26
Changed
------
- Removed Dependency on browser extension.

[1.0.17] - 2023-09-13
Changed
------
- Removed unused omni.kit.widget.custom

[1.0.16] - 2023-09-13
Changed
------
- Code cleanup

[1.0.15] - 2023-05-04
Fixed
------
- Adjusting for interface change in the ListWindow implementation.

[1.0.14] - 2023-02-10
Changed
------
- Grabbing MarkupListWindow from `omni.kit.markup.core` instead of our internal implementation.

[1.0.13] - 2022-12-13
Changed
------
- Markup window is now created early enough to appear when switching to comments.

[1.0.12] - 2022-12-08
Changed
------
- Fix test pending error.

[1.0.11] - 2022-12-01
Changed
------
- Hook play with event.

[1.0.10] - 2022-11-29
Changed
------
- Disable golden test.

[1.0.9] - 2022-11-17
Changed
------
- OM-73261 - Fixing markup playlist playback.

[1.0.8] - 2022-11-15
Changed
------
- OM-70677: User Friendly Navigation Bar.

[1.0.7] - 2022-11-09
Changed
------
- Moved markup folder more to the left to balance the view.

[1.0.6] - 2022-11-09
Changed
------
- Hide markup list on file open

[1.0.5] - 2022-11-09
Changed
------
- Updated SVG icons]

[1.0.4] - 2022-11-01
Changed
------
- Trigger to publish new version.

[1.0.3] - 2022-10-31
Changed
------
- Add alignment parameter for show list window.
- OM-70266: Make waypoint/markup list window fill the viewport.

[1.0.2] - 2022-10-24
Changed
------
- Button behaves as a 1-shot, not a toggle.

[1.0.1] - 2022-10-24
Fixed
------
- Fix show list window issues

[1.0.0] - 2022-10-20
Added
------
- The very initial version
