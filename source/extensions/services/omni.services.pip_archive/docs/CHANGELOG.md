# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.18.16] - 2026-10-15
### Changed
- Resolve runtime dependencies together; remove repeated aiohttp/urllib3 installations.
- Align aioboto3 15.5.0, aiobotocore 2.25.1 and boto3/botocore 1.40.61. Keep build tools in a separate no-dependencies block.

## [0.18.15] - 2026-09-07
### Fixed
- NVBUG-6714305: Update services pip to use aiohttp 3.14.3.

## [0.18.14] - 2026-08-18
### Fixed
- NVBUG-6627767: Update services pip to use typing_extensions 4.14.1.

## [0.18.13] - 2026-07-17
### Fixed
- OMPE-101939: Update services pip to use aiohttp 3.14.1 (CVE-2026-50269).

## [0.18.12] - 2026-07-14
### Fixed
- OMPE-98308: Update services pip to use PyJWT 2.13.0 (CVE-2026-48525).

## [0.18.11] - 2026-06-29
### Fixed
- Update services pip to use cryptography 48.0.1.

## [0.18.10] - 2026-06-25
### Fixed
- OMPE-96687: Update services pip to use urllib3 2.7.0.
- Update zeroconf to 0.43.0 so services pip prebundle resolves.

## [0.18.9] - 2026-05-05
### Fixed
- OMPE-92532: Update services pip to use requests 2.33.0.

## [0.18.8] - 2026-04-24
### Fixed
- OMPE-90374 OMPE-89823: Update services pip to use cryptography 46.0.7 which also update openssl to 3.5.6.

## [0.18.7] - 2026-03-24
### Fixed
- OMPE-86726: Update services pip to use PyJWT 2.12.1.

## [0.18.6] - 2026-02-13
### Fixed
- OMPE-82023: Update services pip to use cryptography 46.0.5.

## [0.18.5] - 2026-02-05
### Fixed
- OMPE-80082: Update services pip to use cryptography 46.0.4 to update OpenSSL to 3.5.5.
- OMPE-80022: Update services pip to use urllib3>=2.6.3.
- OMPE-79964 & OMPE-79955: Update services pip to use setuptools==80.10.2 to update jaraco-context and wheel.
- OMPE-79959: Update services pip to use aiohttp==3.13.3.

## [0.18.4] - 2025-12-10
### Fixed
- OMPE-74597: Update services pip to use urllib3>=2.6.0.

## [0.18.3] - 2025-12-05
### Fixed
- OMPE-74095 & OMPE-72449: Update services pip to use aiomysql-0.3.0 and aiosignal-1.4.0.

## [0.18.2] - 2025-11-26
### Fixed
- OMPE-65074: Update services pip to use aiohttp-3.12.14 and setuptools-79.0.1.

## [0.18.1] - 2025-10-17
### Fixed
- OMPE-68374: Updated repository url

## [0.18.0] - 2025-10-10
### Updated
- OMPE-60307: Update `pyjwt` to 2.10.1.

## [0.17.0] - 2025-05-29
### Updated
- Update boto3 and relates lib version to match Kit 108 sdk updates.

## [0.16.0] - 2025-05-05
### Changed
- Update `wrapt` to version `1.17.2` for Python 3.11 compatibility.

## [0.15.0] - 2025-03-18
### Changed
- Update aiokafka and boto3 version to match Kit 107 sdk updates.

## [0.14.2] - 2025-03-10
### Changed
- Removed unsignable pip exes from packaging

## [0.14.1] - 2025-02-19
### Changed
- OMPE-33278: set Python and Kit version targets in omni.services.pip_archive

## [0.13.10] - 2025-02-20
### Changed
- OMPE-34947: Update aiohttp to 3.11.11

## [0.14.0] - 2025-01-13
### Changed
- OMPE-33278: set Python and Kit version targets in omni.services.pip_archive

## [0.13.7] - 2025-01-06
### Changed
- Remove forcing Pip version to remove out of date setuptool and autocommand
- NOTE: This version is yanked because it breaks omni.services.starfleet.auth-0.1.5 with Kit 106.5

## [0.13.6] - 2024-07-22
### Changed
- OMPE-13648: bumped 'requests' from 2.31.0->2.32.0 as advised by nSpect report

## [0.13.5] - 2024-06-24
### Changed
- Add `aiobotocore` and update related dependencies

## [0.13.4] - 2024-06-14
### Changed
- Bump `aiohttp` PIP library to `3.9.5`
- Add `cryptography` PIP library at version `42.0.8`

## [0.13.3] - 2024-05-09
### Changed
- Bump `typing_extensions` PIP library to `4.10.0`

## [0.13.2] - 2023-10-18
### Changed
- Bump `omniverse.omniauth.python-client` packman dependency to `1.0.10.gitlab.79.05880cca`

## [0.13.1] - 2023-09-18
### Changed
- Bring in third-party library required by the omni.services.kubernetes.client packman package. `kubernetes_asyncio==24.2.3`

## [0.13.0] - 2023-09-07
### Changed
- Bump `omniverse.logging.python-logger` packman package to `0.7.5.gitlab.56.e4c29e94`
- Bump `omniverse.omniauth.python-client` packman dependency to `1.0.9.gitlab.76.64103cd7`
  - Adds `requests==2.31.0`
  - Adds `aiohttp==3.8.5`

## [0.12.0] - 2023-09-01
### Changed
- Removed `asgi_correlation_id==4.2.0` PIP library, which will be offered through the `omni.kit.pip_archive` instead.

## [0.11.1] - 2023-07-12
### Changed
- Bump `omniverse.logging.python-logger` packman package to `0.7.1.gitlab.49.41805640`
- Bump `omniverse.omniauth.python-client` packman dependency to `0.7.7.gitlab.50.a98b5c27`

## [0.11.0] - 2023-08-15
### Changed
- Bump version, no dependencies added or updated.

## [0.10.0] - 2023-08-08
### Added
- Added `asgi_correlation_id==4.2.0` PIP library.

## [0.9.4] - 2023-07-14
### Changed
- Bump `omniverse.omniauth.python-client` packman dependency to `0.7.3.gitlab.38.9f2716c4`

## [0.9.3] - 2023-07-12
### Changed
- Bump `omniverse.logging.python-logger` packman package to `0.6.2.gitlab.33.a9a3aa29`
- Bump `omniverse.omniauth.python-client` packman dependency to `0.7.2.gitlab.36.e7f5f0d4`

## [0.9.2] - 2023-07-10
### Changed
- Bump `omniverse.logging.python-logger` packman package to `0.6.1.gitlab.31.578ea5e1`
- Bump `omniverse.omniauth.python-client` packman dependency to `0.7.0.gitlab.34.b9f38250`

## [0.9.1] - 2023-06-29
### Changed
- Bump `omniverse.logging.python-logger` packman package to `0.6.0.gitlab.30.6d6c4f9c`

## [0.9.0] - 2023-06-27
### Changed
- Bring in (omni.auth packman dependency) third-party library `"pyjwt==2.7.0"` (to aid with Windows builds) instead of `"pyjwt[crypto]==2.7.0"` is not feasible to build in Windows.

## [0.7.0] - 2023-06-12
### Changed
- Bring in third-party libraries required by the omniverse_authorization_client packman package. `"pyjwt[crypto]==2.7.0"` and `"pyyaml==6.0"`

## [0.6.0] - 2023-05-14
### Changed
- Make extension native to republish for Windows and Linux in case of compiled python libraries.

## [0.5.0] - 2023-05-07
### Changed
- Bump `databases` to `0.7.0` for python 3.10 support
- Bump  `asyncpg` to `0.27.0` for python 3.10 support
- Bump `aiomysql` to `0.1.1` for python 3.10 support
- Bump `aiosqlite` to `0.19.0` for python 3.10 support

## [0.4.5] - 2023-04-18
### Changed
- Bump `prometheus_client` to `0.12.0` for Python 3.10 support

## [0.4.4] - 2023-03-07
### Changed
- Bump `asyncpg` to `0.24.0` for Python 3.10 support

## [0.4.3] - 2023-02-24
### Changed
- added `zeroconf` package.

## [0.4.2] - 2022-12-13
### Changed
- Bump `aiohttp` to `3.8.3`.

## [0.4.1] - 2022-10-25
### Changed
- Do not import `watchdog` to not produce warnings. No need to import anything anymore, extension system can just add it to `sys.path`.

## [0.4.0] - 2022-04-21
### Changed
- Changed default import package to try and reduce overhead of loading `omni.services.pip_archive`.

## [0.3.0] - 2022-02-07
### Changed
- Adding `aiodocker` package.
- Remove `Elasticsearch` package.

## [0.2.0] - 2022-01-25
### Changed
- Adding OpenSearch package.
- Adding Elasticsearch package.

## [0.1.6] - 2021-10-23
### Changed
- Updated iconography of Extension to match Omniverse Farm branding.

## [0.1.5] - 2021-09-19
### Added
- Add pynvml package.

## [0.1.4] - 2021-09-09
### Added
- Add aioredis package.

## [0.1.3] - 2021-08-28
### Added
- Add aioboto3 package.

## [0.1.2] - 2021-07-19
### Added
- Add watchdog python package.

## [0.1.1] - 2021-06-14
### Added
- Include only SWIPAT approved packages.

## [0.1.0] - 2021-06-14
### Added
- Initial commit.
