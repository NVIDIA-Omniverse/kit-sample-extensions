# CHANGELOG

This document records all notable changes to ``omni.kit.browser.folder.core`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

## [2.1.1] - 2026-09-09
### Fixed
- OMPE-109433: a browser torn down without `destroy()` no longer reports its worker's
  cancellation as an error, which failed other extensions' tests at shutdown.

## [2.1.0] - 2026-08-31
### Added
- OMPE-101618: scan progress with a cancel, off unless a browser asks for it with
  `show_scan_progress`. Adding a whole drive, network share, filesystem root or Nucleus server
  asks for confirmation first.

### Fixed
- OMPE-101618: a scan no longer freezes the app. A collection also lists each file once, however
  its path is spelled.

## [2.0.3] - 2026-03-10
### Fixed
- OMPE-82599: Skip stat_async for HTTP/HTTPS URLs in start_traverse to avoid misleading "Invalid URL" warnings for S3 directory-prefix-style paths.

## [2.0.2] - 2026-02-03
### Changed
- Added `FolderCategoryDelegate` to the Python API reference; formerly available only under the Publish API.

## [2.0.1] - 2026-01-28
### Changed
- OMPE-74205: show folders only when adding collection (require kit 110 or later)

## [2.0.0] - 2026-01-26
### Changed
- Styling update using centralized global styling
- expose CONTEXT_MENU_STYLE as public API

## [1.12.1] - 2025-11-24
### Changed
- Show progress per folder when loading folders

## [1.11.1] - 2025-11-20
### Changed
- OMPE-71391: Use gather when traversing sub folders in parallel to speed up

## [1.10.10] - 2025-07-03
### Changed
- OMPE-53344: Remove warnings when setting BrowserFile.thumbnail property.

## [1.10.9] - 2025-05-09
### Changed
- OMPE-44165: Need to set permission after shutil.copytree

## [1.10.8] - 2025-05-05
### Changed
- OMPE-44165: Do not use "root" as test folder name because it may fail in OVC2 test

## [1.10.7] - 2025-04-25
### Changed
- OMPE-44165: Do not use omni.client.write_file_async because it may fail in OVC2 test

## [1.10.6] - 2025-04-19
### Fixed
- OMPE-44165: Use TempDirectory for tests

## [1.10.5] - 2025-04-14
### Fixed
- Fix doc build issues.

## [1.10.4] - 2025-04-01
### Changed
- Make getter and setter methods for url and thumbnail properties.

## [1.10.3] - 2025-02-07
### Changed
- OMPE-27665: Add python API document.

## [1.10.2] - 2025-01-23
- OMPE-31528: Make it compatible with different nucleus connector API and avoid deprecated usage for
    omni.kit.widget.nucleus_connector.get_connector_instance in newer Kit SDK.

## [1.10.1] - 2024-11-08
- Add BrowserPropertyDelegate as arguments of browser widget instead of self-register to work for different browsers

## [1.10.0] - 2024-09-19
- OMPE-21829: Add TreeFolderBrowserWidgetEx to show property view

## [1.9.13] - 2024-08-31
### Changed
- Update cached file list entry if necessary when traversing folders

## [1.9.12] - 2024-01-30
### Changed
- OM-103774: Improve documentation for FileSystemFolder and FolderBrowserModel.

## [1.9.11] - 2024-01-15
### Changed
- OMPRW-519: Fix category items not loaded correctly with air gap

## [1.9.10] - 2023-12-15
### Changed
- Fix collect multiple files not works as expect issue.

## [1.9.9] - 2023-10-26
### Changed
- OM-112780: Only refresh category item to hide loading icon when traverse done without changes
- Fix custom folder setting changed and add test

## [1.9.8] - 2023-10-11
### Added
- Added more test coverage and fixed test class name to not get clobbered by other identical one

## [1.9.7] - 2023-07-17
### Changed
- Fix ETM test failure with kit 105.0.1 integ-master

## [1.9.6] - 2023-06-27
### Changed
- Enable caching new root folders during warmup

## [1.9.5] - 2023-06-23
### Changed
- Make category count right to add new folder to a existed category item

## [1.9.4] - 2023-06-23
### Changed
- If different url found in cache file, should set has_cache to False
- Replace "%20" with space in category(folder) and detail(file) name
- When register external folder, check duplicated by name in existing category items

## [1.9.3] - 2023-06-14
### Changed
- use "setting_folders_hide_in_category" to define folders hide in category view instead simple "hide_root_folder"

## [1.9.2] - 2023-06-13
### Added
- FolderBrowserModel: Add argument to load and watch a setting for custom root folder paths

## [1.9.1] - 2023-06-13
### Added
- "hide_root_folder" does not take effect to folder with "/" in name

## [1.9.0] - 2023-05-31
### Added
- Add new argument "hide_root_folder" to not show root folder in category tree

## [1.8.8] - 2023-05-31
### Added
- OM-94780: Added the ability to register and unregister root folders with the FolderBrowserModel

## [1.8.7] - 2023-05-25
### Changed
- OM-96228: Remove warning of "python.pipapi"

## [1.8.6] - 2023-05-23
### Changed
- OM-95536: Support wild char when filter folders by name

## [1.8.5] - 2023-05-23
### Changed
- OM-88159: Add collect menu for folder category item's right click.

## [1.8.4] - 2023-04-04
### Changed
- OM-88151: Fix issue that traverse folder with invalid url again and again

## [1.8.3] - 2023-04-01
### Changed
- Fix error without "omniverse.toml" in GFN

## [1.8.2] - 2023-03-17
### Changed
- OM-86101: New argument "multiple_drag" to support multiple drag. Default False.

## [1.8.1] - 2023-03-11
### Changed
- OM-85835: Fix ETM failure

## [1.8.0] - 2023-03-08
### Changed
- OM-75191: Show loading animation while category in loading progress (require omni.kit.browser.core v2.3.0)

## [1.7.5] - 2023-02-04
### Changed
- Expose more functions for SimReady

## [1.7.4] - 2023-02-01
### Changed
- Change some functions to be overridden for SimReady

## [1.7.3] - 2023-01-04
### Fixed
- Decrement parent counts when samples are deregistered

## [1.7.2] - 2023-01-04
### Added
- Add property for detail selections in browser widget

## [1.7.1] - 2022-12-12
### Changed
- OM-75630: If folder url redirected, do not load from cache

## [1.7.0] - 2022-12-12
### Changed
- OM-75623: Replace url if alias defined in omniverse.toml

## [1.6.3] - 2022-12-09
### Changed
- OM-75623: Continue traversing folder even for an invalid URL (stat failed and not omniverse server)

## [1.6.2] - 2022-11-25
### Changed
- update docs

## [1.6.1] - 2022-11-16
### Changed
- OM-70692: Use omni.kit.widget.nucleus_connector to connect nucleus server when traversing folder while not connected

## [1.6.0] - 2022-10-31
### Changed
- Use TreeFolderBrowserModel/TreeFolderBrowserWidget for treeview mode
- If cache file enabled, only traverse collection when selected
- Do not traverse into sub folders if not necessary
- Filter sub folders/files during traverse to reduce cache and memory size
- After traverse, compare to cache, if nothing changed, do not refresh views

## [1.5.4] - 2022-10-25
### Changed
- OM-66710: Fix categories does not show if timeout during traversing folders

## [1.5.3] - 2022-10-18
### Changed
- OM-65821: Some folders in Sample browser were not saved/populated as expected

## [1.5.2] - 2022-10-11
### Changed
- Remove trailing slash in remove_root_folder

## [1.5.1] - 2022-10-11
### Changed
- Fix issue on summary enabled in treeview mode
### Added
- Argument to caching all folders during warmup

## [1.5.0] - 2022-10-06
### Added
- Enable local cache in category treeview mode

## [1.4.4] - 2022-09-30
### Changed
- Add argument to folder browser model to do not traverse folder after created

## [1.4.3] - 2022-09-21
### Changed
- Select/Deselect navigation button when clicked

## [1.4.2] - 2022-09-14
### Changed
- Sort Category items in treeview
- Add splitter_extra_width arg to browser widget

## [1.4.1] - 2022-09-13
### Changed
- Retry list async for kinds of exceptions

## [1.4.0] - 2022-08-31
### Added
- Use Path.stem for more robust extensions rather than last 4 chars
- Add parent and is_last_child to FolderCategoryItem
- Modify category delegate to handle 3 levels of tree hierarchy
- Add tree mode category delegate

## [1.3.0] - 2022-08-29
### Added
- Add local cache to avoid folder traverse when close and open the app again

## [1.2.2] - 2022-08-26
### Changed
- Republish since published 1.2.1 to be a wrong version

## [1.2.1] - 2022-08-19
### Changed
- Make navigation button and add/remove collection work for category tree mode

## [1.2.0] - 2022-07-22
### Added
- Add tree mode to show both collections and categories in category tree view

## [1.1.14] - 2022-07-22
### Changed
- Change process_root_folder to publish

## [1.1.13] - 2022-03-30
### Changed
- Republish for repo updates

## [1.1.12] - 2022-02-17
### Fixed
- Check connection status after url set

## [1.1.11] - 2022-02-16
### Changed
- Wait until server connected when list root folder

## [1.1.10] - 2022-01-22
### Changed
- Force updating collection combobox when folder appened
- Fix duplicated name in collections

## [1.1.9] - 2021-12-08
### Added
- Fix destory to destroy typo

## [1.1.8] - 2021-10-16
### Added
- Retry max 3 times when timeout in listing folders

## [1.1.7] - 2021-09-30
### Added
- Show timeout if list folder timeout
- Show menu item "Refresh current collection" in options menu if timeout

## [1.1.6] - 2021-09-27
### Added
- Timeout to list folder

## [1.1.5] - 2021-09-13
### Changed
- If hide item without thumbnail, also donot count

## [1.1.4] - 2021-06-28
### Added
- Show "..." instead of category number when loading not completed

## [1.1.3] - 2021-06-09
### Changed
- Show label in two lines for small thumbnail size is small and one line for large thumbnail size

## [1.1.2] - 2021-05-29
### Added
- Argument for extra filter function

## [1.1.1] - 2021-05-28
### Added
- Predownload

## [1.1.0] - 2021-05-28
### Added
- Allow to create custom folder object

## [1.0.9] - 2021-05-20
### Removed
- Remove carb.log_warn when list

## [1.0.8] - 2021-05-20
### Changed
- Donot sort collections to keep order of settings

## [1.0.7] - 2021-05-17
### Changed
- Better Dependencies
- add support for hide_file_without_thumbnails: default False
- add support for show_category_subfolders: default False

## [1.0.6] - 2021-05-17
### Changed
- Fix runtime error

## [1.0.5] - 2021-05-15
### Changed
- Available default thumbnail file name
- Fix error on default options menu
### Removed
- Unused carb.log_info

## [1.0.4] - 2021-05-12
### Added
- Arguments for thumbanil size

## [1.0.3] - 2021-05-11
### Added
- Interface to create custom file object: used for multi materials in one file.

## [1.0.2] - 2021-05-07
### Changed
- Rename from omni.kit.browser.folder
- Move options menu to omni.kit.browser.core

## [1.0.1] - 2021-05-04
### Changed
- Rename from omni.kit.browser.folder.model
### Added
- API to remove root folder
- Folder browser widget

## [1.0.0] - 2021-04-19
### Added
- First release
