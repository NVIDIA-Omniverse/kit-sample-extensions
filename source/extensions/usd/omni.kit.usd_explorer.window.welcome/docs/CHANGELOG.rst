**********
CHANGELOG
**********

This document records all notable changes to ``omni.kit.usd_explorer.window.welcome`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

[1.2.0] - 2026-04-07
- Updated to Events 2.0 (carb.eventdispatcher)

[1.1.0] - 2025-12-16
- OMPE-75219: Close welcome window when a new stage is being opened.

[1.0.7] - 2025-04-07
- Fixed unit tests

[1.0.6] - 2025-04-03
- OMPE-42603 - The Welcome Window no longer crops itself if the app window is resized.

[1.0.5] - 2024-12-04
- OMPE-26079 - Ensuring the New button on the Welcome Window does a full file/new.

[1.0.4] - 2024-10-04
- OMPE-24141 - Disabling the golden image test to solve the ETM failures, at least until a better testing system can be implemented.

[1.0.3] - 2024-10-02
- OMPE-22152 - Adjusting wait time before snapping golden image, hoping this smooths out the intermittent ETM failures.

[1.0.2] - 2024-09-20
- OMPE-22152 - Adding `omni.kit.actions.core` to test dependencies.

[1.0.1] - 2024-08-29
- Author change

[1.0.0] - 2024-04-10
- Rename "usd_presenter" -> "usd_explorer"

[0.1.49] - 2023-11-02
- Added identifiers to UI elements for more robust tests.

[0.1.48] - 2023-10-30
- Improved the aliazing.

[0.1.47] - 2023-10-30
- Fixed an error that could occur when connecting to a remote server in the Open Dialog.

[0.1.46] - 2023-10-26
- Added background window to fake modality.

[0.1.45] - 2023-10-24
- OMFP-3087 - Add test for canceling out of open dialog -> ensuring welcome window is still open.

[0.1.44] - 2023-10-17
- OMFP-1911 - Update docs URL.

[0.1.43] - 2023-10-17
- OMFP-2419 - Change "Modify" button to "New"

[0.1.42] - 2023-10-13
- OMFP-2419 - Change "Modify" button to "New"

[0.1.41] - 2023-10-16
- Establish Kit setting for Welcome window's visibility.

[0.1.40] - 2023-10-13
- Fixed OMFP-2519 by changing the way welcome window is destroyed, USD Explorer checks visibility of welcome window
 to hide other tools. This change ensures welcome window is hidden properly.

[0.1.39] - 2023-10-11
- OMFP-2471 - Rename 'Comment' -> 'Review' and 'Modify' -> 'Layout'

[0.1.38] - 2023-10-11
- One more change for handling invalid strings in OpenLink.

[0.1.37] - 2023-10-11
- Address MR comments.

[0.1.36] - 2023-10-11
- OMFP-2240 - Toss a warning message if user tries to open link with invalid file path.
- Better handling of hot reload.
- Reformat change log.

[0.1.35] - 2023-10-10
- Added omni.kit.actions.core import and dependency.

[0.1.35] - 2023-10-10
- Added omni.kit.actions.core import and dependency.

[0.1.34] - 2023-10-10
- OMFP-2198
- display progress window when opening a USD file with the 'Open Link' button.

[0.1.33] - 2023-10-06
- OMFP-2112
- Close welcome window when a new stage is being opened;
              not immediately upon opening the file dialog (in case the user hits Cancel there)

[0.1.32] - 2023-09-26
- OMFP-761
- fixed `RecentFileCard` to not show %xx codes in filenames
- OMFP-761 - fixed Window/Welcome Window error

[0.1.31] - 2023-10-06
- OMFP-1946
- Welcome window is no longer shown when About is closed

[0.1.30] - 2023-10-04
- OMFP-648
- Add live link container for opening a file or joining a live session.
- Add placeholder docs url so that the 'Learn' action item will appear.
- Add 'Modify' action item that sets the current mode to Modify.
- Remove recent files container and 'About' action item.

[0.1.30] - 2023-09-26
- OMFP-761
- fixed `RecentFileCard` to not show %xx codes in filenames

[0.1.29] - 2023-06-27
- OM-95865
- Hide the nav bar 100% of the time at startup in File

[0.1.28] - 2023-06-02
- OM-97114
- Moving the Open button nav bar insertion into app setup extensions.

[0.1.27] - 2023-06-01
- OM-96340
- Fixed the regression in the recent_files_container to retrieve the recents list.

[0.1.26] - 2023-05-01
- About window code now calls the appropriate public attribute to show the dialog.

[0.1.25] - 2023-05-01
- Making sure the weindow and recent file container widget exist before trying _update_recent_files()

[0.1.24] - 2023-05-01
- Setting open button to never highlight

[0.1.23] - 2023-04-27
- Republishing to fix icons that LFS screwed up.

[0.1.22] - 2023-04-27
- Republishing to fix icons that LFS screwed up.

[0.1.21] - 2023-04-27
- OM-90595: Don't change the state image when click open button
- OM-90093: change open button's tooltip to label

[0.1.20] - 2023-04-07
- untracking PNGs from LFS

[0.1.19] - 2023-04-05
- Fixing PNGs

[0.1.18] - 2023-04-04
- Rename "view" -> "usd_explorer"

[0.1.17] - 2023-02-23
- Changed close button color from red to titlebar grey

[0.1.16] - 2023-02-21
- Recents File widget will not break if local_folder is None - more fixes. get_setting() -> get_setting_as_string()

[0.1.15] - 2023-02-21
- Recents File widget will not break if local_folder is None

[0.1.14] - 2023-02-21
- OM-83318 - A startup preference now contributes to the visibility of the close button if an emtpy stage is loaded.

[0.1.13] - 2023-02-14
- Restored PNG icons. The .gitignore for this new repo had them masked out.

[0.1.12] - 2023-02-14
- The visibility of the Learn button now keys off of an exts.omni.kit.usd_explorer.window.welcome.docsURL setting. If the setting doesn't exist, or is an empty string, the button is not added. If the setting is a string that points to the docs URL for the app the button is visible and will open that web page. "exts.omni.kit.usd_explorer.window.welcome".docsURL = "app_view/app_view/overview.html" will have the Learn button open https://docs.omniverse.nvidia.com/app_view/app_view/overview.html

[0.1.11] - 2022-12-28
- Add app window resize subscription, resize and re-position welcome window accordingly

[0.1.10] - 2022-11-15
- Add window visibility changed subscription, hide nav bar when open file window is active

[0.1.9] - 2022-10-27
- Hide viewport axis&HUD, bottom menubar and navigation bar when welcome window is active

[0.1.8] - 2022-10-27
- Add omni.kit.menu.file as dependency, it handles recent files

[0.1.7] - 2022-10-18
- Remove close button for welcome window (and esc key to close)
- Updated modal overlay shade for welcome window to be transparent

[0.1.6] - 2022-10-14
- Bring back changes in 0.1.3
- Added get_instance for testing, since ui.Workspace.show_window doesn't trigger show_window_fn correctly

[0.1.5] - 2022-10-03
- Removed New Stage and New File buttons. Removed checkbox option to show dialog at startup.

[0.1.3] - 2022-09-24- Cleanup stage sub events and connect callbacks, window is shown on start up instead of stage open
- add window positioning on startup

[0.1.2] - 2022-08-04
- Renamed extension to omni.kit.usd_explorer.window.welcome

[0.1.1] - 2022-05-04
- Remove unavailable items from recent file list

[0.1.0] - 2020-08-22
- Initial view startup window implementation
