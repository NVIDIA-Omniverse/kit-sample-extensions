**********
CHANGELOG
**********

This document records all notable changes to ``omni.kit.usd_explorer.render.preset`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.


[1.1.1] - 2026-08-19
====================
Changed
------
- OMPE-65241: Dropped the ``omni.app.dev`` test dependency, which hung the Windows CI runners.
- OMPE-65241: ``test_render_preset`` asserts ``/rtx/renderpreset`` instead of RTX defaults.
- Declared the directly imported ``omni.kit.menu.utils`` dependency.

[1.1.0] - 2026-04-07
====================
Changed
------
- Updated to Events 2.0 (carb.eventdispatcher)

[1.0.7] - 2025-09-23
====================
Changed
------
- remove fastShutdown and disable startup test for updating kit SDK to 109

[1.0.6] - 2025-08-15
====================
Changed
------
- Ensured fastShutdown was being used for unit tests.

[1.0.5] - 2025-04-14
====================
Added
------
- Added RTX - Real-Time 2.0 to render list

[1.0.4] - 2025-04-07
====================
Changed
-------
- OMPE-42901 - Updated to use Events 2.0. Fixed a bug where the USD Explorer was not being updated correctly when the USD stage changed. This was due to the use of the old event system, which has been deprecated in favor of the new Events 2.0 system. The new system provides a more efficient and reliable way to handle events, ensuring that the USD Explorer is always up-to-date with the latest changes in the USD stage.


[1.0.3] - 2025-04-07
====================
Changed
-------
- OMPE-42901 - Updated to use Events 2.0


[1.0.2] - 2024-08-29
========================

Changed
-------

- Author change


[1.0.1] - 2024-04-10
========================

Changed
-------

- Updated extenson.toml to use omni.kit.usd_explorer.tooltip


[1.0.0] - 2024-04-10
========================

Changed
-------

- Rename "usd-presenter" -> "usd_explorer"

[0.1.1] - 2023-04-04
========================

Changed
-------

- Rename "view" -> "usd-presenter"


[0.1.0] - 2020-08-03
========================

Added
------

- Initial view render preset implementation
