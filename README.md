# NVIDIA Kit Sample Extensions

Kit Sample Extensions is a collection of NVIDIA Omniverse Kit extensions
for developers building OpenUSD applications.
Use the source to learn Kit extension patterns, add capabilities to an application,
or adapt an example to your own workflow, subject to its license terms.

The repository brings together Python and C++ extensions for user interfaces,
asset workflows, scene authoring, animation, services, and developer tools. Some
extensions are small examples; others provide substantial tools and integrations
with additional dependencies.

## What's included

Extensions are grouped by domain under [`source/extensions`](source/extensions):

| Group | Examples and uses |
| --- | --- |
| [Animation](source/extensions/animation) | Animation preferences and USD animation settings. |
| [Assets](source/extensions/assets) | Asset validation, import, and export workflows. |
| [Deprecated](source/extensions/deprecated) | Animation graph schema used by supported asset workflows. |
| [Developer tools](source/extensions/devtools) | Settings inspection, command macros, profiling, and development utilities. |
| [Physics](source/extensions/physics) | Physics scene authoring and preview tools. |
| [Services](source/extensions/services) | Service clients, transports, facilities, rendering, and asset workflow services. |
| [Tools](source/extensions/tools) | Curve creation, scene visualization, and other authoring tools. |
| [UI](source/extensions/ui) | Widgets, browsers, property interfaces, manipulators, and application windows. |
| [USD](source/extensions/usd) | Collections, variant editing, semantic properties, and other USD workflows. |
| [Utilities](source/extensions/utils) | Stage opening, client helpers, light rigs, and application integrations. |
| [Warp](source/extensions/warp) | Warp integration and GPU compute examples. |
| [Web](source/extensions/web) | Web messaging, deep links, streaming integration, and cloud configuration. |

See [Compatibility](#compatibility) for Kit-version and dependency guidance.

This release ships extensions. The build tools generate an application manifest
to lock and precache their dependencies; example applications are not included.

Each extension directory is named for its extension identifier. Its
`config/extension.toml` declares dependencies, Python modules or native plugins,
and package metadata. Consult its `docs` directory, where provided, for
extension-specific usage and settings.

## Getting started

### Requirements

- Git and [Git LFS](https://git-lfs.com/) to retrieve source and binary assets.
- A development environment matching one of the configured release platforms:
  Windows x86-64, Linux x86-64, or Linux aarch64. Native compilation requires the
  platform's build toolchain. On Windows, install Visual Studio 2022 with the
  Desktop development with C++ workload (MSVC v143) and a Windows SDK. Compiler
  and Windows SDK packages are not downloaded by this repository.
- Access to the Kit SDK packages and extension dependencies pinned by this
  repository.
- Hardware and drivers compatible with the selected Kit SDK and the extensions
  you want to run. Rendering and GPU-dependent tests require an appropriate GPU.

Use a short checkout path on Windows to avoid path-length and build-tool issues.

> **Windows / Warp:** Building Warp requires the Visual Studio 2022 C++ toolchain
> (MSVC v143). The pinned CUDA 12.9 toolkit rejects MSVC 14.50 and newer with an
> `unsupported Microsoft Visual Studio version` error. If you have newer Visual
> Studio versions installed alongside VS 2022, keep the VS 2022 selection and
> Windows pre-build environment setup in `repo.toml`; this ensures Warp uses the
> repository's selected compiler instead of discovering the newest installation.

### Get the source and build

Clone this repository using the URL from GitHub's **Code** menu. Open a terminal
in the checkout and retrieve its binary assets:

```sh
git lfs pull
```

From the repository root, build the release configuration:

**Windows (Developer PowerShell for Visual Studio 2022):**

```powershell
.\repo.bat build
```

**Linux:**

```sh
./repo.sh build
```

The repository tools download the required Kit SDK and dependencies and build the
configured extensions. Release is the default build configuration.

### Use an extension in your application

Choose an extension, read its manifest and documentation, and check that its
dependencies are available for your Kit version. For example,
[`omni.kit.debug.settings`](source/extensions/devtools/omni.kit.debug.settings)
provides a window for inspecting Kit settings.

After building, add the staged extensions and dependency cache to your application's
extension search paths. The following `.kit` configuration illustrates how to
enable the settings inspector; merge these entries into your application's existing
sections and replace the placeholders with your checkout path and platform
(`windows-x86_64`, `linux-x86_64`, or `linux-aarch64`):

```toml
[dependencies]
"omni.kit.debug.settings" = {}

[settings.app.exts]
folders.'++' = [
    "<checkout>/_build/<platform>/release/exts",
    "<checkout>/_build/<platform>/release/extscache",
]
```

Launch your application with the matching Kit SDK. Use forward slashes in the
configuration paths on Windows as well.

### Test your changes

After building, run the repository's extension tests from the repository root:

```powershell
# Windows
.\repo.bat test
```

```sh
# Linux
./repo.sh test
```

Run tests with the SDK, dependencies, and GPU configuration used by your
application.

## Compatibility

Use dependency versions that match your Kit release. Each extension's
`config/extension.toml` and documentation describe its dependencies and usage.
[`repo.toml`](repo.toml) records build, test, and publication selection, including
exclusions.

When using these extensions with the
[Omniverse Kit early access release](https://github.com/NVIDIA-Omniverse/omniverse-kit),
review that release's compatibility changes.

## Related projects

- [Omniverse Kit early access](https://github.com/NVIDIA-Omniverse/omniverse-kit)
- [Kit App Template](https://github.com/NVIDIA-Omniverse/kit-app-template)

## Feedback and contributions

Feedback, bug reports, and improvements are welcome through this repository's
GitHub issues and pull requests. Include the release or commit, Kit SDK version,
platform, affected extension, reproduction steps, and relevant logs when reporting
a problem. For changes, describe the behavior and the build or runtime checks
you performed.

## License and security

This project uses NVIDIA's proprietary license. See [LICENSE](LICENSE) for the
NVIDIA Software License Agreement and included product-specific terms.

Review the license notices supplied with each extension and its dependencies
before reuse or redistribution.

*Placeholder: Contribution guidelines will be added here.*

To report a potential security vulnerability, follow [SECURITY.md](SECURITY.md).
Do not report security vulnerabilities through public GitHub issues.
