# Overview

`omni.services.convert.asset` is a Kit services extension that provides a service for batch conversion of various 3D file formats to USD using the Asset Converter Extension (`omni.kit.asset_converter`). This service extension leverages the underlying asset converter capabilities to convert files such as FBX, OBJ, GLTF, and other supported formats to USD format.

Upon loading, it registers with the Asset Converter service, allowing other extensions and external processes to utilize its conversion capabilities through a standardized API interface.

## About

The Asset Converter Service Extension provides an easy-to-use API to call into the asset conversion service.

## Usage

The Asset Converter Service Extension can be used in several ways:

1. **Direct API Calls**: Call the service directly from Python code or other extensions
2. **Batch Processing**: Use for automated conversion of multiple files
3. **Integration**: Integrate with other Omniverse services and extensions

The service provides a robust and flexible solution for converting various 3D file formats to USD, making it easier to work with different asset types in the Omniverse ecosystem.

## Supported File Formats

The Asset Converter Service supports conversion from the following file formats to USD:
- **FBX** (.fbx)
- **OBJ** (.obj)
- **GLTF/GLB** (.gltf, .glb)
- **LXO** (.lxo)
- **MD5** (.md5)
- **STL** (.stl)
- **BVH** (.bvh)

## Deprecations and Removals

- Removed NVCF utility functions, and related test artifacts

## ASSET CONVERTER SERVICE REQUEST FORMAT

The Asset Converter Service accepts requests in JSON format with the following structure:

### Request Arguments:

#### Required Arguments:

**import_path**
- **Description**: Full path to the source file to convert
- **Data Format**: string
- **Example**: `"/path/to/model.fbx"`

**output_path**
- **Description**: Full path to the output USD file
- **Data Format**: string
- **Example**: `"/path/to/output/model.usd"`

#### Optional Arguments:

**converter_settings**
- **Description**: JSON object containing conversion configuration options
- **Data Format**: object
- **Default Value**: `{}`
- **Example**: `{ "merge_all_meshes": true, "smooth_normals": true }`

**archive_path**
- **Description**: Optional path to `.zip`, `.tar`, or `.tar.gz` archive that contains the input file(s)
- **Data Format**: string
- **Default Value**: `""`
- **Example**: `"/path/to/archive.zip"`

## Sample Request Examples

### Minimal Conversion Request:

```json
{
  "import_path": "/path/to/simple_model.obj",
  "output_path": "/path/to/output/simple_model.usd"
}
```

### Basic Conversion Request:

```json
{
  "import_path": "/path/to/model.fbx",
  "output_path": "/path/to/output/model.usd",
  "converter_settings": {
    "merge_all_meshes": true,
    "smooth_normals": true
  }
}
```

### Conversion with Archive:

```json
{
  "import_path": "/path/to/model.fbx",
  "output_path": "/path/to/output/model.usd",
  "converter_settings": {
    "merge_all_meshes": true,
    "smooth_normals": true
  },
  "archive_path": "/path/to/archive.zip"
}
```

### Advanced Conversion Request:

```json
{
  "import_path": "/path/to/animated_model.glb",
  "output_path": "/path/to/output/animated_model.usd",
  "converter_settings": {
    "merge_all_meshes": false,
    "smooth_normals": true,
    "embed_mdl_in_usd": true,
    "embed_textures": true,
    "create_world_as_default_root_prim": true,
    "ignore_animations": false,
    "ignore_camera": false,
    "ignore_light": false,
    "ignore_materials": false,
    "use_meter_as_world_unit": true
  }
}
```



## CONVERTER SETTINGS CONFIGURATION

Conversion options are configured by supplying a JSON object in the `converter_settings` parameter. Below are the available configuration options.

### JSON Converter Settings:

**Format**: Each option is specified as a JSON key-value pair, e.g. `"option_name": default_value`

#### Converter Option: Bake MDL Material

**Description**: If true, bakes MDL materials during conversion.

**Default Value**: false
**Value Ranges**: true, false
**Data Format**: bool

**Config Example**:
```json
"bake_mdl_material": false
```

#### Converter Option: Baking Scales

**Description**: If true, applies baking scales during conversion.

**Default Value**: false
**Value Ranges**: true, false
**Data Format**: bool

**Config Example**:
```json
"baking_scales": false
```

#### Converter Option: Convert FBX to Y Up

**Description**: If true, converts FBX files to Y-up coordinate system.

**Default Value**: false
**Value Ranges**: true, false
**Data Format**: bool

**Config Example**:
```json
"convert_fbx_to_y_up": false
```

#### Converter Option: Convert FBX to Z Up

**Description**: If true, converts FBX files to Z-up coordinate system.

**Default Value**: false
**Value Ranges**: true, false
**Data Format**: bool

**Config Example**:
```json
"convert_fbx_to_z_up": false
```

#### Converter Option: Create World as Default Root Prim

**Description**: If true, creates a world as the default root prim in the USD hierarchy.

**Default Value**: true
**Value Ranges**: true, false
**Data Format**: bool

**Config Example**:
```json
"create_world_as_default_root_prim": true
```

#### Converter Option: Disabling Instancing

**Description**: If true, disables instancing during conversion.

**Default Value**: false
**Value Ranges**: true, false
**Data Format**: bool

**Config Example**:
```json
"disabling_instancing": false
```

#### Converter Option: Embed MDL in USD

**Description**: If true, embeds MDL materials directly in the USD file.

**Default Value**: true
**Value Ranges**: true, false
**Data Format**: bool

**Config Example**:
```json
"embed_mdl_in_usd": true
```

#### Converter Option: Embed Textures

**Description**: If true, embeds texture files directly in the USD file.

**Default Value**: true
**Value Ranges**: true, false
**Data Format**: bool

**Config Example**:
```json
"embed_textures": true
```

#### Converter Option: Export Hidden Props

**Description**: If true, exports hidden properties during conversion.

**Default Value**: false
**Value Ranges**: true, false
**Data Format**: bool

**Config Example**:
```json
"export_hidden_props": false
```

#### Converter Option: Export MDL GLTF Extension

**Description**: If true, exports MDL GLTF extension data.

**Default Value**: false
**Value Ranges**: true, false
**Data Format**: bool

**Config Example**:
```json
"export_mdl_gltf_extension": false
```

#### Converter Option: Export Preview Surface

**Description**: If true, exports USD Preview Surface materials.

**Default Value**: false
**Value Ranges**: true, false
**Data Format**: bool

**Config Example**:
```json
"export_preview_surface": false
```

#### Converter Option: Export Separate GLTF

**Description**: If true, exports GLTF data as separate files.

**Default Value**: false
**Value Ranges**: true, false
**Data Format**: bool

**Config Example**:
```json
"export_separate_gltf": false
```

#### Converter Option: Ignore Animations

**Description**: If true, ignores animation data during conversion.

**Default Value**: false
**Value Ranges**: true, false
**Data Format**: bool

**Config Example**:
```json
"ignore_animations": false
```

#### Converter Option: Ignore Camera

**Description**: If true, ignores camera data during conversion.

**Default Value**: false
**Value Ranges**: true, false
**Data Format**: bool

**Config Example**:
```json
"ignore_camera": false
```

#### Converter Option: Ignore Flip Rotations

**Description**: If true, ignores flip rotations during conversion.

**Default Value**: false
**Value Ranges**: true, false
**Data Format**: bool

**Config Example**:
```json
"ignore_flip_rotations": false
```

#### Converter Option: Ignore Light

**Description**: If true, ignores lighting data during conversion.

**Default Value**: false
**Value Ranges**: true, false
**Data Format**: bool

**Config Example**:
```json
"ignore_light": false
```

#### Converter Option: Ignore Materials

**Description**: If true, ignores material data during conversion.

**Default Value**: false
**Value Ranges**: true, false
**Data Format**: bool

**Config Example**:
```json
"ignore_materials": false
```

#### Converter Option: Ignore Pivots

**Description**: If true, ignores pivot points during conversion.

**Default Value**: false
**Value Ranges**: true, false
**Data Format**: bool

**Config Example**:
```json
"ignore_pivots": false
```

#### Converter Option: Ignore Unbound Bones

**Description**: If true, ignores unbound bones during conversion.

**Default Value**: false
**Value Ranges**: true, false
**Data Format**: bool

**Config Example**:
```json
"ignore_unbound_bones": false
```

#### Converter Option: Keep All Materials

**Description**: If true, preserves all materials during conversion.

**Default Value**: false
**Value Ranges**: true, false
**Data Format**: bool

**Config Example**:
```json
"keep_all_materials": false
```

#### Converter Option: Merge All Meshes

**Description**: If true, merges all meshes into a single mesh during conversion.

**Default Value**: false
**Value Ranges**: true, false
**Data Format**: bool

**Config Example**:
```json
"merge_all_meshes": false
```

#### Converter Option: Single Mesh

**Description**: If true, creates a single mesh from all geometry.

**Default Value**: false
**Value Ranges**: true, false
**Data Format**: bool

**Config Example**:
```json
"single_mesh": false
```

#### Converter Option: Smooth Normals

**Description**: If true, generates smooth normals for meshes.

**Default Value**: true
**Value Ranges**: true, false
**Data Format**: bool

**Config Example**:
```json
"smooth_normals": true
```

#### Converter Option: Support Point Instancer

**Description**: If true, enables support for USD Point Instancer.

**Default Value**: false
**Value Ranges**: true, false
**Data Format**: bool

**Config Example**:
```json
"support_point_instancer": false
```

#### Converter Option: Use Double Precision to USD Transform Op

**Description**: If true, uses double precision for USD transform operations.

**Default Value**: false
**Value Ranges**: true, false
**Data Format**: bool

**Config Example**:
```json
"use_double_precision_to_usd_transform_op": false
```

#### Converter Option: Use Meter as World Unit

**Description**: If true, uses meters as the world unit during conversion.

**Default Value**: false
**Value Ranges**: true, false
**Data Format**: bool

**Config Example**:
```json
"use_meter_as_world_unit": false
```

### Complete Example Configuration:

```json
{
  "bake_mdl_material": false,
  "baking_scales": false,
  "convert_fbx_to_y_up": false,
  "convert_fbx_to_z_up": false,
  "create_world_as_default_root_prim": true,
  "disabling_instancing": false,
  "embed_mdl_in_usd": true,
  "embed_textures": true,
  "export_hidden_props": false,
  "export_mdl_gltf_extension": false,
  "export_preview_surface": false,
  "export_separate_gltf": false,
  "ignore_animations": false,
  "ignore_camera": false,
  "ignore_flip_rotations": false,
  "ignore_light": false,
  "ignore_materials": false,
  "ignore_pivots": false,
  "ignore_unbound_bones": false,
  "keep_all_materials": false,
  "merge_all_meshes": false,
  "single_mesh": false,
  "smooth_normals": true,
  "support_point_instancer": false,
  "use_double_precision_to_usd_transform_op": false,
  "use_meter_as_world_unit": false
}
```

## HTTP ENDPOINTS

The Asset Converter Service provides the following HTTP endpoints:

### Health Check

**Endpoint**: `GET /convert/asset/health`

**Description**: Check if the service is alive and responding.

**Response Codes**:
- `200 OK`: Service is running

**Response JSON**:
```json
{
  "status": "OK"
}
```

### Readiness Check

**Endpoint**: `GET /convert/asset/ready`

**Description**: Check if the service is ready to accept new conversion requests. Used by Kubernetes readiness probes.

**Response Codes**:
- `200 OK`: Service is ready or not ready

**Response JSON**:
```json
{
  "ready": true
}
```

### Service Status

**Endpoint**: `GET /convert/asset/status`

**Description**: Get the current state of the conversion service, including active jobs and available slots.

**Response Codes**:
- `200 OK`: Status retrieved successfully

**Response JSON**:
```json
{
  "state": "IDLE",
  "active_jobs": 0,
  "max_job_count": 5,
  "available_slots": 5,
  "current_jobs": [
    {
      "job_id": "<job_id>",
      "file_path": "/path/to/file.fbx",
      "progress": 0.45,
      "start_time": "<job_start_time>"
    }
  ]
}
```

**Status Values**:
- `IDLE`: No jobs currently running
- `RUNNING`: One or more jobs in progress

### Job Status

**Endpoint**: `GET /convert/asset/status/{job_id}`

**Description**: Get the status of a specific conversion job by job_id. Only active (currently running) jobs can be queried via this endpoint. For completed or failed jobs, use the `/convert/asset/history` endpoint.

**Response Codes**:
- `200 OK`: Job status retrieved successfully
- `404 NOT FOUND`: Job with the specified ID not found (job may have completed or never existed)

**Response JSON**:
```json
{
  "job_id": "<job_id>",
  "file_path": "/path/to/file.fbx",
  "state": "RUNNING",
  "progress": 0.45,
  "error_message": "",
  "start_time": "<job_start_time>"
}
```

**Job State Values**:
- `RUNNING`: Job is currently in progress
- `COMPLETED`: Job completed successfully
- `ERROR`: Job encountered an error

### Job History

**Endpoint**: `GET /convert/asset/history`

**Description**: Get the history of completed and failed conversion jobs from the current session.

**Response Codes**:
- `200 OK`: History retrieved successfully

**Response JSON**:
```json
{
  "max_session_history_count": 5,
  "jobs": [
    {
      "job_id": "<job_1_id>",
      "file_path": "/path/to/file.fbx",
      "output_path": "/path/to/output.usd",
      "state": "COMPLETED",
      "progress": 1.0,
      "error_message": "",
      "start_time": "<job_1_start_time>",
      "end_time": "<job_1_end_time>"
    }
  ]
}
```

**Job State Values**:
- `RUNNING`: Job was running (should not appear in history)
- `COMPLETED`: Job completed successfully
- `ERROR`: Job encountered an error

### Convert Asset File

**Endpoint**: `POST /convert/asset/process`

**Description**: Convert an asset file to USD format.

**Request Body**: See [ASSET CONVERTER SERVICE REQUEST FORMAT](https://docs.omniverse.nvidia.com/kit/docs/omni.services.convert.asset/latest/Overview.html#asset-converter-service-request-format) section above.

**Response Codes**:
- `200 OK`: Conversion completed successfully
- `503 SERVICE UNAVAILABLE`: All conversion slots are full
- `422 UNPROCESSABLE ENTITY`: Invalid file path or unsupported output format
- `500 INTERNAL SERVER ERROR`: Conversion failed with an error

**Response JSON**:
```json
{
  "status": 200,
  "comment": "File /path/to/file.fbx was successfully converted to /path/to/output.usd."
}
```

**Job State Values** (for jobs created by this endpoint):
- `RUNNING`: Job is currently in progress
- `COMPLETED`: Job completed successfully
- `ERROR`: Job encountered an error

## Environment Variables

The following environment variables can be used to override default service behavior:

- **ASSET_SERVICE_MAX_JOB_COUNT**: Maximum number of concurrent conversion jobs allowed (default: `5`)
- **ASSET_SERVICE_MAX_SESSION_HISTORY_COUNT**: Maximum number of jobs kept in session history (default: `5`)

## Licensing Terms of Use and Third-Party Notices
`omni.services.convert.asset` is governed by the
[NVIDIA Software License Agreement](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-software-license-agreement/)
and the [Product Specific Terms for NVIDIA AI Products](https://www.nvidia.com/en-us/agreements/enterprise-software/product-specific-terms-for-ai-products/).
Redistribution of this extension is permitted only as provided by those terms.
By downloading or using NVIDIA Omniverse, you agree to the terms. See the
[Omniverse License Agreement](https://docs.omniverse.nvidia.com/dev-guide/latest/common/NVIDIA_Omniverse_License_Agreement.html).
