**********
CHANGELOG
**********

This document records all notable changes to ``omni.kit.viewport.menubar.bottom`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

[1.0.7] - 2026-08-28
Changed
------
- Updated dependencies.

[1.0.6] - 2026-08-27
Changed
------
- Ported extension from ``kit-viewport-menubars`` (deprecated) to ``kit-sample-extensions``.
  No functional change; ``repository`` metadata now points at the new source home.

Fixed
------
- Removed ``omni.kit.renderer.capture`` from ``[[test]]`` dependencies; it is already
  pulled in transitively (``omni.kit.viewport.menubar.core`` -> ``omni.ui`` ->
  ``omni.kit.renderer.imgui``), which fails ``omni.kit.test``'s ``[[test]]`` sanity check

[1.0.5] - 2023-10-13
Changed
------
- OMFP-2350 - teleportation not working below the vertical height of the navbar. Used content_clipping argument

[1.0.4] - 2023-10-03
Changed
------
- Default spacing.
- Added common button styles.

[1.0.3] - 2023-03-15
Changed
------
- Updating test arguments.

[1.0.2] - 2022-10-26
Changed
------
- Update test for kit 105

[1.0.1] - 2022-07-15
Changed
------
- Remove the hard-coded _build_menubar, make it more stable when base class changed.

[1.0.0] - 2022-07-15
Changed
------
- Changed the export interface for bottom bar name
- Remove the rect of the bar, make it 100% transparent.
- Align the bar to the bottom. (This needs omni.kit.viewport.menubar.core to get some fix)

[Unreleased] - 2022-07-12
Added
------
- The very initial version
