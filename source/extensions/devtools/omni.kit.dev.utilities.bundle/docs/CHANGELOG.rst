**********
CHANGELOG
**********

This project adheres to `Semantic Versioning <https://semver.org/>`_.

[0.2.2] - 2026-09-23
Fixed
-----
- Clean up registered actions, the window visibility callback, and the menu layout correctly during shutdown.


[0.2.1] - 2025-02-13
Changed
-------
- NVBUG-5110273: Menu changes properly clean up at shutdown.


[0.2.0] - 2024-11-29
Changed
-------
- OMPE-28231: Added failure pattern exclusion for python 3.11 related warnings.


[0.1.14] - 2024-10-16
Changed
-------
- OMPE-25403 - Removing extension widget dependencies for the Extension Browser.


[0.1.13] - 2024-10-10
Changed
-------
- OMPE-24664 - Adding extension widget dependencies as they have been migrated out of the Extension Manager.


[0.1.12] - 2024-08-30
Changed
-------
- OMPE-20035 - Excluding error line so that we don't fail tests on windows
- OMPE-20036 - Excluding error line so that we don't fail tests on windows


[0.1.11] - 2024-08-29
Changed
-------
- OMPE-20036 - Adding bundle waiver.


[0.1.10] - 2024-07-12
Changed
-------
- Further TOML syntax issues for omni.kit.debug.settings.


[0.1.9] - 2024-07-12
Changed
-------
- Corrected TOML definition for extension settings to use correct syntax.


[0.1.8] - 2024-07-11
Changed
-------
- OMPE-14617 - Updated VS Code Debug window handling for the updated extension.


[0.1.7] - 2024-06-27
Changed
-------
- OMPE-8732 - Moved utilities menu items under root Developer menu group.


[0.1.6] - 2024-06-26
Changed
-------
- OMPE-8732 - Bumping version to ensure VS Code is added to the bundle.


[0.1.5] - 2024-06-24
Changed
-------
- OMPE-8732 - VS Code Link extension re-added, hides on startup, has full menu control.


[0.1.4] - 2024-06-19
Changed
-------
- OMPE-8732 - omi.kit.debug.settings - the window and the menu stay in sync in terms of visibility.


[0.1.3] - 2024-06-17
Changed
-------
- OMPE-8732 - omni.kit.debug.settings startup visibility controlled by setting.


[0.1.2] - 2024-05-01
Changed
-------
- Removed the Window Inspector.


[0.1.1] - 2024-04-12
Changed
-------
- Changed menu_index from 0 -> 3


[0.1.0] - 2024-04-11
Changed
-------
- Changed menu_index to a smaller value


[0.0.9] - 2024-04-09
Changed
-------
- Removing VS Code Link and Undo/Redo Viewer until they can be updated to behave correctly when forced hidden on startup.


[0.0.8] - 2024-04-09
Changed
-------
- Ensured the menu ticks matched window visibility. VS Code Link and the Undo/Redo View must start visible.
  If not, then their menu entries never work correctly.


[0.0.7] - 2024-04-05
Changed
-------
- Moved the DEBUG menu under a new Developer menu.


[0.0.6] - 2024-04-03
Changed
-------
- Updated some code formatting.


[0.0.5] - 2024-04-02
Added
-----
- Added the Settings inspector.


[0.0.4] - 2024-04-01
Changed
-------
- Created the *DEBUG* menu and moved the various debug extensions there.


[0.0.3] - 2024-03-26
Changed
------
- Trimming included extesnions down to what is specified in the SRD.


[0.0.2] - 2024-03-24
Changed
------
- Taking out usd_paths until the test dependency can be resolved.


[0.0.1] - 2024-03-12
Added
------
- The initial version
