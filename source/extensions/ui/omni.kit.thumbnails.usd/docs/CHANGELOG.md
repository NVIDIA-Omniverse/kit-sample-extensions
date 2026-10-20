# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.0.14] - 2026-10-12
### Fixed
- Kit 111: the default thumbnail template references nothing Kit 111 does not ship. The floor material is a built-in UsdPreviewSurface instead of `../../../NVIDIA/Materials/Base/Wall_Board/Cardboard.mdl`, and the dome light has no texture instead of `Marbles/textures/HDRI/B2_2k_256_4k.hdr`; both files are absent in Kit 111 and logged errors. The rendered thumbnail is unchanged.

## [1.0.13] - 2026-10-12
### Fixed
- Kit 111 tests: the test generator starts the capture from its open callback, since Kit 111 sends OPENED before that callback runs.

## [1.0.12] - 2025-11-05
### Fixed
- OMPE-55892: Remove unused import

## [1.0.11] - 2025-10-22
### Fixed
- OMPE-68887: Updating Pillow to 12.0.0 for OSS security fixes.

## [1.0.10] - 2025-08-26
### Fixed
- OMPE-61043: Removing legacy viewport tests as those extensions were removed in kit 107.1, also fixing other configuration issues.

## [1.0.9] - 2024-01-19
### Fixed
- OM-118790: Registers preferences on omni.kit.window.preferences 1.4.0 an above

## [1.0.8] - 2024-01-16
### Fixed
- OM-118506: Eliminated function call at import time to allow other python extension that `import omni.kit.thumbnails.usd` to generate their documentation without errors.

## [1.0.7] - 2023-11-28
### Added
- OM-106456: Fix for `UsdThumbnailGenerator` opening USD file from a network path.

## [1.0.6] - 2023-11-27
### Added
- OM-106456: Fixed `test_thumbnail_generator`

## [1.0.5] - 2023-11-02
### Added
- OMFP-3377: Increase test coverage to 85%.
### Fixed
- Fixed some exceptions due to bad arguments.

## [1.0.4] - 2023-10-18
### Changed
- OM-94687: Wait stage load asset finished in generate thumbnail async function.

## [1.0.3] - 2023-10-13
### Changed
- Set extension write target to be per-platform.

## [1.0.2] - 2023-10-11
### Changed
- PIL 10.0.0 no longer has Image.ANTIALIAS. Replaced with Image.LANCZOS which is the same algorithm as ANTIALIAS.

## [1.0.1] - 2023-03-21
### Changed
- Use pxr instead for rtx renderer, will remove ~300 seconds of compiling ray tracing shaders
- Update Kit-sdk

## [1.0.0] - 2023-03-20
### Changed
- Build with 105.0+master.109294

## [0.5.2] - 2022-07-26
### Fixed
- Fix issue with capturing on new Viewport when default Viewport is not focused.

## [0.5.1] - 2021-02-18
### Added
- Teach how to capture with new Viewport.
- Frame prims with a command and not through viewport_legacy.

## [0.5.0] - 2021-07-07
### Added
- Make capture thumbnail setting persistent.

## [0.4.0] - 2020-10-16
### Added
- add support to create thumbnails for Files


## [0.3.0] - 2020-10-16
### Added
- Make omni.kit.editor optional
- Add omni.kit.renderer.core/capture to allow working without omni.kit.editor

## [0.2.0] - 2020-10-14
### Added
- Renamed extension to omni.kit.thumbnails.usd to fall in line with the other thumbnail extensions
- Fixed slow writing of files on Windows to cause error.

## [0.1.1] - 2020-09-18
### Added
- Windows paths fix.

## [0.1.0] - 2020-09-18
### Added
- Initial release. When enabled, a thumbnail is generated for the active USD file when the fileis saved.
