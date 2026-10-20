Changelog
=========

This document records all notable changes to ``omni.wrapp.explorer`` extension.
This project adheres to `Semantic Versioning <https://semver.org/>`_.

## [2.4.5] - 2026-10-15
- Replace omni_wrapp_minimal with public ovpackage 0.2.1, retaining the wrapp Python API and explicitly installing local/S3 backend dependencies.
- Remove obsolete Package Explorer dependencies from the general UI pip bundle; Package Explorer uses its dedicated prebundle.

## [2.4.4] - 2026-09-02
- OMPE-106692: Upgrade aioboto3 to 15.5.0 and omni_wrapp_minimal to 2.3.1 (CVE-2026-69243).

## [2.4.3] - 2026-05-19
- Use a dedicated Package Explorer pip prebundle to avoid bundling unnecessary dependencies.

## [2.4.2] - 2026-04-22
- Upgraded to omni_wrapp_minimal==2.2.0 public release.

## [2.4.1] - 2026-02-24
- OMPE-79635 - Upgraded to omni_wrapp_minimal==2.1.0 public release.
- Allow relative path in wrapp_repo.config file.

## [2.4.0] - 2026-02-2
- OMPE-79949: Migrate Migrate omni.wrapp.package_explorer from kit-browsers to kit-sample-extensions.

## [2.3.0] - 2026-01-28
- Update settings dialog to support newer version of workspace config.

## [2.2.1] - 2026-01-27
- Add pip dependency: `urllib3>=2.6.3`
- Update to omni.wrapp_api-2.1.0-b3.
- Security scan updates.

## [2.2.0] - 2026-01-09
- OMPE-76705: Package Explorer GA2 UI enhancement
  - OMPE-44043: Fix multiple asset installation bug
  - OMPE-61665: Add Uninstall support: right-click context menu and a button in the Details pane
  - Prevent search bar from clearing after package install or refresh
  - Add install/uninstall Progress bar in Details pane
  - Split Refresh and Edit Settings into separate icons
  - Refresh icon animation to indicates refreshing in progress
- OMPE-76242: Upgrade to WRAPP 2.1.0 alpha pip module

## [2.1.2] - 2026-01-27
- Update to omni.wrapp_api-2.1.0-b3.
- Security scan updates.

## [2.1.1] - 2026-01-26
- Add pip dependency: `urllib3>=2.6.3`,

## [2.1.2] - 2026-01-27
- Update to omni.wrapp_api-2.1.0-b3.
- Security scan updates.

## [2.1.1] - 2026-01-26
- Add pip dependency: `urllib3>=2.6.3`,

## [2.1.0] - 2025-12-04
- OMPE-74135: Add progress bar support in Package Explorer for WRAPP install and uninstall actions.

## [2.0.1] - 2025-10-01
- OMPE-65311: Use the repo display name as the top browsing category label.

## [2.0.0] - 2025-09-16
- OMPE-63907: Update to omni.wrapp_api-2.1.0-a103.

## [1.4.6] - 2025-09-15
- OMPE-63225: Allow s3:// path in WRAPP repo settings dialog UI.

## [1.4.5] - 2025-09-05
- OMPE-62812: Allow duplicate repository URLs in the WRAPP settings dialog.

## [1.4.4] - 2025-09-04
- OMPE-62001: Refresh Package Explorer even when no valid WRAPP repository path is configured.

## [1.4.3] - 2025-08-22
- OMPE-56804: Update to omni.wrapp_api-2.1.0-a102.

## [1.4.2] - 2025-08-08
- OMPE-56804: Update to omni.wrapp_api-2.1.0-a101.

## [1.4.1] - 2025-07-28
- OMPE-56740: wrapp_repo_config take precedence over the wrapp_project_config.

## [1.4.0] - 2025-07-01
- OMPE-49311: Cleanup omni.wrapp.package_exploer code and add repo settings dialog. Remove omni.simready.browser dependency.

## [1.3.11] - 2025-06-17
- OMPE-52355: Update to omni.wrapp_api-2.0.0-b01, fix 0k file issues.

## [1.3.10] - 2025-06-10
- OMPE-50930: Fix issue on updating multiple assets from Package Explorer.

## [1.3.9] - 2025-06-09
- OMPE-50987: Properly handle inaccessible repos.

## [1.3.8] - 2025-06-05
- Update to handle asyncio exceptions, fixed exception message, cleaned up unused variable

## [1.3.7] - 2025-06-04
- Update to omni.wrapp_api-2.0.0-a916, which is built for Kit 107.3 vanilla, not using omni.pip.cloud.

## [1.3.6] - 2025-06-03
- Update to omni.wrapp_api-2.0.0-a915, remove the workarounds for OMPE-48894, and use only one scheduler for WRAPP.

## [1.3.5] - 2025-06-02
- OMPE-40881: Increase the number of WRAPP parallel jobs to 200 and file transfer jobs to 50

## [1.3.4] - 2025-06-02
- OMPE-50257: Fix an issue that Package Explorer Right-Click Updated to latest Packages failing
- OMPE-50132: Fix an issue that switching from a workspace containing published robot to another workspace causes Package Explorer infinite error loop

## [1.3.3] - 2025-05-30
- OMPE-50061: Fix an issue that Package Explorer shows ghost asset in the list

## [1.3.2] - 2025-05-29
- OMPE-49689: Fix an issue that installing packages from UI button causes infinite async loop

## [1.3.1] - 2025-05-23
- OMPE-48894: Use only one scheduler for WRAPP
- OMPE-49853: Remove Add Repository feature from the Options Menu

## [1.3.0] - 2025-05-19
- OMPE-49091: Add repository refresh support via Project workspace change callback from omni.cip.workspace when available.

## [1.2.1] - 2025-05-18
- OMPE-48697: Fix an infinite async loop issue on IssacSim 5.0 with Kit GUI on Windows.
- Remove default search folders from toml.

## [1.2.0] - 2025-05-16
- OMPE-48697: Fix IssacSim 5.0 Crashes when Package Explorer runs WRAPP install
- OMPE-48635: Fix Package Explorer adds extra folders
- OMPE-48469: Package Explorer for CIP uses CIP config settings

## [1.1.0] - 2025-04-15
- Custom default thumbnail for missing thumbnails
- Add /exts/omni.wrapp.package_explorer/interface_usd_name setting for setting top level interface USD file name

## [1.0.1] - 2025-04-15
- Update omni.wrapp_api dependency to 2.0.0-a910

## [1.0.0] - 2025-03-18
- Init version
