# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [5.0.1] - 2026-10-16
### Changed
- Issue a fresh package for verified Windows signing and signed publication metadata.

## [5.0.0] - 2025-12-17
- [OMPE-68641] Update kit-kernel to 110.0, Python 3.12, and USD 25.11

## [4.0.0] - 2025-05-13
- [OMPE-47017] Update kit-kernel to 108.0, Python 3.12, and USD 25.02

## [3.0.0] - 2025-02-05
- [OMPE-35621] Update kit-kernel and repo dependencies to support ABI=1

## [2.0.0] - 2024-12-18
- [OMPE-29921] Update kit-kernel to 107.0, Python 3.11, and USD 24.05

## [1.0.0] - 2024-12-18
- [OMPE-32025] Updating extension to Kit Kernel 106.5.x, adding Gitlab CI/CD, update repo tools, remove rtx plugins, and clean up repo.

## [0.0.10] - 2023-06-08
- Updating repo tools

## [0.0.9] - 2023-05-12
- Updating Kit SDK (105.0.1)

## [0.0.8] - 2023-05-03
- Store String/Number (as doubles)/Boolean properties and save as USD attributes
- Precision fix to store values as doubles where possible
- Conversion of Lat/Long: changed conversion to convert from degrees-to-meters instead of default value of stage's metersPerUnit
- BasisCurves now linear
- Change in Stage hierarchy: Additional Xform added between GeoJSON and Features that takes the name of the folder (path /World/Geospatial/GeoJSON/<folderName>/Features/); Purpose - to group features together from this source GeoJSON and allow the user to move features to origin
- Xform Features now has translation set to geographical location of features; Can be set to {0,0,0} if the user wishes to see features at stage origin (and avoid view of gaps)

## [0.0.7] - 2023-03-15
- Updates to packages for Kit 105

## [0.0.6] - 2022-11-21
- Fix missing features due to Pair ID

## [0.0.5] - 2022-11-18
- Added title bar for undocked window

## [0.0.4] - 2022-10-28
- Updated Kit SDK version to 104.1

## [0.0.3] - 2022-10-26
- Added GeoJSON features "Point", "MultiPoint", "MultiLineString"

## [0.0.2] - 2022-10-25
- Added "beta" tag

## [0.0.1] - 2022-10-18
- Initial beta build
