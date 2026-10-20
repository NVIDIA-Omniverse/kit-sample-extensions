**********
CHANGELOG
**********

This document records all notable changes to ``omni.kit.viewport.menubar.timeline`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

[1.0.3] - 2026-08-27
Changed
------
- Ported extension from ``kit-viewport-menubars`` (deprecated) to ``kit-sample-extensions``

Fixed
------
- Guard against a missing bottom menubar in ``on_startup``, and against a never-created button in ``on_shutdown``
- Removed the unused ``actions`` import and ``deregister_all_actions_for_extension`` call from ``extension.py``
- Removed duplicate ``omni.kit.viewport.utility`` from ``[[test]]`` dependencies (already in ``[dependencies]``)

[1.0.2] - 2023-10-13
Changed
------
- OMFP-2350 - teleportation not working below the vertical height of the viewport bottom bar. Used content_clipping argument

[1.0.1] - 2023-10-09
Changed
------
- Add subscription to "modal_tool_active" setting to manage timeline toggle button visibility

[1.0.0] - 2023-10-03
Added
---------
- The very initial version of the timeline minibar toggle extension
