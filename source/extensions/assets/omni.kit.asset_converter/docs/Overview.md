# Overview

## Table of Contents
- [1.0 Overview](#10-overview)
  - [1.1 Introduction](#11-introduction)
  - [1.2 System Requirements](#12-system-requirements)
  - [1.3 Supported Formats and Features](#13-supported-formats-and-features)
  - [1.4 Material Parameters Support](#14-material-parameters-support)
  - [1.5 Known Issues and Limitations](#15-known-issues-and-limitations)
  - [1.6 Getting Help](#16-getting-help)

## 1.0 Overview

### 1.1 Introduction

The Asset Converter extension (`omni.kit.asset_converter`) provides interfaces to convert common 3D formats (FBX, OBJ, GLTF, etc.) to USD and vice versa.

Most applications such as Isaac Sim, and Kit-App-Template include the Asset Converter extension enabled by default.

#### Extensions that use the Asset Converter

The Asset Converter is integrated into the Omniverse ecosystem through a couple of extensions:

- omni.kit.tool.asset_importer {doc}`omni.kit.tool.asset_importer<omni.kit.tool.asset_importer:Overview>`
- omni.kit.tool.asset_exporter {doc}`omni.kit.tool.asset_exporter<omni.kit.tool.asset_exporter:Overview>`

### 1.2 System Requirements

The Asset Converter extension requires NVIDIA Omniverse Kit and compatible hardware. For detailed system requirements, including:
- Driver versions
- Hardware specifications
- Operating system support
- Minimum system requirements

Please refer to the [Omniverse technical requirements documentation](https://docs.omniverse.nvidia.com/materials-and-rendering/latest/common/technical-requirements.html).

### 1.3 Supported Formats and Features

#### Core Features
- Supports bidirectional conversion between USD and common formats (OBJ, FBX, glTF)
- Falls back to Assimp for unrecognized formats
- Supports both glTF (text) and glb (binary) formats with/without embedded textures
- Supports import/export of:
  - Meshes
  - Cameras
  - Light types (point, sphere, distance, rect)
  - Rigid and skeletal animations

#### Material Support
- Converts glTF materials to MDL:
  - KHR_materials_pbrSpecularGlossiness
  - KHR_materials_clearcoat
  - KHR_draco_mesh_compression
  - KHR_texture_transform
  - KHR_materials_volume
  - KHR_materials_emissive_strength
  - KHR_materials_ior
  - KHR_materials_sheen
  - KHR_materials_transmission
- Supports MDL material baking via `AssetConverterContext.bake_mdl_material`
- Supports direct import/export of MDL material graphs to/from glTF using NV_materials_mdl extension

> **Note:** CAD formats (SolidWorks, STL, Autodesk Inventor, AutoCAD 3D, Creo, Revit, Solid Edge, Step, Iges, JT, and DGN) are supported by the CAD Converter extension. For more details, visit the [CAD Converter documentation](https://docs.omniverse.nvidia.com/kit/docs/omni.kit.converter.cad/latest/Overview.html#formats-and-features-supported).

### 1.4 Material Parameters Support

#### Import Material Support

|             | ASSIMP | FBX | glTF | OBJ |
|-------------|--------|-----|------|-----|
| DIFFUSE     | ✓      | ✓   | ✓    | ✓   |
| EMISSIVE    | ✓      | ✓   | ✓    | ✓   |
| OPACITY     | ✓      | ✓   | ✓    | ✓   |
| NORMAL      | ✓      | ✓   | ✓    | ✓   |
| SPECULAR    | ✓      | ✓   | ✓    | -   |
| GLOSSY      | ✓      | -   | ✓    | -   |
| OCCLUSION   | ✓      | ✓   | ✓    | -   |
| ROUGHNESS   | ✓      | ✓   | ✓    | ✓   |
| METALLIC    | ✓      | ✓   | ✓    | ✓   |
| CLEARCOAT   | ✓      | -   | ✓    | -   |
| TRANSMISSION| ✓      | -   | ✓    | -   |
| SHEEN       | ✓      | -   | ✓    | -   |

#### Export Material Support

| Parameter    | ASSIMP | FBX | glTF |
|-------------|--------|-----|------|
| DIFFUSE     | ✓      | ✓   | ✓    |
| EMISSIVE    | ✓      | ✓   | ✓    |
| OPACITY     | ✓      | ✓   | ✓    |
| NORMAL      | ✓      | ✓   | ✓    |
| SPECULAR    | ✓      | -   | ✓    |
| GLOSSY      | ✓      | -   | ✓    |
| OCCLUSION   | ✓      | -   | ✓    |
| ROUGHNESS   | ✓      | -   | ✓    |
| METALLIC    | ✓      | -   | ✓    |
| CLEARCOAT   | ✓      | -   | ✓    |
| TRANSMISSION| ✓      | -   | ✓    |
| SHEEN       | ✓      | -   | ✓    |
| AMBIENT     | -      | ✓   | -    |
| DISPLACEMENT| -      | ✓   | -    |

### 1.5 Known Issues and Limitations

- Recursive skeleton support is not available for glTF
- Export from USD to other formats only supports:
  - OmniPBR
  - OmniGlass
  - UsdPreviewSurface
  - Specified gltf.mdl

### 1.6 Getting Help

- Enterprise Customers: Report issues through the [Enterprise Support Portal](https://www.nvidia.com/en-us/omniverse/enterprise/support/)
- Alternatively, users can also report Omniverse issues on  [NVIDIA Forums](https://forums.developer.nvidia.com/t/how-to-report-an-issue-with-omniverse/199675)
