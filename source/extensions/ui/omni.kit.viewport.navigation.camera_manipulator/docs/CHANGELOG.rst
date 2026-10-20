**********
CHANGELOG
**********

This project adheres to `Semantic Versioning <https://semver.org/>`_.

[110.0.4] - 2026-10-16
Changed
-------
- Give the existing Kit 111 compatibility changes a distinct package version: replace the retired raycast dependency with viewport picking and handle runtime extent values.

[110.0.3] - 2026-10-15
Fixed
-----
- Kit 111: double-click sets the orbit target to the surface under the cursor again, through the viewport pick query (``request_query``) instead of the removed world-ray query; no dependency on ``omni.kit.raycast.query``.
- Re-enable the orbit-target tests that were skipped while the world-ray query was unavailable.

[110.0.2] - 2026-08-20
Fixed
-----
- OMPE-66357: De-flake ``_set_orbit_target()``: retry the emulated double-click until it registers, wait for the raycast, and skip the cursor settle on retries.
- Widen ``multiClickWait`` to 1000ms for the ``ui`` test process only; the 200ms product default is unchanged.
- ``test_orbit_target_invalidate`` now reuses ``_set_orbit_target()``.

[110.0.1] - 2026-08-07
Fixed
-----
- De-flake ``test_orbit_gesture_with_target``: replace inline double-click sequence with ``_set_orbit_target()`` so the async raycast callback completes before the drag gesture begins.

[110.0.0] - 2026-06-16
Fixed
-----
- OMPE-44796: Make ``test_frame_button`` distance-agnostic so it passes for both the old and new ``FramePrimsCommand`` framing distance.

[107.3.2] - 2026-05-28
Fixed
-----
- De-flake ``test_default_target_distance`` by reusing the ``_set_orbit_target`` / ``assertTrueWithRetry`` helpers so the orbit-target double-click waits for the same ``wait_n_updates(10)`` settling used elsewhere in the suite.

[107.3.1] - 2026-04-13
Changed
------
- OMPE-82352: Prevent Pan and Dolly navigation from stalling when the composed world speed becomes too small near the camera target.
- Expose the navigation clamp maximum magnitude as a setting and raise its default value to 2000.

[107.3.0] - 2026-02-27
Changed
------
- OMPE-82352: Fix Dolly infinity point navigation freeze issue.

[107.2.13] - 2026-01-28
Changed
------
- OMPE-69933: Exclude omni.rtx error log since all tests passed.


[107.2.12] - 2026-01-22
Changed
------
- OMPE-75089: Skip test_orbit_double_click_speed test on linux ETM agents for flaky failure.

[107.2.11] - 2026-01-12
Changed
------
- OMPE-69933: Exclude rtx.scenedb error log since all tests passed.

[107.2.10] - 2025-11-21
Changed
------
- OMPE-68825: Skip test_orbit_target_with_wasd test on linux ETM agents for flaky failure.

[107.2.9] - 2025-11-05
Changed
------
- Remove the test rt setting to use the default rt mode.

[107.2.8] - 2025-10-01
Fixed
------
- Waiting an thresholds for test_orbit_pan_gesture test
- Uninitialized attribute usage
Changed
------
- Move to carb.eventdispatcher for stage and update event subscriptions

[107.2.7] - 2025-09-26
Fixed
------
- OMPE-65314: Fixed test_orbit_target_with_wasd test failure by using proper drag and drop gesture instead of individual mouse events

[107.2.6] - 2025-08-28
Changed
------
-OMPE-60241: Add value test for camera matrix.

[107.2.5] - 2025-08-21
Changed
------
-OMPE-56848: Fixed "Detected deprecated setting" in tests by load/save usd files in kit

[107.2.4] - 2025-07-23
Changed
------
-OMPE-47773: Exclude shader compile error in test for arm test failure.

[107.2.3] - 2025-07-07
Changed
------
-Bump version to publish the test rt setting change.

[107.2.2] - 2025-05-13
Changed
------
-OMPE-47773: Skip image compare test and other unstable test for aarch64.

[107.2.1] - 2025-05-05
Changed
------
-OMPE-42898: Updated to use eventdispatcher (Events 2.0) instead of EventStream (Events 1.0)

[107.2.0] - 2025-04-09
Removed
------
- Deprecated legacy Viewport usage

[107.0.0] - 2025-01-09
Changed
------
- Update public api.

[106.1.4] - 2024-11-21
Changed
------
- OMPE-29311: Adding a check to `fit_camera` to ignore empty bounding boxes when computing.

[106.1.3] - 2024-09-06
Changed
------
- OMPE-20908:Reintroducing the fix from 1.0.53 that was never merged back to master.

[106.1.2] - 2024-09-05
Changed
------
- OMPE-20688:Fix test failed with kit sdk 106.0.

[106.1.1] - 2024-09-03
Changed
------
- Fix test failed with kit sdk 106.1

[1.0.52] - 2023-11-15
Changed
-------
- OMFP-3875: Make orbit target aware of section plane

[1.0.51] - 2023-11-02
Changed
-------
- OMFP-3550: Avoid moving camera if guide prim of other tools is selected

[1.0.50] - 2023-10-26
Changed
-------
- Consider scene up axis when unrolling camera at scene load time.

[1.0.49] - 2023-10-24
Changed
-------
- OMFP-3097: Accept double-clicks that are twice slower than default to set orbit target.

[1.0.48] - 2023-10-24
Changed
-------
- Fix test failures.

[1.0.47] - 2023-10-23
Changed
-------
- OMFP-2889: Fixed cursor shape when mouse in viewport that is covered by other window.

[1.0.46] - 2023-10-23
Changed
-------
- OMFP-3068: Adjust camera only if FSD is active.

[1.0.45] - 2023-10-20
Changed
-------
- Fit perspective camera within the scene bounding box.

[1.0.44] - 2023-10-20
Changed
-------
- OMFP-2431: Add default focus distance if target is not set
- OMFP-2652: Improve target validation when dragging mouse after pressing W/S keys

[1.0.43] - 2023-10-19
Changed
-------
- OMFP-2854: removed usused carb.imgui import

[1.0.42] - 2023-10-19
Changed
-------
- OMFP-2652: Keep orbit target valid when pressing W/S keys.

[1.0.41] - 2023-10-19
Changed
-------
- OMFP-2698: Make orbit work properly with new target when dragging mouse immediately after double click (without releasing mouse).

[1.0.40] - 2023-10-18
Changed
-------
- OMFP-604: Set Orbit cursor shape when it active

[1.0.39] - 2023-10-18
Changed
-------
- OMFP-2745: To reset the cursor, we need to clear it, not override with a default, as that breaks everything.

[1.0.38] - 2023-10-17
Changed
-------
- OMFP-1269: Increase coverage and fix test crashes

[1.0.37] - 2023-10-16
Changed
-------
- OMFP-2431: Set initial orbit target distance to 5 meters

[1.0.36] - 2023-10-13
Changed
-------
- OMFP-2228: Matching orbit rotation speed to settings

[1.0.35] - 2023-10-12
Changed
-------
- replace dependencies."filter:platform"."windows-x86_64" to "filter:platform"."windows-x86_64".dependencies for toml validity

[1.0.34] - 2023-10-12
Changed
------
- Simplify orbit target enable / disable. Avoid flickering on setting new target.

[1.0.33] - 2023-10-12
Changed
------
- OMFP-1269: Increase Code Coverage of omni.kit.viewport.navigation.camera_manipulator.

[1.0.32] - 2023-10-12
Changed
------
- OMFP-2204: Reduced redundant calculations on setting new Orbit target.

[1.0.31] - 2023-10-11
Changed
------
- OMFP-2346: Fix orbit target jittering.

[1.0.30] - 2023-10-10
Changed
------
- OMFP-2204: Setting new focal point should retain the previous distance from target to camera position.

[1.0.29] - 2023-10-10
Changed
------
- OMFP-2106: add focal point indicator for orbit tool
- OMFP-2107: add closed hand cursor when dragging to orbit

[1.0.28] - 2023-10-09
Changed
------
- OMFP-2108: update orbit target when middle mouse pan to prevent notification or invalid orbit target

[1.0.27] - 2023-10-05
Changed
------
- OMFP-636: added notification if orbit target is not set

[1.0.26] - 2023-10-04
Changed
------
- Add stdoutFailPatterns.exclude to ignore shader loading error

[1.0.25] - 2023-10-03
Changed
-------
- OMFP-789 - Added code to handle for current tool change for navigation modes.


[1.0.24] - 2023-10-03
Changed
-------
- OMFP-637 - Added code to abide by the visibility settings for buttons. Icon updates


[1.0.23] - 2023-09-28
Changed
------
- OMFP-599, OMFP-600, OMFP-601 fix ui.scene elements destruction on hot reload. Turned ui.scene elements off when tool is not enabled.


[1.0.22] - 2023-09-13
Changed
------
- Adjusted tooltip height.

[1.0.21] - 2023-09-13
Fixed
------
- Removed vertical separator. All separator definitions are moving to bundle extensions to make it easier for apps to define where they appear.

[1.0.20] - 2023-08-02
Fixed
------
- OM-103904: Set rotate flag to False when call set_target_world to change the orbit target point

[1.0.19] - 2023-08-02
Fixed
------
- OM-103230: Use ComputeWorldBound instead of  ComputeLocalBound to get the orbit target mesh's bound

[1.0.18] - 2023-07-30
Fixed
------
- OM-102641 - Keep the 'capture' vertical separator, regardless of app deployment type (e.g.cloud)

[1.0.17] - 2023-05-11
Fixed
------
- OM-9916: Hides a separator when running on cloud, to keep nav bar looking correct.

[1.0.16] - 2023-05-10
Fixed
------
- OM-88882: Updated default operator to proper "none" value.

[1.0.15] - 2023-04-28
Fixed
------
- OM-88882: change default operation to none.

[1.0.14] - 2023-03-08
Fixed
------
- OM-84079: Fix orbit brings camera far away from framed object.

[1.0.13] - 2023-02-13
Fixed
------
- OM-81855: Fix it takes two clicks to select 'look around' after teleporting issue.

[1.0.12] - 2023-02-10
Fixed
------
- OM-80439: Remove the raycast dependency to avoid rebuild BVH.

[1.0.11] - 2023-02-08
Fixed
------
- OM-80439: delay to set the raycast scene when needed.

[1.0.10] - 2022-12-12
Added
------
- Added inertia settings for tumble and move, this should fix the remaining nav tools.

[1.0.9] - 2022-12-12
Changed
------
- Increased size of hand icon in the navFrame icon.

[1.0.8] - 2022-12-01
Changed
------
- Fix orth_zoom not exsit issue.

[1.0.7] - 2022-11-29
Changed
------
- Disable golden test.

[1.0.6] - 2022-11-18
Added
------
- Added configurable option to disable orbit-frame-camera behavior.

[1.0.5] - 2022-11-15
Changed
------
- OM-70677: User Friendly Navigation Bar.

[1.0.4] - 2022-11-10
Changed
------
- OM-71225: Fix double click to disable orbit issue.

[1.0.3] - 2022-11-09
Changed
------
- Updated SVG icons

[1.0.2] - 2022-11-01
Changed
------
- Change the implement for Frame button function.

[1.0.1] - 2022-10-31
Added
------
- Optimize the default operation.

[1.0.0] - 2022-10-20
Added
------
- The very initial version
