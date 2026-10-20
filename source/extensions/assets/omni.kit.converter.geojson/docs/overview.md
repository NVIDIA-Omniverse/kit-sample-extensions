# GeoJSON Converter

## Overview

The NVIDIA Omniverse™ GeoJSON Converter Extension parses geospatial data stored in GeoJSON files and visualizes them in Omniverse™.

## Features

- Parses GeoJSON (.geojson) files and converts the data into prims on a USD stage
- This converter supports conversion of Point, MultiPoint, LineString, MultiLineString, Polygon, and MultiPolygon GeoJSON feature geometry types.
- UI window provides a field for the user to define a file location containing the GeoJSON file(s) and a checkbox to toggle for recursively checking for GeoJSON files from user-defined file location

> **Note:** The tool is currently able to convert data following the WGS84 coordinate system

## Parsing and Converting GeoJSON Data

This tutorial provides the steps to parse and convert GeoJSON data into USD prims in Omniverse Composer. The *GeoJSON Converter (beta)* Extension is not enabled by default in Composer and will need to be enabled for use.

1. Open Omniverse Composer.

![](images/open-geospatial-consortium-extension_image_extension-window.png)

2. Navigate to **Window > GeoJSON Converter (beta)** to open the extension window.

![](images/Geojson-Ext_2_Select_extension.png)

3. Click on the **GeoJSON Converter (Beta)** tab.

![](images/Geojson-Ext_3_Geojson_ext_startup.png)

The window contains a collapsible window for settings for the extension. Below is a description of each field.

| Fields | Description |
|---|---|
| File location(s) | (string) starting directory path containing GeoJSON file(s) |
| Recursively check for GeoJSON files? | (checkbox) when set to True, extension will recursively check for GeoJSON files starting at this directory; otherwise, parse GeoJSON files at this directory |

4. In the "Settings" collapsible window, for the "File location(s)" field add the absolute path for the folder you wish to parse GeoJSON data from.

![](images/Geojson-Ext_4_Filled_url.png)

> **Note:** Providing a relative path will cause errors. Some paths may be invalid due to user read-write permissions and whether the folder exists.

5. In the "Settings" collapsible window, select or deselect the "Recursively check for GeoJSON files?" checkbox in order to recursively traverse through folders starting from the defined directory or only parse the files at the defined directory.

6. When inputs have been provided and ready, click on the **Convert GeoJSON File(s) button**.

> **Note:** The conversion may take some time to load.

7. Verify your feature(s) has/have been created in the stage by navigating to the Stage tab, clicking on the Geospatial prim, and hitting the F-key to focus on the desired feature.

![](images/Geojson-Ext_5_Generated_output_hierarchy_2023-1-0.png)

![](images/Geojson-Ext_6_Generated_output_stage.png)

> **Note:** You may not be able to see the feature, so try to zoom in and out. To help with rendering, follow the following steps.

8. (Optional) In your viewport, select the Perspective camera and select the three-slider icon to the right of Perspective.

![](images/OGC-Ext_16_perspective_camera.png)

9. (Optional) In the Properties tab, increase the far clipping range value. You can multiply the value by inserting a zero (0) before the decimal (.) point (i.e., "100000000.0" becomes "1000000000.0").

![](images/OGC-Ext_15_increase_far_clipping_range_add_0.png)

10. (Optional) If your GeoJSON file contains features with a "properties" object, then the GeoJSON Converter will convert each entry as a USD attribute for the given USD feature. Here are the currently supported GeoJSON property types:

| GeoJSON Type | Matching USD type in C++ and Python |
|---|---|
| boolean | PXR_NS::SdfValueTypeNames->Bool (save as bool) |
| number | PXR_NS::SdfValueTypeNames->Double (save as C++ double, Python float) |
| string | PXR_NS::SdfValueTypeNames->String (save as C++ std::string, Python str) |

The namespace of each attribute begins with "omni:kit:converter:geojson" then is followed by ":property_name". See below example of accessing attributes.

Here is an example of accessing the attributes in C++:

```cpp
bool readBool;
PXR_NS::UsdAttribute readBoolAttr = my_prim.GetAttribute( PXR_NS::TfToken("omni:kit:converter:geojson:my_boolean_attribute") );
readBoolAttr.Get( &readBool );

double readNumber;
PXR_NS::UsdAttribute readNumberAttr = my_prim.GetAttribute( PXR_NS::TfToken("omni:kit:converter:geojson:my_number_attribute") );
readNumberAttr.Get( &readNumber );

std::string readString;
PXR_NS::UsdAttribute readStringAttr = my_prim.GetAttribute( PXR_NS::TfToken("omni:kit:converter:geojson:my_string_attribute") );
readStringAttr.Get( &readString );
```

You can also view how to get the value of an attribute in Python from the Omniverse documentation here: https://docs.omniverse.nvidia.com/dev-guide/latest/programmer_ref/usd/properties/get-attribute-value.html

## Known Issues

### Rendering Issues

- When prims are placed far from origin, there are gaps between them. The user can select the set of prims with the "Features" Xform from where the file originated from then set the translation to {0,0,0}
