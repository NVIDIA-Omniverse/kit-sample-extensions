// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "UsdPCH.h"

// #define CPPHTTPLIB_READ_TIMEOUT_SECOND 100
// #define CPPHTTPLIB_READ_TIMEOUT_USECOND 100
#define CARB_EXPORTS

#include <carb/PluginUtils.h>
#include <carb/events/EventsUtils.h>
#include <carb/events/IEvents.h>
#include <carb/logging/Log.h>

#include <memory>
#include <set>

#define EXTENSION_NAME "omni.kit.converter.geojson.plugin"

#include <algorithm>
#include <fstream>
#include <iostream>
#include <math.h>
#include <string>
#include <utility> // std::pair, std::make_pair
#include <vector>

#ifdef _WIN32
// #include <windows.h>
// #include <tchar.h>
// #include <urlmon.h>
// #pragma comment(lib, "urlmon.lib")
// #pragma comment(lib,"wininet.lib")
#    include <filesystem>
namespace fs = std::filesystem;
#    include <stdlib.h>
#endif

#ifdef __linux__
// need alternative to urlmon
// #include <curl.h>
#    include <experimental/filesystem>
namespace fs = std::experimental::filesystem;
#endif

// include/geojson_converter/ include files
#include "geojson_converter/feature.h"
#include "geojson_converter/geojson_converter.h"

// include/omni/kit/converter/geojson/ include files
#include "omni/kit/converter/geojson/omniUsdHelper.h"
// #include "omni/kit/converter/geojson/types.h"
#include "nlohmann/json.hpp"
#include "omni/kit/converter/geojson/utils.h" //gets types.h
#include "omni/kit/converter/geojson/xformUtils.h"

PXR_NAMESPACE_USING_DIRECTIVE
// PXR_NAMESPACE_OPEN_SCOPE

// Omniverse logging is noisy, only enable it if verbose mode (-v)
static bool gOmniverseLoggingEnabled = false;

// Global for making the logging reasonable
static std::mutex gLogMutex;

using Vec2f = PXR_NS::GfVec2f;
using Vec3f = PXR_NS::GfVec3f;

using Vec3d = PXR_NS::GfVec3d;

using Vec3i = PXR_NS::GfVec3i;


static Vec3d gDefaultRotation(0);
static Vec3i gDefaultRotationOrder(0, 1, 2);
static Vec3d gDefaultScale(1);

// Multiplatform array size
#define HW_ARRAY_COUNT(array) (sizeof(array) / sizeof(array[0]))

// Private tokens for building up SdfPaths. We recommend
// constructing SdfPaths via tokens, as there is a performance
// cost to constructing them directly via strings (effectively,
// a table lookup per path element). Similarly, any API which
// takes a token as input should use a predefined token
// rather than one created on the fly from a string.
TF_DEFINE_PRIVATE_TOKENS(
    _tokens,
    (box)(DistantLight)(DomeLight)(Looks)(Root)(Shader)(st)

    // These tokens will be reworked or replaced by the official MDL schema for USD.
    // https://developer.nvidia.com/usd/MDLschema
    (Material)((_module, "module"))(name)(out)((shaderId, "mdlMaterial"))(mdl)

    // Tokens used for USD Preview Surface
    (weight) // added
    (diffuseColor)(roughness)(metallic)(normal)(file)(result)(varname)(rgb)(RAW)(sRGB)(surface)(PrimST)(UsdPreviewSurface)((
        stPrimvarName, "frame:stPrimvarName"))((UsdShaderId, "UsdPreviewSurface"))(
        (PrimStShaderId, "UsdPrimvarReader_float2"))(UsdUVTexture));

// Globals for Omniverse Connection and base Stage
static PXR_NS::UsdStageRefPtr stage;
static double stageScale;
static std::string downloadDirectory;

// Namespace for json.hpp
using json = nlohmann::json;

using value_t = nlohmann::detail::value_t;

std::vector<Feature*> features;
Coordinate firstCoordinate = Coordinate(0.0, 0.0, 0.0);

// Two functions below are for the Haversine formula
// https://stackoverflow.com/questions/27928/calculate-distance-between-two-latitude-longitude-points-haversine-formula
double deg2rad(double deg)
{
    return deg * (M_PI / 180.0);
}

double getDistanceFromLatLonInKm(double lat1, double lon1, double lat2, double lon2)
{
    double R = 6378.137; // Radius of the earth in km
    double dLat = deg2rad(lat2 - lat1); // deg2rad above
    double dLon = deg2rad(lon2 - lon1);
    double a =
        sin(dLat / 2.0) * sin(dLat / 2.0) + cos(deg2rad(lat1)) * cos(deg2rad(lat2)) * sin(dLon / 2.0) * sin(dLon / 2.0);
    double c = 2.0 * atan2(sqrt(a), sqrt(1.0 - a));
    double d = R * c; // Distance in km
    return d;
}

void cleanNameForUSD(std::string& nameIn, bool spacesOnly = false)
{
    if (nameIn.size() > 0)
    {
        if (nameIn.at(1) == ':')
        {
            // disk file
            return;
        }

        // Cannot start with a number
        if (nameIn[0] >= '0' && nameIn[0] <= '9')
            nameIn = "_" + nameIn;

        // Remove any non alphanumberic data from the string
        for (int x = 0; x < nameIn.size(); x++)
        {
            if (!spacesOnly && !(nameIn[x] >= '0' && nameIn[x] <= '9' || nameIn[x] >= 'A' && nameIn[x] <= 'Z' ||
                                 nameIn[x] >= 'a' && nameIn[x] <= 'z' || nameIn[x] == '_' || nameIn[x] == '/'))
            {
                nameIn[x] = '_';
            }
            else if (spacesOnly && nameIn[x] == ' ')
                nameIn[x] = '_';
        }
    }
    // Don't allow for a blank name
    else
    {
        nameIn = "Default";
    }
}

// Create a simple box in USD with normals and UV information
double h = 50.0;
int gBoxVertexIndices[] = { 0,  1,  2,  1,  3,  2,  4,  5,  6,  4,  6,  7,  8,  9,  10, 8,  10, 11,
                            12, 13, 14, 12, 14, 15, 16, 17, 18, 16, 18, 19, 20, 21, 22, 20, 22, 23 };
double gBoxNormals[][3] = { { 0, 0, -1 }, { 0, 0, -1 }, { 0, 0, -1 }, { 0, 0, -1 }, { 0, 0, 1 },  { 0, 0, 1 },
                            { 0, 0, 1 },  { 0, 0, 1 },  { 0, -1, 0 }, { 0, -1, 0 }, { 0, -1, 0 }, { 0, -1, 0 },
                            { 1, 0, 0 },  { 1, 0, 0 },  { 1, 0, 0 },  { 1, 0, 0 },  { 0, 1, 0 },  { 0, 1, 0 },
                            { 0, 1, 0 },  { 0, 1, 0 },  { -1, 0, 0 }, { -1, 0, 0 }, { -1, 0, 0 }, { -1, 0, 0 } };
double gBoxPoints[][3] = { { h, -h, -h }, { -h, -h, -h }, { h, h, -h },  { -h, h, -h }, { h, h, h },    { -h, h, h },
                           { -h, -h, h }, { h, -h, h },   { h, -h, h },  { -h, -h, h }, { -h, -h, -h }, { h, -h, -h },
                           { h, h, h },   { h, -h, h },   { h, -h, -h }, { h, h, -h },  { -h, h, h },   { h, h, h },
                           { h, h, -h },  { -h, h, -h },  { -h, -h, h }, { -h, h, h },  { -h, h, -h },  { -h, -h, -h } };
double gBoxUV[][2] = { { 0, 0 }, { 0, 1 }, { 1, 1 }, { 1, 0 }, { 0, 0 }, { 0, 1 }, { 1, 1 }, { 1, 0 },
                       { 0, 0 }, { 0, 1 }, { 1, 1 }, { 1, 0 }, { 0, 0 }, { 0, 1 }, { 1, 1 }, { 1, 0 },
                       { 0, 0 }, { 0, 1 }, { 1, 1 }, { 1, 0 }, { 0, 0 }, { 0, 1 }, { 1, 1 }, { 1, 0 } };

// Bind a material to this geometry
static void CreateMaterial(std::string primName, std::string meshName, UsdGeomMesh meshIn, const PXR_NS::SdfPath& rootPrimPath)
{
    // followed https://graphics.pixar.com/usd/release/tut_simple_shading.html
    // samples repo may have been missing the st reader? still not too familiar with it
    // Create a material instance for this in USD
    // Make path for "/Root/Looks/Fieldstone";
    PXR_NS::SdfPath matPath = rootPrimPath
                                  .AppendChild(_tokens->Looks)
                                  //    .AppendChild(PXR_NS::TfToken(primName))
                                  .AppendChild(PXR_NS::TfToken(meshName)); //_tokens->box);
    UsdShadeMaterial newMat = UsdShadeMaterial::Define(stage, matPath);

    // Add a UsdPreviewSurface
    std::string usdPreviewSurfaceShaderName = primName + "PreviewSurface";
    SdfPath shaderPath = matPath.AppendChild(TfToken(usdPreviewSurfaceShaderName));
    UsdShadeShader usdPreviewSurfaceShader = UsdShadeShader::Define(stage, shaderPath);
    usdPreviewSurfaceShader.CreateIdAttr(VtValue(_tokens->UsdPreviewSurface));
    UsdShadeInput roughnessInput = usdPreviewSurfaceShader.CreateInput(_tokens->roughness, SdfValueTypeNames->Float);

    UsdShadeOutput usdPreviewSurfaceOutput = newMat.CreateSurfaceOutput();
    usdPreviewSurfaceOutput.ConnectToSource(usdPreviewSurfaceShader.ConnectableAPI(), _tokens->surface);

    // Add Texturing
    std::string stReaderName = primName + "stReader";
    shaderPath = matPath.AppendChild(TfToken(stReaderName));
    UsdShadeShader primStShader = UsdShadeShader::Define(stage, shaderPath);
    primStShader.CreateIdAttr(VtValue(_tokens->PrimStShaderId));

    std::string diffuseColorShaderName = primName + "DiffuseColorTex";
    shaderPath = matPath.AppendChild(TfToken(diffuseColorShaderName));
    UsdShadeShader diffuseTextureSampler = UsdShadeShader::Define(stage, shaderPath);
    diffuseTextureSampler.CreateIdAttr(VtValue(_tokens->UsdUVTexture));
    UsdShadeInput texInput = diffuseTextureSampler.CreateInput(_tokens->file, SdfValueTypeNames->Asset);
    diffuseTextureSampler.CreateInput(_tokens->st, SdfValueTypeNames->Float2)
        .ConnectToSource(primStShader.CreateOutput(_tokens->result, SdfValueTypeNames->Float2));
    UsdShadeOutput diffuseTextureSamplerOutput =
        diffuseTextureSampler.CreateOutput(_tokens->rgb, SdfValueTypeNames->Float3);
    usdPreviewSurfaceShader.CreateInput((_tokens->diffuseColor), SdfValueTypeNames->Color3f)
        .ConnectToSource(diffuseTextureSampler.ConnectableAPI(), _tokens->rgb);

    UsdShadeInput stInput = newMat.CreateInput(_tokens->stPrimvarName, SdfValueTypeNames->Token);
    stInput.Set(_tokens->st);
    primStShader.CreateInput(_tokens->varname, SdfValueTypeNames->Token).ConnectToSource(stInput);

    // Final step, associate the material with the face
    PXR_NS::UsdShadeMaterialBindingAPI usdMaterialBinding(meshIn);
    usdMaterialBinding.Bind(newMat);

    // Commit the changes to the USD
    /// stage->Save();
    // omniUsdLiveProcess();
}

void CreateAttributes(PXR_NS::UsdPrim prim, Feature* feature)
{
    for (std::pair<std::string, bool> boolProperty : feature->boolProperties)
    {
        PXR_NS::UsdAttribute attrBool =
            prim.CreateAttribute(PXR_NS::TfToken(boolProperty.first), PXR_NS::SdfValueTypeNames->Bool, true);
        attrBool.Set(boolProperty.second);
    }
    for (std::pair<std::string, double> doubleProperty : feature->doubleProperties)
    {
        PXR_NS::UsdAttribute attrDouble =
            prim.CreateAttribute(PXR_NS::TfToken(doubleProperty.first), PXR_NS::SdfValueTypeNames->Double, true);
        attrDouble.Set((double)doubleProperty.second);
    }
    for (std::pair<std::string, std::string> stringProperty : feature->stringProperties)
    {
        PXR_NS::UsdAttribute attrString =
            prim.CreateAttribute(PXR_NS::TfToken(stringProperty.first), PXR_NS::SdfValueTypeNames->String, true);
        attrString.Set((std::string)stringProperty.second);
    }
    for (std::pair<std::string, PXR_NS::VtArray<PXR_NS::GfVec3d>> GfVec3dArray : feature->GfVec3dArrayProperties)
    {
        PXR_NS::UsdAttribute attrGfVec3dArray =
            prim.CreateAttribute(PXR_NS::TfToken(GfVec3dArray.first), PXR_NS::SdfValueTypeNames->Vector3dArray, true);
        attrGfVec3dArray.Set(GfVec3dArray.second);
    }
}

void CreateCenterRail()
{
    if (features.size() > 0)
    {
        // std::cout << "Creating center rails" << std::endl;
        std::set<std::string> completedPairs;
        Feature *leftRail, *rightRail;
        for (int i = 0; i < features.size(); i++)
        {
            // if we iterated to a feature who has a pair ID have not completed a center rail
            if (!features[i]->pairID.empty() && (completedPairs.find(features[i]->pairID) == completedPairs.end()))
            {

                // std::cout << "Found rail with pair ID" << std::endl;

                if (features[i]->propertyType == "Rail_Left")
                {
                    leftRail = features[i];
                    // std::cout << "It was a left rail." << std::endl;
                }
                else if (features[i]->propertyType == "Rail_Right")
                {
                    rightRail = features[i];
                    // std::cout << "It was a right rail." << std::endl;
                }
                // std::cout << "Index (i) was at: " << i << std::endl;
                // std::cout << "Index (j) starts at: " << i + 1 << std::endl;
                // iterate through rest of features list
                for (int j = i + 1; j < features.size(); j++)
                {
                    // found other pair
                    // add check if rail_center?
                    if (features[j]->pairID == features[i]->pairID)
                    {
                        // std::cout << "Found another rail with the same pair ID" << std::endl;
                        if (features[j]->propertyType == "Rail_Left")
                        {
                            leftRail = features[j];
                            // std::cout << "It was a left rail." << std::endl;
                        }
                        else if (features[j]->propertyType == "Rail_Right")
                        {
                            rightRail = features[j];
                            // std::cout << "It was a right rail." << std::endl;
                        }
                    }
                }
                // if we have not completed the pair for this rail, and both rails have been identified
                if (completedPairs.find(features[i]->pairID) == completedPairs.end() &&
                    (leftRail != nullptr && rightRail != nullptr))
                {
                    // std::cout << "Both rails found for pair ID " << features[i]->pairID << std::endl;
                    Feature* centerRail = new Feature();

                    // read feature, geometry, type object key
                    centerRail->geometryType = leftRail->geometryType;
                    // std::cout << "Feature, Geometry, Type: " << feature_object->geometryType << std::endl;

                    // read feature, properties elements
                    // read feature, properties, object id element
                    centerRail->object_id = leftRail->pairID + "_Center_Rail";

                    // read feature, properties, type element
                    centerRail->propertyType = "Rail_Center";

                    // read feature, properties, Pair_ID element
                    centerRail->pairID = leftRail->pairID;

                    // read feature, properties, material element
                    centerRail->material = leftRail->material;
                    // std::cout << "Feature, Properties, Material: " << feature_object->material << std::endl;

                    // read feature, geometry, coordinate elements
                    // std::cout << "Feature, Geometry, Coordinates" << std::endl;
                    // 0 added as a check
                    int numVert =
                        std::max<int>((std::min(leftRail->coordinates.size(), rightRail->coordinates.size())), 0);

                    if (numVert > 0)
                    {
                        for (int c = 0; c < numVert; c++)
                        {
                            double longDiff =
                                (rightRail->coordinates[c].longitude) - (leftRail->coordinates[c].longitude);
                            double latDiff = (rightRail->coordinates[c].latitude) - (leftRail->coordinates[c].latitude);
                            double elevDiff = (rightRail->coordinates[c].altitude) - (leftRail->coordinates[c].altitude);

                            Coordinate centCoor((rightRail->coordinates[c].longitude - (longDiff / 2.0)),
                                                (rightRail->coordinates[c].latitude - (latDiff / 2.0)),
                                                (rightRail->coordinates[c].altitude - (elevDiff / 2.0)));

                            // double distance = sqrt(pow(longDiff, 2) + pow(latDiff, 2));
                            // centCoor.roll = atan2(p1.altitude - p2.altitude, p1.distance - p2.distance)

                            centerRail->coordinates.push_back(centCoor);
                        }
                        // std::cout << "Created center rail " << centerRail->pairID << std::endl;
                        features.push_back(centerRail);
                        leftRail = NULL;
                        rightRail = NULL;
                        completedPairs.insert(features[i]->pairID);
                    }
                    else
                    {
                        // std::cout << "Failed to create a center rail with this pair due to coordinates error..." <<
                        // std::endl;
                    }
                }
            }
        }
    }
    else
    {
        // std::cout << "No features exist. Cannot check for and create center rails" << std::endl;
    }
}

void CreateRailways(Feature* feature, const PXR_NS::SdfPath& rootPrimPath, std::string objectID)
{
    if (feature->geometryType == "Point" && feature->coordinates.size() > 0)
    {
        // std::cout << "debugging: CreateRailways, Point, start" << std::endl;
        std::string pointName("Point_" + objectID);
        // std::cout << "debugging: CreateRailways, Point, clean name" << std::endl;
        cleanNameForUSD(pointName);
        // pointName.append(std::to_string(featureNumber));
        PXR_NS::SdfPath pointXformPath =
            rootPrimPath.AppendChild(PXR_NS::TfToken("Points")).AppendChild(PXR_NS::TfToken(pointName));
        // std::cout << "debugging: CreateRailways, Point, path: " << pointXformPath.GetString() << std::endl;

        // std::cout << "debugging: CreateRailways, Point, checking if prim exists at path" << std::endl;

        if (!stage->GetPrimAtPath(pointXformPath))
        {
            // std::cout << "Prim name: " << pointXformPath << std::endl;
            // std::cout << "debugging: CreateRailways, Point, defining UsdGeomMesh" << std::endl;
            UsdGeomMesh mesh = PXR_NS::UsdGeomMesh::Define(stage, pointXformPath);
            UsdModelAPI(mesh).SetKind(KindTokens->model);
            mesh.AddTranslateOp(PXR_NS::UsdGeomXformOp::PrecisionDouble);
            mesh.AddRotateXYZOp(PXR_NS::UsdGeomXformOp::PrecisionDouble);
            mesh.AddScaleOp(PXR_NS::UsdGeomXformOp::PrecisionDouble).Set(GfVec3d(1.0));

            // PXR_NS::SdfPath boxPrimPath = pointXformPath.AppendChild(PXR_NS::TfToken(pointName + "_Box"));

            // UsdGeomMesh mesh = UsdGeomMesh::Define(stage, boxPrimPath);

            // Add all of the vertices
            // std::cout << "debugging: CreateRailways, Point, points data" << std::endl;
            int num_vertices = HW_ARRAY_COUNT(gBoxPoints);
            VtArray<GfVec3f> points;
            double offsetLong = feature->coordinates[0].longitude;
            double offsetLat = feature->coordinates[0].latitude;
            double offsetAlt = feature->coordinates[0].altitude;
            points.resize(num_vertices);
            for (int i = 0; i < num_vertices; i++)
            {
                points[i] = GfVec3f(gBoxPoints[i][0], gBoxPoints[i][1], gBoxPoints[i][2]);
            }
            mesh.CreatePointsAttr(VtValue(points));

            // std::cout << "debugging: CreateRailways, Point, indices data" << std::endl;
            // Calculate indices for each triangle
            int num_indices = HW_ARRAY_COUNT(gBoxVertexIndices); // 2 Triangles per face * 3 Vertices per Triangle * 6
                                                                 // Faces
            VtArray<int> vecIndices;
            vecIndices.resize(num_indices);
            for (int i = 0; i < num_indices; i++)
            {
                vecIndices[i] = gBoxVertexIndices[i];
            }
            mesh.CreateFaceVertexIndicesAttr(VtValue(vecIndices));

            // Add vertex normals
            // std::cout << "debugging: CreateRailways, Point, normals data" << std::endl;
            int num_normals = HW_ARRAY_COUNT(gBoxNormals);
            VtArray<GfVec3f> meshNormals;
            meshNormals.resize(num_vertices);
            for (int i = 0; i < num_vertices; i++)
            {
                meshNormals[i] = GfVec3f((double)gBoxNormals[i][0], (double)gBoxNormals[i][1], (double)gBoxNormals[i][2]);
            }
            mesh.CreateNormalsAttr(VtValue(meshNormals));

            // Add face vertex count
            // std::cout << "debugging: CreateRailways, Point, vertex count data" << std::endl;
            VtArray<int> faceVertexCounts;
            faceVertexCounts.resize(12); // 2 Triangles per face * 6 faces
            std::fill(faceVertexCounts.begin(), faceVertexCounts.end(), 3);
            mesh.CreateFaceVertexCountsAttr(VtValue(faceVertexCounts));

            // Set the color on the mesh
            // std::cout << "debugging: CreateRailways, Point, color" << std::endl;
            UsdAttribute displayColorAttr = mesh.CreateDisplayColorAttr();
            {
                VtVec3fArray valueArray;
                GfVec3f rgbFace(0.3f, 0.3f, 0.3f);
                valueArray.push_back(rgbFace);
                displayColorAttr.Set(valueArray);
            }

            // // std::cout << "debugging: CreateRailways, Point, UV (st) data" << std::endl;
            // // Set the UV (st) values for this mesh
            // UsdGeomPrimvar attr2 = mesh.CreatePrimvar(_tokens->st, SdfValueTypeNames->TexCoord2fArray);
            // {
            //     int uv_count = HW_ARRAY_COUNT(gBoxUV);
            //     VtVec2fArray valueArray;
            //     valueArray.resize(uv_count);
            //     for (int i = 0; i < uv_count; ++i)
            //     {
            //         valueArray[i].Set((float)(gBoxUV[i]));
            //     }

            //     bool status = attr2.Set(valueArray);
            // }
            // attr2.SetInterpolation(UsdGeomTokens->vertex);

            double east = 1.0;
            if (feature->coordinates[0].longitude < 0.0)
            {
                east *= -1.0;
            }
            double north = 1.0;
            if (feature->coordinates[0].latitude < 0.0)
            {
                north *= -1.0;
            }
            double kmToM = 1000.0;

            // PXR_NS::GfVec3d result = GeodeticToCartesian(PXR_NS::GfVec3d(feature->coordinates[0].latitude,
            // feature->coordinates[0].longitude, feature->coordinates[0].altitude)); std::cout << "new: "; std::cout <<
            // "\t" << std::to_string(result[0]) << " / "; std::cout << std::to_string(result[1]) << " / "; std::cout <<
            // std::to_string(result[2]); std::cout << std::endl; std::cout << "old: "; std::cout << "\t" <<
            // std::to_string(-1.0 * east * getDistanceFromLatLonInKm(0.0, 0.0, 0.0, feature->coordinates[0].longitude)
            // * kmToM) << " / "; std::cout << std::to_string(feature->coordinates[0].altitude) << " / "; std::cout <<
            // std::to_string(north * getDistanceFromLatLonInKm(0.0, 0.0, feature->coordinates[0].latitude, 0.0) *
            // kmToM); std::cout << std::endl;

            // Move it
            // std::cout << "debugging: CreateRailways, Point, setting transform" << std::endl;
            xformUtils::setLocalTransformSRT(
                /* USD Prim */ mesh.GetPrim(),
                /* translation */
                GfVec3d(
                    static_cast<double>(-1.0 * east * kmToM *
                                        (getDistanceFromLatLonInKm(0.0, 0.0, 0.0, offsetLong) -
                                         getDistanceFromLatLonInKm(0.0, 0.0, 0.0, firstCoordinate.longitude))), // lat(deg)
                                                                                                                // -> km
                    static_cast<double>(offsetAlt - firstCoordinate.altitude), // y-axis
                    static_cast<double>(north * kmToM *
                                        (getDistanceFromLatLonInKm(0.0, 0.0, offsetLat, 0.0) -
                                         getDistanceFromLatLonInKm(0.0, 0.0, 0.0, firstCoordinate.latitude))) // long(deg)
                                                                                                              // -> km
                    ),
                /* rotation */ GfVec3d(0.0, 0.0, 0.0),
                /* gDefaultRotationOrder */ gDefaultRotationOrder,
                /* gDefaultScale */ gDefaultScale);

            // PXR_NS::GfVec3d offsetCoor = GeodeticToCartesian(PXR_NS::GfVec3d(offsetLat, offsetLong, offsetAlt));

            // xformUtils::setLocalTransformSRT(/* USD Prim */ mesh.GetPrim(),
            // /* translation */ GfVec3d(
            //                         static_cast<double>(-1.0 * east * offsetCoor[0] * kmToM),   //lat(deg)  -> km
            //                         static_cast<double>(north * offsetCoor[1] * kmToM),         //long(deg) -> km
            //                         static_cast<double>(offsetCoor[2]) // y-axis
            //                         ),
            // /* rotation */ GfVec3d(0.0, 180.0, 0.0),
            // /* gDefaultRotationOrder */ gDefaultRotationOrder,
            // /* gDefaultScale */ gDefaultScale);

            // std::cout << "debugging: CreateRailways, Point, creating attributes" << std::endl;
            CreateAttributes(mesh.GetPrim(), feature);
            // std::cout << "debugging: CreateRailways, Point, finished creating mesh" << std::endl;
        }
    }
    else if (feature->geometryType == "LineString" && feature->coordinates.size() > 1)
    {
        std::string lineName("LineString_" + objectID);
        cleanNameForUSD(lineName);
        // lineName.append(std::to_string(featureNumber));
        PXR_NS::SdfPath lineStringXformPath = rootPrimPath.AppendChild(PXR_NS::TfToken("LineStrings"));

        // if (!feature->pairID.empty()){
        //     std::string pair = feature->pairID;
        //     cleanNameForUSD(pair);
        //     lineStringXformPath = lineStringXformPath.AppendChild(PXR_NS::TfToken("Paired_Rails"))
        //                                              .AppendChild(PXR_NS::TfToken(pair));
        //     if (feature->propertyType == "Rail_Left"){
        //         lineStringXformPath = lineStringXformPath.AppendChild(PXR_NS::TfToken("Rail_Left"));
        //     }
        //     else if (feature->propertyType == "Rail_Right"){
        //         lineStringXformPath = lineStringXformPath.AppendChild(PXR_NS::TfToken("Rail_Right"));
        //     }
        //     else if (feature->propertyType == "Rail_Center"){
        //         lineStringXformPath = lineStringXformPath.AppendChild(PXR_NS::TfToken("Rail_Center"));
        //     }
        // }

        lineStringXformPath = lineStringXformPath.AppendChild(PXR_NS::TfToken(lineName));

        if (!stage->GetPrimAtPath(lineStringXformPath))
        {
            // std::cout << "Prim name: " << lineStringXformPath << std::endl;
            PXR_NS::UsdGeomBasisCurves lineMesh = PXR_NS::UsdGeomBasisCurves::Define(stage, lineStringXformPath);
            UsdModelAPI(lineMesh).SetKind(KindTokens->model);

            // PXR_NS::SdfPath railwayPrimPath = lineStringXformPath.AppendChild(PXR_NS::TfToken(lineName));

            PXR_NS::VtArray<GfVec3f> parsed_curve_points(feature->coordinates.size());
            PXR_NS::VtArray<float> width_beta(feature->coordinates.size());

            double offsetLong = feature->coordinates[0].longitude;
            double offsetLat = feature->coordinates[0].latitude;
            double offsetAlt = feature->coordinates[0].altitude;
            double kmToM = 1000.0;
            // std::cout << "lineName: " << lineName << std::endl;
            for (int i = 0; i < feature->coordinates.size(); i++)
            {
                Coordinate coordinate = feature->coordinates[i];
                double resLong = coordinate.longitude - offsetLong;
                double resLat = coordinate.latitude - offsetLat;
                double east = 1.0;
                // if (resLong < 0.0){
                // east *= -1.0;
                // }
                double north = 1.0;
                // if (resLat < 0.0){
                // north *= -1.0;
                // }
                // std::cout << "coordinate.latitude: " << coordinate.latitude << std::endl;
                // std::cout << "offsetLat: " << offsetLat << std::endl;
                // std::cout << "coordinate.latitude - offsetLong: " << coordinate.latitude - offsetLat << std::endl;
                // std::cout << "coordinate.longitude: " << coordinate.longitude << std::endl;
                // std::cout << "offsetLong: " << offsetLong << std::endl;
                // std::cout << "coordinate.longitude - offsetLong: " << coordinate.longitude - offsetLong << std::endl;
                // std::cout << "coordinate.altitude: " << coordinate.altitude << std::endl;
                // PXR_NS::GfVec3d convCoor = GeodeticToCartesian(PXR_NS::GfVec3d(coordinate.latitude - offsetLat,
                // coordinate.longitude - offsetLong, coordinate.altitude - offsetAlt)); PXR_NS::GfVec3d offsetCoor =
                // GeodeticToCartesian(PXR_NS::GfVec3d(offsetLat, offsetLong, offsetAlt)); convCoor -= offsetCoor;
                // std::cout.precision(17);
                // std::cout << "coordinate before GfVec3f: " << std::endl;
                // std::cout << "\tLatitude: " << std::fixed << (coordinate.latitude) << std::endl;
                // std::cout << "\tLongitude: " << std::fixed << (coordinate.longitude) << std::endl;
                // std::cout << "\tElevation: " << std::fixed << (coordinate.altitude) << std::endl;
                parsed_curve_points[i] = GfVec3f(
                    // (-1.0 * east * (getDistanceFromLatLonInKm(0.0, 0.0, 0.0, (resLong))) * kmToM),   //lat(deg)  ->
                    // km (coordinate.altitude - offsetAlt) * 100.0, //m         -> km (north *
                    // (getDistanceFromLatLonInKm(0.0, 0.0, (resLat), 0.0)) * kmToM));     //long(deg) -> km
                    // ((getDistanceFromLatLonInKm(0.0, 0.0, 0.0, (coordinate.longitude))) * kmToM),   //lat(deg)  -> km
                    // (coordinate.altitude) * 100.0,                                                    //m         ->
                    // km
                    // ((getDistanceFromLatLonInKm(0.0, 0.0, (coordinate.latitude), 0.0)) * kmToM));     //long(deg) ->
                    // km

                    (kmToM * east *
                     (getDistanceFromLatLonInKm(0.0, 0.0, 0.0, coordinate.longitude) -
                      getDistanceFromLatLonInKm(0.0, 0.0, 0.0, offsetLong))), // lat(deg)  -> km
                    ((coordinate.altitude - offsetAlt)), // m         -> km
                    (-(kmToM * north *
                       (getDistanceFromLatLonInKm(0.0, 0.0, coordinate.latitude, 0.0) -
                        getDistanceFromLatLonInKm(0.0, 0.0, offsetLat, 0.0))))); // long(deg) -> km
                // static_cast<double>(kmToM * east * convCoor[0]),   //lat(deg)  -> km
                // static_cast<double>(convCoor[1]),                                                    //m         ->
                // km static_cast<double>((kmToM * north * convCoor[2])));     //long(deg) -> km
                // TODO: width based on scale of world (or meters per unit) from WGS84 schema
                // width_beta[i] = { 0.3f * 100.0 };
                // std::cout << "coordinate after GfVec3f: " << std::endl;
                // std::cout << "\tLatitude: " << std::fixed << (parsed_curve_points[i][2]) << std::endl;
                // std::cout << "\tLongitude: " << std::fixed << (parsed_curve_points[i][0]) << std::endl;
                // std::cout << "\tElevation: " << std::fixed << (parsed_curve_points[i][1]) << std::endl;
                width_beta[i] = { 0.3f };
            }

            // collect points from CSV...
            // PXR_NS::UsdGeomBasisCurves lineMesh = PXR_NS::UsdGeomBasisCurves::Define(stage, railwayPrimPath);
            PXR_NS::VtArray<GfVec3f> disp_color_beta;

            if (feature->propertyType == "Rail_Left")
            {
                disp_color_beta = { GfVec3f(1.0, 0.0, 0.0) };
            }
            else if (feature->propertyType == "Rail_Right")
            {
                disp_color_beta = { GfVec3f(0.0, 1.0, 0.0) };
            }
            else if (feature->propertyType == "Rail_Center")
            {
                disp_color_beta = { GfVec3f(1.0, 1.0, 0.0) };
            }
            else
            {
                disp_color_beta = { GfVec3f(0.3, 0.3, 0.3) };
            }
            // PXR_NS::VtArray<double> width_beta = { 20.0f }; //{ 1.5f };
            PXR_NS::VtArray<int> vertex_count = { (int)parsed_curve_points.size() };
            // std::cout << "vertex_count: " << vertex_count << std::endl;

            // // From https://graphics.pixar.com/usd/dev/api/class_usd_geom_basis_curves.html
            // // type	    wrap	                        validitity
            // // linear   nonperiodic	                    curveVertexCounts[i] > 2
            // // linear	periodic	                    curveVertexCounts[i] > 3
            // // cubic	nonperiodic	                    (curveVertexCounts[i] - 4) % vstep == 0
            // // cubic	periodic	                    (curveVertexCounts[i]) % vstep == 0
            // // cubic	pinned (catmullRom/bspline)     (curveVertexCounts[i] - 2) >= 0

            // // Vertex count requirements
            // // bezier 3
            // // catmullRom 1... or 2?
            // // bspline 1

            // // vstep review:
            // // vstep = 1
            // //  [0 1 2 3] becomes [1 2 3 4]
            // // vstep = 3
            // //  [0 1 2 3] becomes [3 4 5 6]
            // // if vstep is 3 (number of vertices is divisible by 3)
            // if ((vertex_count[0] - 4) % 3 == 0) {
            //     lineMesh.GetTypeAttr().Set(TfToken("cubic"));
            // }
            // else {
            //     lineMesh.GetTypeAttr().Set(TfToken("linear"));
            // }

            // if (vertex_count[0] < 3) {
            // // if (feature->coordinates.size() < 3) {
            //     lineMesh.GetBasisAttr().Set(TfToken("bspline"));
            //     // lineMesh.GetWrapAttr().Set(TfToken("nonperiodic"));
            // }
            // else {
            //     // lineMesh.GetTypeAttr().Set(TfToken("cubic"));
            //     // lineMesh.GetWrapAttr().Set(TfToken("nonperiodic"));
            //     lineMesh.SetWidthsInterpolation(TfToken("constant"));
            //     // lineMesh.GetBasisAttr().Set(TfToken("catmullRom"));
            //     lineMesh.GetBasisAttr().Set(TfToken("bezier"));
            //     // lineMesh.GetBasisAttr().Set(TfToken("bspline"));
            // }

            lineMesh.GetTypeAttr().Set(TfToken("linear"));
            // lineMesh.GetBasisAttr().Set(TfToken("bspline"));
            // lineMesh.GetWrapAttr().Set(TfToken("nonperiodic"));
            lineMesh.GetCurveVertexCountsAttr().Set(vertex_count);
            lineMesh.GetDisplayColorAttr().Set(disp_color_beta);
            lineMesh.CreatePointsAttr(PXR_NS::VtValue(parsed_curve_points));
            lineMesh.GetWidthsAttr().Set(width_beta);

            double east = 1.0;
            if (feature->coordinates[0].longitude < 0.0)
            {
                east *= -1.0;
            }
            double north = 1.0;
            if (feature->coordinates[0].latitude < 0.0)
            {
                north *= -1.0;
            }

            // xformUtils::setLocalTransformSRT(/* USD Prim */ lineMesh.GetPrim(),
            // /* translation */ GfVec3d(
            //                         (0.0,   //lat(deg)  -> km
            //                         0.0,                                                                        //
            //                         y-axis 0.0)),     //long(deg) -> km
            //                         // (-1.0 * east * getDistanceFromLatLonInKm(0.0, 0.0, 0.0, offsetLong) * kmToM,
            //                         //lat(deg)  -> km
            //                         // offsetAlt * 100.0, // y-axis
            //                         // north * getDistanceFromLatLonInKm(0.0, 0.0, offsetLat, 0.0) * kmToM)),
            //                         //long(deg) -> km
            // /* rotation */ GfVec3d(0.0, 0.0, 0.0),
            // /* gDefaultRotationOrder */ gDefaultRotationOrder,
            // /* gDefaultScale */ gDefaultScale);

            // PXR_NS::UsdPrim prim = lineMesh.GetPrim();
            // prim.ApplyAPI(pos_api);
            // prim.CreateAttribute(PXR_NS::TfToken("omni:geospatial:wgs84:localPosition"),
            // SdfValueTypeNames->Double3).Set((offsetLat, offsetLong, offsetAlt));

            // std::cout << "Translation: " << std::endl;
            // std::cout << "\tX: " << std::fixed << ((-1.0 * east * getDistanceFromLatLonInKm(0.0, 0.0, 0.0,
            // offsetLong) * kmToM)) << std::endl; std::cout << "\tY: " << std::fixed << ((offsetAlt)) << std::endl;
            // std::cout << "\tZ: " << std::fixed << ((north * getDistanceFromLatLonInKm(0.0, 0.0, offsetLat, 0.0) *
            // kmToM)) << std::endl;

            lineMesh.AddTranslateOp(PXR_NS::UsdGeomXformOp::PrecisionDouble)
                .Set(GfVec3d((-1.0 * east * kmToM *
                              (getDistanceFromLatLonInKm(0.0, 0.0, 0.0, offsetLong) -
                               getDistanceFromLatLonInKm(0.0, 0.0, 0.0, firstCoordinate.longitude))), // lat(deg)  -> km
                             (offsetAlt - firstCoordinate.altitude), // y-axis
                             (north * kmToM *
                              (getDistanceFromLatLonInKm(0.0, 0.0, offsetLat, 0.0) -
                               getDistanceFromLatLonInKm(0.0, 0.0, 0.0, firstCoordinate.latitude))) // long(deg) -> km
                             ));
            lineMesh.AddRotateXYZOp(PXR_NS::UsdGeomXformOp::PrecisionDouble).Set(GfVec3d(0.0, 180.0, 0.0));
            lineMesh.AddScaleOp(PXR_NS::UsdGeomXformOp::PrecisionDouble).Set(gDefaultScale);

            // xformUtils::setLocalTransformSRT(/* USD Prim */ lineMesh.GetPrim(),
            // /* translation */ GfVec3d(
            //                         (-1.0 * east * getDistanceFromLatLonInKm(0.0, 0.0, 0.0, offsetLong) * kmToM),
            //                         //lat(deg)  -> km (offsetAlt), // y-axis (north * getDistanceFromLatLonInKm(0.0,
            //                         0.0, offsetLat, 0.0) * kmToM)         //long(deg) -> km
            //                         ),
            // /* rotation */ GfVec3d(0.0, 180.0, 0.0),
            // /* gDefaultRotationOrder */ gDefaultRotationOrder,
            // /* gDefaultScale */ gDefaultScale);

            // PXR_NS::GfVec3d offsetCoor = GeodeticToCartesian(PXR_NS::GfVec3d(offsetLat, offsetLong, offsetAlt));

            // xformUtils::setLocalTransformSRT(/* USD Prim */ lineMesh.GetPrim(),
            // /* translation */ GfVec3d(
            //                         static_cast<double>(-1.0 * east * offsetCoor[0] * kmToM),   //lat(deg)  -> km
            //                         static_cast<double>(north * offsetCoor[1] * kmToM),         //long(deg) -> km
            //                         static_cast<double>(offsetCoor[2]) // y-axis
            //                         ),
            // /* rotation */ GfVec3d(0.0, 180.0, 0.0),
            // /* gDefaultRotationOrder */ gDefaultRotationOrder,
            // /* gDefaultScale */ gDefaultScale);

            // return lineMesh;
            CreateAttributes(lineMesh.GetPrim(), feature);
        }
    }
    else if (feature->geometryType == "Polygon" && feature->coordinates.size() > 2)
    {
        std::string polygonName("Polygon_" + objectID);
        cleanNameForUSD(polygonName);
        // polygonName.append(std::to_string(featureNumber));
        PXR_NS::SdfPath polygonXformPath =
            rootPrimPath.AppendChild(PXR_NS::TfToken("Polygons")).AppendChild(PXR_NS::TfToken(polygonName));
        // std::cout << "polygonXformPath: " << polygonXformPath << std::endl;

        if (!stage->GetPrimAtPath(polygonXformPath))
        {
            PXR_NS::UsdGeomMesh polygon_mesh = PXR_NS::UsdGeomMesh::Define(stage, polygonXformPath);
            UsdModelAPI(polygon_mesh).SetKind(KindTokens->model);
            polygon_mesh.AddTranslateOp(PXR_NS::UsdGeomXformOp::PrecisionDouble);
            polygon_mesh.AddRotateXYZOp(PXR_NS::UsdGeomXformOp::PrecisionDouble);
            polygon_mesh.AddScaleOp(PXR_NS::UsdGeomXformOp::PrecisionDouble).Set(GfVec3d(1.0));

            // PXR_NS::SdfPath railwayPrimPath = polygonXformPath.AppendChild(PXR_NS::TfToken(polygonName + "_Mesh"));

            PXR_NS::VtArray<GfVec3f> parsed_curve_points(feature->coordinates.size());

            double offsetLong = feature->coordinates[0].longitude;
            double offsetLat = feature->coordinates[0].latitude;
            double offsetAlt = feature->coordinates[0].altitude;
            double kmToM = 1000.0;

            PXR_NS::VtArray<Vec2d> st(feature->coordinates.size());
            PXR_NS::VtArray<int> vertexCount = { (int)parsed_curve_points.size() };
            PXR_NS::VtArray<int> vertexIndices(feature->coordinates.size());
            for (int i = 0; i < feature->coordinates.size(); i++)
            {
                Coordinate coordinate = feature->coordinates[i];
                double resLong = coordinate.longitude - offsetLong;
                double resLat = coordinate.latitude - offsetLat;
                double east = 1.0;
                // if (resLong < 0.0){
                // east *= -1.0;
                // }
                double north = 1.0;
                // if (resLat < 0.0){
                // north *= -1.0;
                // }
                // std::cout << "coordinate.longitude: " << coordinate.longitude << std::endl;
                // std::cout << "offsetLong: " << offsetLong << std::endl;
                // std::cout << "coordinate.longitude - offsetLong: " << coordinate.longitude - offsetLong << std::endl;
                // std::cout << "coordinate.latitude: " << coordinate.latitude << std::endl;
                // std::cout << "offsetLat: " << offsetLat << std::endl;
                // std::cout << "coordinate.latitude - offsetLong: " << coordinate.latitude - offsetLat << std::endl;
                // parsed_curve_points[i] = GfVec3f(
                //     (getDistanceFromLatLonInKm(0.0, 0.0, 0.0, coordinate.longitude) * kmToM),   //lat(deg)  -> km
                //     (coordinate.altitude * 100.0),                                                    //m         ->
                //     km (getDistanceFromLatLonInKm(0.0, 0.0, coordinate.latitude, 0.0) * kmToM));     //long(deg) ->
                //     km
                // PXR_NS::GfVec3d convCoor = GeodeticToCartesian(PXR_NS::GfVec3d(coordinate.latitude - offsetLat,
                // coordinate.longitude - offsetLong, coordinate.altitude - offsetAlt)); PXR_NS::GfVec3d offsetCoor =
                // GeodeticToCartesian(PXR_NS::GfVec3d(offsetLat, offsetLong, offsetAlt)); convCoor -= offsetCoor;
                parsed_curve_points[i] =
                    GfVec3f((kmToM * east *
                             (getDistanceFromLatLonInKm(0.0, 0.0, 0.0, coordinate.longitude) -
                              getDistanceFromLatLonInKm(0.0, 0.0, 0.0, offsetLong))), // lat(deg)  -> km
                            ((coordinate.altitude - offsetAlt)), // m         -> km
                            (-1.0 * (kmToM * north *
                                     (getDistanceFromLatLonInKm(0.0, 0.0, coordinate.latitude, 0.0) -
                                      getDistanceFromLatLonInKm(0.0, 0.0, offsetLat, 0.0))))); // long(deg) -> km
                // static_cast<double>(kmToM * east * convCoor[0]),   //lat(deg)  -> km
                // static_cast<double>(convCoor[1]),                                                    //m         ->
                // km static_cast<double>((kmToM * north * convCoor[2])));     //long(deg) -> km
                st[i] = Vec2d{ coordinate.longitude, coordinate.latitude };
                vertexIndices[i] = { i };
            }

            // std::cout << "railwayPrimPath: " << polygonXformPath << std::endl;
            // auto polygon_mesh = PXR_NS::UsdGeomMesh::Define(stage, railwayPrimPath);
            // UsdModelAPI(polygon_mesh).SetKind(KindTokens->model);
            // polygon_mesh.GetPrim().GetParent().AddTranslateOp(PXR_NS::UsdGeomXformOp::PrecisionDouble);
            // polygon_mesh.GetPrim().GetParent().AddRotateXYZOp(PXR_NS::UsdGeomXformOp::PrecisionDouble);
            // polygon_mesh.GetPrim().GetParent().AddScaleOp(PXR_NS::UsdGeomXformOp::PrecisionDouble).Set(GfVec3d(1.0));

            polygon_mesh.CreatePointsAttr().Set(parsed_curve_points);
            polygon_mesh.CreateFaceVertexCountsAttr().Set(vertexCount);
            polygon_mesh.CreateFaceVertexIndicesAttr().Set(vertexIndices);
            // polygon_mesh.GetDoubleSidedAttr().Set(true);

            // auto polygon_mesh_primvars_api =
            //     PXR_NS::UsdGeomPrimvarsAPI(polygon_mesh.GetPrim());
            // polygon_mesh_primvars_api
            //     .CreatePrimvar(PXR_NS::TfToken("st"), PXR_NS::SdfValueTypeNames->Float2Array,
            //                     PXR_NS::UsdGeomTokens->vertex)
            //     .Set(st);

            // texCoords.Set([(0, 0), (1, 0), (1,1), (0, 1)])

            double east = 1.0;
            if (feature->coordinates[0].longitude < 0.0)
            {
                east *= -1.0;
            }
            double north = 1.0;
            if (feature->coordinates[0].latitude < 0.0)
            {
                north *= -1.0;
            }

            // xformUtils::setLocalTransformSRT(/* USD Prim */ polygonName.GetPrim(),
            // /* translation */ GfVec3d((0.0,   //lat(deg)  -> km
            //                            0.0,                                                                        //
            //                            y-axis 0.0)),     //long(deg) -> km
            // /* rotation */ GfVec3d(0.0, 0.0, 0.0),
            // /* gDefaultRotationOrder */ gDefaultRotationOrder,
            // /* gDefaultScale */ gDefaultScale);

            xformUtils::setLocalTransformSRT(
                /* USD Prim */ polygon_mesh.GetPrim(),
                /* translation */
                GfVec3d((-1.0 * east * kmToM *
                         (getDistanceFromLatLonInKm(0.0, 0.0, 0.0, offsetLong) -
                          getDistanceFromLatLonInKm(0.0, 0.0, 0.0, firstCoordinate.longitude))), // lat(deg)  -> km
                        (offsetAlt - firstCoordinate.altitude), // y-axis
                        (north * kmToM *
                         (getDistanceFromLatLonInKm(0.0, 0.0, offsetLat, 0.0) -
                          getDistanceFromLatLonInKm(0.0, 0.0, 0.0, firstCoordinate.latitude)))), // long(deg) -> km
                /* rotation */ GfVec3d(0.0, 180.0, 0.0),
                /* gDefaultRotationOrder */ gDefaultRotationOrder,
                /* gDefaultScale */ gDefaultScale);

            // PXR_NS::GfVec3d offsetCoor = GeodeticToCartesian(PXR_NS::GfVec3d(offsetLat, offsetLong, offsetAlt));

            // xformUtils::setLocalTransformSRT(/* USD Prim */ polygon_mesh.GetPrim(),
            // /* translation */ GfVec3d(
            //                         static_cast<double>(-1.0 * east * offsetCoor[0] * kmToM),   //lat(deg)  -> km
            //                         static_cast<double>(north * offsetCoor[1] * kmToM),         //long(deg) -> km
            //                         static_cast<double>(offsetCoor[2]) // y-axis
            //                         ),
            // /* rotation */ GfVec3d(0.0, 180.0, 0.0),
            // /* gDefaultRotationOrder */ gDefaultRotationOrder,
            // /* gDefaultScale */ gDefaultScale);

            CreateMaterial(polygonName, polygonName, polygon_mesh, polygon_mesh.GetPrim().GetPath());

            // return NULL;

            CreateAttributes(polygon_mesh.GetPrim(), feature);
        }
    }
}

void ReadCoordinatesList(Feature* feature_object, nlohmann::json json_coordinates_list)
{
    for (auto coordinateGroup = json_coordinates_list.begin(); coordinateGroup != json_coordinates_list.end();
         coordinateGroup++)
    {
        /*	GeoJSON - "coordinates" is a list consisting of coordinate lists
         *	URL: https://datatracker.ietf.org/doc/html/rfc7946
         *	Description: " The first two elements are longitude and
         *	latitude, or easting and northing, precisely in that order
         *	and using decimal numbers. Altitude or elevation MAY be
         *	included as an optional third element."
         *
         *	Structure:
         *	"coordinates": [
         *		[ // list of coordinate values
         *			Longitude,	index 0
         *			Latitude,
         *			Elevation
         *		],
         *		[ // another list of coordinate values
         *			Longitude,
         *			Latitude,
         *			Elevation
         *		],
         *		...
         *		[
         *			Longitude,
         *			Latitude,
         *			Elevation
         *		]
         *	]
         *
         *	Doing coordinateGroup.value() will return [ Latitude, Longitude, Elevation ]
         *	To get the coordinate value at an index, say 0, do coordinateGroup.value().at(0).get<double>() to return
         *that value
         */

        // std::cout << "Values in coordinate group: " << coordinateGroup.value().size() << std::endl;

        double altitude = 0.0;

        // std::cout << "Coordinate from JSON: " << std::endl;
        // std::cout << "\tLatitude: " << std::to_string(coordinateGroup.value().at(1).get<double>()) << std::endl;
        // std::cout << "\tLongitude: " << std::to_string(coordinateGroup.value().at(0).get<double>()) << std::endl;
        if (coordinateGroup.value().size() > 2)
        {
            altitude = coordinateGroup.value().at(2).get<double>();
            // std::cout << "\tElevation: " << std::to_string(coordinateGroup.value().at(2).get<double>()) << std::endl;
        }

        Coordinate coordinate(
            coordinateGroup.value().at(0).get<double>(), coordinateGroup.value().at(1).get<double>(), altitude);
        // std::cout << "Coordinate saved: " << std::endl;
        // std::cout << "\tLatitude: " << std::to_string(coordinate.latitude) << std::endl;
        // std::cout << "\tLongitude: " << std::to_string(coordinate.longitude) << std::endl;
        // std::cout << "\tElevation: " << std::to_string(coordinate.altitude) << std::endl;
        feature_object->coordinates.push_back(coordinate);
    }
}

// Parse and store JSON data as features
void ExtractFeatures(json& j_complete)
{
    int featureCount = 0;
    if (j_complete.contains("features"))
    {
        auto& json_features_list = j_complete["features"];
        for (auto& json_feature : json_features_list)
        {
            // std::cout << typeid(json_feature).name() << std::endl;
            if (json_feature.contains("geometry"))
                if (json_feature["geometry"].contains("type"))
                    if (json_feature["geometry"]["type"] == "Point" || json_feature["geometry"]["type"] == "MultiPoint" ||
                        json_feature["geometry"]["type"] == "LineString" ||
                        json_feature["geometry"]["type"] == "MultiLineString" ||
                        json_feature["geometry"]["type"] == "Polygon" ||
                        json_feature["geometry"]["type"] == "MultiPolygon")
                    {

                        Feature* feature_object = new Feature();
                        featureCount++;
                        // read feature, geometry, type object key
                        feature_object->geometryType = json_feature["geometry"]["type"].get<std::string>();
                        // std::cout << "Feature, Geometry, Type: " << feature_object->geometryType << std::endl;
                        // if (feature_object->geometryType == "MultiPolygon")
                        //     std::cout << "Feature, Geometry, Type: " << feature_object->geometryType << std::endl;

                        std::string geometryTypePropertyName = "geojson_geometry_type";

                        cleanNameForUSD(geometryTypePropertyName);

                        // std::cout << "\tname with prefix="  << geometryTypePropertyName << std::endl;

                        std::pair<std::string, std::string> stringProperty =
                            std::make_pair(geometryTypePropertyName, feature_object->geometryType);
                        feature_object->stringProperties.insert(stringProperty);

                        // read feature, properties elements
                        // read feature, properties, object id element
                        if (json_feature["properties"].contains("object_id"))
                        {
                            feature_object->object_id = json_feature["properties"]["object_id"].get<std::string>();
                            // std::cout << "Feature, Properties, Object ID: " << feature_object->object_id <<
                            // std::endl;
                        }
                        // read feature, properties, id element
                        else if (json_feature["properties"].contains("id"))
                        {
                            feature_object->object_id = json_feature["properties"]["id"].get<std::string>();
                            // std::cout << "Feature, Properties, Object ID: " << feature_object->object_id <<
                            // std::endl;
                        }
                        // read feature, properties, id element
                        else if (json_feature["properties"].contains("title"))
                        {
                            feature_object->object_id = json_feature["properties"]["title"].get<std::string>();
                            // std::cout << "Feature, Properties, Object ID: " << feature_object->object_id <<
                            // std::endl;
                        }
                        else
                        {
                            feature_object->object_id = std::to_string(featureCount);
                        }

                        // read feature, properties, type element
                        if (json_feature["properties"].contains("type"))
                        {
                            feature_object->propertyType = json_feature["properties"]["type"].get<std::string>();
                            // std::cout << "Feature, Properties, Type: " << feature_object->propertyType << std::endl;
                        }

                        // read feature, properties, Pair_ID element
                        if (json_feature["properties"].contains("Pair_ID"))
                        {
                            feature_object->pairID = json_feature["properties"]["Pair_ID"].get<std::string>();
                            // std::cout << "Feature, Properties, Pair ID: " << feature_object->pairID << std::endl;
                        }

                        // read feature, properties, height element
                        if (json_feature["properties"].contains("height"))
                        {
                            feature_object->height = json_feature["properties"]["height"];
                            // std::cout << "Feature, Properties, height: " << feature_object->height << std::endl;
                        }

                        // read feature, properties, material element
                        if (json_feature["properties"].contains("material"))
                        {
                            feature_object->material = json_feature["properties"]["material"].get<std::string>();
                            // std::cout << "Feature, Properties, Material: " << feature_object->material << std::endl;
                        }

                        // read feature, properties, coordinates element(s)
                        if (json_feature["geometry"].contains("coordinates"))
                        {
                            // read feature, geometry, coordinate elements
                            // std::cout << "Feature, Geometry, Coordinates" << std::endl;
                            nlohmann::json json_coordinates_list;
                            if (feature_object->geometryType == "Point")
                            {
                                // std::cout << "Reading a Point feature." << std::endl;
                                json_coordinates_list = json_feature["geometry"]["coordinates"];
                                // TODO: update ReadCoordinatesList to reflect a Point's coordinate array
                                //       as it is an array and not a list of arrays
                                // ReadCoordinatesList(feature_object, json_coordinates_list);

                                double altitude = 0.0;

                                if (json_feature["geometry"]["coordinates"].size() > 2)
                                {
                                    altitude = json_feature["geometry"]["coordinates"].at(2).get<double>();
                                }

                                Coordinate coordinate(json_feature["geometry"]["coordinates"].at(0).get<double>(),
                                                      json_feature["geometry"]["coordinates"].at(1).get<double>(),
                                                      altitude);
                                feature_object->coordinates.push_back(coordinate);
                            }
                            else if (feature_object->geometryType == "MultiPoint")
                            { // TODO: have MultiPolygon class have list of Polygons
                                std::cout << "Reading a MultiPoint feature." << std::endl;
                                auto& pointList = json_feature["geometry"]["coordinates"];
                                int pointCount = pointList.size();
                                std::cout << "pointCount: " << pointCount << std::endl;
                                for (int i = 0; i < pointCount; i++)
                                {
                                    Feature* pointInMultiPoint = new Feature();
                                    // Polygon* polygonInMultiPolygon = new Polygon();
                                    nlohmann::json pointCoordinatesList = pointList.at(i);
                                    ReadCoordinatesList(pointInMultiPoint, pointCoordinatesList);
                                    // read feature, geometry, type object key
                                    pointInMultiPoint->geometryType = "Point";
                                    // std::cout << "Feature, Geometry, Type: " << feature_object->geometryType <<
                                    // std::endl;

                                    // read feature, properties elements
                                    // read feature, properties, object id element
                                    pointInMultiPoint->object_id =
                                        feature_object->object_id + "_child_" + std::to_string(i);
                                    // std::cout << "Feature, Properties, Object ID: " << feature_object->object_id <<
                                    // std::endl;

                                    // read feature, properties, type element
                                    pointInMultiPoint->propertyType = feature_object->propertyType;
                                    // std::cout << "Feature, Properties, Type: " << feature_object->propertyType <<
                                    // std::endl;

                                    // TODO: do a check on geometry type, height only applies to polygons and multi
                                    // polygons read feature, properties, height element
                                    // feature->height = featureElement["properties"]["height"];
                                    // read feature, properties, material element
                                    pointInMultiPoint->material = feature_object->material;

                                    // std::cout << "Feature, Properties, Material: " << feature_object->material <<
                                    // std::endl; MultiPolygon* multiPolygon =
                                    // dynamic_cast<MultiPolygon*>(feature_object);
                                    // multiPolygon->polygonLists.push_back(polygonInMultiPolygon);
                                    if (pointInMultiPoint->coordinates.size() > 0)
                                        features.push_back(pointInMultiPoint);
                                }
                            }
                            else if (feature_object->geometryType == "LineString")
                            {
                                // std::cout << "Point, Properties, Object ID: " << feature_object->object_id <<
                                // std::endl;
                                json_coordinates_list = json_feature["geometry"]["coordinates"];
                                std::cout.precision(17);
                                // std::cout << "First coordinate from JSON: " << std::endl;
                                // std::cout << "\tLatitude: " << std::fixed <<
                                // (json_coordinates_list.begin().value().at(1).get<double>()) << std::endl; std::cout
                                // << "\tLongitude: " << std::fixed <<
                                // (json_coordinates_list.begin().value().at(0).get<double>()) << std::endl; std::cout
                                // << "\tElevation: " << std::fixed <<
                                // (json_coordinates_list.begin().value().at(2).get<double>()) << std::endl;
                                ReadCoordinatesList(feature_object, json_coordinates_list);
                            }
                            else if (feature_object->geometryType == "MultiLineString")
                            { // TODO: have MultiPolygon class have list of Polygons
                                auto& lineStringList = json_feature["geometry"]["coordinates"];
                                int lineStringCount = lineStringList.size();
                                // std::cout << "polygonCount: " << polygonCount << std::endl;
                                for (int i = 0; i < lineStringCount; i++)
                                {
                                    Feature* lineStringInMultiLineString = new Feature();
                                    // Polygon* polygonInMultiPolygon = new Polygon();
                                    nlohmann::json lineStringCoordinatesList = lineStringList.at(i);
                                    // std::cout << "First coordinate from JSON: " << std::endl;
                                    // std::cout << "\tLatitude: " <<
                                    // std::to_string(json_coordinates_list.begin().value().at(1).get<double>()) <<
                                    // std::endl; std::cout << "\tLongitude: " <<
                                    // std::to_string(json_coordinates_list.begin().value().at(0).get<double>()) <<
                                    // std::endl; std::cout << "\tElevation: " <<
                                    // std::to_string(json_coordinates_list.begin().value().at(2).get<double>()) <<
                                    // std::endl;
                                    ReadCoordinatesList(lineStringInMultiLineString, lineStringCoordinatesList);
                                    // read feature, geometry, type object key
                                    lineStringInMultiLineString->geometryType = "LineString";
                                    // std::cout << "Feature, Geometry, Type: " << feature_object->geometryType <<
                                    // std::endl;

                                    // read feature, properties elements
                                    // read feature, properties, object id element
                                    lineStringInMultiLineString->object_id =
                                        feature_object->object_id + "_child_" + std::to_string(i);
                                    std::cout << "MultiPoint, Properties, Object ID: " << feature_object->object_id
                                              << std::endl;

                                    // read feature, properties, type element
                                    lineStringInMultiLineString->propertyType = feature_object->propertyType;
                                    // std::cout << "Feature, Properties, Type: " << feature_object->propertyType <<
                                    // std::endl;

                                    // TODO: do a check on geometry type, height only applies to polygons and multi
                                    // polygons read feature, properties, height element
                                    // feature->height = featureElement["properties"]["height"];
                                    // read feature, properties, material element
                                    lineStringInMultiLineString->material = feature_object->material;

                                    // std::cout << "Feature, Properties, Material: " << feature_object->material <<
                                    // std::endl; MultiPolygon* multiPolygon =
                                    // dynamic_cast<MultiPolygon*>(feature_object);
                                    // multiPolygon->polygonLists.push_back(polygonInMultiPolygon);
                                    if (lineStringInMultiLineString->coordinates.size() > 1)
                                        features.push_back(lineStringInMultiLineString);
                                }
                            }
                            else if (feature_object->geometryType == "Polygon")
                            {
                                json_coordinates_list = json_feature["geometry"]["coordinates"].at(0);
                                ReadCoordinatesList(feature_object, json_coordinates_list);
                            }
                            // else if (feature_object->geometryType == "Polygon"){ // TODO: have Polygon class have
                            // list of coordinates lists
                            //     for (int i = 0; i < json_feature["geometry"]["coordinates"].size(); i++){
                            //         nlohmann::json_coordinates_list = json_feature["geometry"]["coordinates"].at(i);
                            //     }
                            // }
                            else if (feature_object->geometryType == "MultiPolygon")
                            { // TODO: have MultiPolygon class have list of Polygons
                                auto& polygonList = json_feature["geometry"]["coordinates"];
                                int polygonCount = polygonList.size();
                                // std::cout << "polygonCount: " << polygonCount << std::endl;
                                for (int i = 0; i < polygonCount; i++)
                                {
                                    Feature* polygonInMultiPolygon = new Feature();
                                    // Polygon* polygonInMultiPolygon = new Polygon();
                                    nlohmann::json polygonCoordinatesList = polygonList.at(i).at(0);
                                    ReadCoordinatesList(polygonInMultiPolygon, polygonCoordinatesList);
                                    // read feature, geometry, type object key
                                    polygonInMultiPolygon->geometryType = "Polygon";
                                    // std::cout << "Feature, Geometry, Type: " << feature_object->geometryType <<
                                    // std::endl;

                                    // read feature, properties elements
                                    // read feature, properties, object id element
                                    polygonInMultiPolygon->object_id =
                                        feature_object->object_id + "_child_" + std::to_string(i);
                                    // std::cout << "Feature, Properties, Object ID: " << feature_object->object_id <<
                                    // std::endl;

                                    // read feature, properties, type element
                                    polygonInMultiPolygon->propertyType = feature_object->propertyType;
                                    // std::cout << "Feature, Properties, Type: " << feature_object->propertyType <<
                                    // std::endl;

                                    // TODO: do a check on geometry type, height only applies to polygons and multi
                                    // polygons read feature, properties, height element
                                    // feature->height = featureElement["properties"]["height"];
                                    // read feature, properties, material element
                                    polygonInMultiPolygon->material = feature_object->material;

                                    // std::cout << "Feature, Properties, Material: " << feature_object->material <<
                                    // std::endl; MultiPolygon* multiPolygon =
                                    // dynamic_cast<MultiPolygon*>(feature_object);
                                    // multiPolygon->polygonLists.push_back(polygonInMultiPolygon);
                                    if (polygonInMultiPolygon->coordinates.size() > 2)
                                        features.push_back(polygonInMultiPolygon);
                                }
                            }

                            std::string name = "geojson:coordinates";

                            cleanNameForUSD(name);

                            // std::cout << "\tname with prefix="  << name << std::endl;

                            PXR_NS::VtArray<PXR_NS::GfVec3d> coordinatesArray;
                            for (auto coordinate : feature_object->coordinates)
                            {
                                // TODO: change for z-up
                                coordinatesArray.push_back(
                                    PXR_NS::GfVec3d(coordinate.longitude, coordinate.altitude, coordinate.latitude));
                            }

                            // Note: while the Points attribute of classes inheriting from UsdGeomPointBased (e.g.,
                            // UsdGeomMesh)
                            //      will store coordinates as an array of GfVec3f it is best to retain precision using
                            //      an array of GfVec3d
                            std::pair<std::string, PXR_NS::VtArray<PXR_NS::GfVec3d>> coordinatesProperty =
                                std::make_pair(name, coordinatesArray);
                            feature_object->GfVec3dArrayProperties.insert(coordinatesProperty);
                        }

                        // if (feature_object->coordinates.size() > 4){
                        //     std::cout << "polygon_" << featureCount << " is an N-gon with more than 4 vertices" <<
                        //     std::endl;
                        // }

                        nlohmann::json properties = json_feature["properties"];

                        // for each property
                        // std::cout << "properties's size()=" << properties.size() << std::endl;

                        for (auto featureProperty = properties.begin(); featureProperty != properties.end();
                             ++featureProperty)
                        {
                            std::string name = featureProperty.key();

                            // std::cout << "Property:" << std::endl << "\tname="  << name << std::endl;

                            cleanNameForUSD(name);

                            // if the property name does *not* start with "omni:kit:converter:geojson:"
                            if (!(name.rfind("omni:kit:converter:geojson:", 0) == 0))
                            {
                                // prepend the prefix
                                name = "omni:kit:converter:geojson:" + name;
                            }

                            // std::cout << "\tname with prefix="  << name << std::endl;

                            auto value = featureProperty.value();

                            // std::cout << "\tvalue=" << value << std::endl;

                            if (value.is_boolean())
                            {
                                std::pair<std::string, bool> boolProperty = std::make_pair(name, value.get<bool>());
                                feature_object->boolProperties.insert(boolProperty);
                                // break;
                            }
                            // else if (value.is_number_integer()){
                            //     std::pair<std::string, int> intProperty = std::make_pair(name, value.get<int>());
                            //     feature_object->intProperties.insert(intProperty);
                            //     break;
                            // }
                            // else if (value.is_number_float()){
                            else if (value.is_number())
                            {
                                std::pair<std::string, double> doubleProperty = std::make_pair(name, value.get<double>());
                                feature_object->doubleProperties.insert(doubleProperty);
                                // break;
                            }
                            else if (value.is_string())
                            {
                                std::pair<std::string, std::string> stringProperty =
                                    std::make_pair(name, value.get<std::string>());
                                feature_object->stringProperties.insert(stringProperty);
                                // break;
                            }
                            // else{
                            //     std::cout << "\ttype=" << value.type() << std::endl;
                            // }

                            // switch(value.type()){
                            //     // // null
                            //     // case value_t::null: {

                            //     // }
                            //     // boolean
                            //     case value_t::boolean: {
                            //         std::pair<std::string, bool> boolProperty = std::make_pair(name,
                            //         value.get<bool>()); feature_object->boolProperties.insert(boolProperty); break;
                            //     }
                            //     // string
                            //     case value_t::string: {
                            //         std::pair<std::string, std::string> stringProperty = std::make_pair(name,
                            //         value.get<std::string>());
                            //         feature_object->stringProperties.insert(stringProperty);
                            //         break;
                            //     }
                            //     // number (integer)
                            //     case value_t::number_integer: {
                            //         std::pair<std::string, int> intProperty = std::make_pair(name, value.get<int>());
                            //         feature_object->intProperties.insert(intProperty);
                            //         break;
                            //     }
                            //     // // number (unsigned integer)
                            //     // case value_t::number_unsigned: {

                            //     // }
                            //     //  number (single floating-point)
                            //     case value_t::number_float: {
                            //         std::pair<std::string, double> doubleProperty = std::make_pair(name,
                            //         value.get<double>()); feature_object->doubleProperties.insert(doubleProperty);
                            //         break;
                            //     }
                            //     // number (double floating-point)
                            //     // TODO: Verify this is a JSON type!
                            //     case double: {
                            //         std::pair<std::string, double> doubleProperty(name, value.get<double>());
                            //         feature_object->doubleProperties.insert(doubleProperty);
                            //         break;
                            //     }
                            //     // // (JSON) object
                            //     // case value_t::object: {

                            //     // }
                            //     // // array
                            //     // case value_t::array: {

                            //     // }
                            //     // // binary
                            //     // case value_t::binary: {

                            //     // }
                            //     // // discarded
                            //     // case value_t::discarded: {

                            //     // }

                            // }

                            // std::cout << "end for-loop for properties"  << std::endl;
                        }

                        if (feature_object->geometryType == "Point" && feature_object->coordinates.size() > 0)
                            features.push_back(feature_object);
                        else if (feature_object->geometryType == "LineString" && feature_object->coordinates.size() > 1)
                            features.push_back(feature_object);
                        else if (feature_object->geometryType == "Polygon" && feature_object->coordinates.size() > 2)
                            features.push_back(feature_object);
                    }
        }
    }

    // std::cout << "completed parsing GeoJSON features"  << std::endl;

    // Testing, ignore
    // Concave, flat
    // Feature* feature1 = new Feature();
    // Coordinate coordinate1(1.0, 0.0, 0.0);
    // feature1->coordinates.push_back(coordinate1);
    // Coordinate coordinate2(1.0, 1.0, 0.0);
    // feature1->coordinates.push_back(coordinate2);
    // Coordinate coordinate3(0.5, 1.5, 0.0);
    // feature1->coordinates.push_back(coordinate3);
    // Coordinate coordinate4(0.0, 1.0, 0.0);
    // feature1->coordinates.push_back(coordinate4);
    // Coordinate coordinate5(0.0, 0.0, 0.0);
    // feature1->coordinates.push_back(coordinate5);
    // Coordinate coordinate6(1.0, 0.0, 0.0);
    // feature1->coordinates.push_back(coordinate6);
    // feature1->geometryType = "Polygon";
    // feature1->object_id = "1";
    // feature1->propertyType = "1";
    // feature1->material = "1";
    // features.push_back(feature1);

    // Not flat
    // Feature* feature2 = new Feature();
    // Coordinate coordinate21(0.0, 0.0, 0.0);
    // feature2->coordinates.push_back(coordinate21);
    // Coordinate coordinate22(1.0, 0.0, 0.0);
    // feature2->coordinates.push_back(coordinate22);
    // Coordinate coordinate23(1.0, 0.0, 1.0);
    // feature2->coordinates.push_back(coordinate23);
    // Coordinate coordinate24(1.0, 1.0, 1.0);
    // feature2->coordinates.push_back(coordinate24);
    // Coordinate coordinate25(0.0, 1.0, 1.0);
    // feature2->coordinates.push_back(coordinate25);
    // Coordinate coordinate26(0.0, 0.0, 1.0);
    // feature2->coordinates.push_back(coordinate26);
    // Coordinate coordinate27(0.0, 0.0, 0.0);
    // feature2->coordinates.push_back(coordinate27);
    // feature2->geometryType = "Polygon";
    // feature2->object_id = "2";
    // feature2->propertyType = "2";
    // feature2->material = "2";
    // features.push_back(feature2);

    // Convex, flat
    // Feature* feature3 = new Feature();
    // Coordinate coordinate31(1.0, 0.0, 0.0);
    // feature3->coordinates.push_back(coordinate31);
    // Coordinate coordinate32(1.0, 1.0, 0.0);
    // feature3->coordinates.push_back(coordinate32);
    // Coordinate coordinate33(0.5, 0.5, 0.0);
    // feature3->coordinates.push_back(coordinate33);
    // Coordinate coordinate34(0.0, 1.0, 0.0);
    // feature3->coordinates.push_back(coordinate34);
    // Coordinate coordinate35(0.0, 0.0, 0.0);
    // feature3->coordinates.push_back(coordinate35);
    // Coordinate coordinate36(1.0, 0.0, 0.0);
    // feature3->coordinates.push_back(coordinate36);
    // feature3->geometryType = "Polygon";
    // feature3->object_id = "3";
    // feature3->propertyType = "3";
    // feature3->material = "3";
    // features.push_back(feature3);
}

// Parse GeoJSON file
void ParseGeoJSON(std::string path)
{
    std::ifstream file(path.c_str());
    json parsedJsonFile = json::parse(file);

    // TODO: check if response contains features

    // Complete URL
    // std::cout << "path is: " << path << std::endl;
    ExtractFeatures(parsedJsonFile);
}

// "main" function of plugin
int Convert_GeoJSON_Source(const char* stage_url, const char* folder_name, bool recursive)
{

    /*
     *  Check inputs
     *  if pass, return 0
     *  else, return -1
     */

    // TODO: add check and tests (if conditions for Windows and Linux) for permission to write images to the defined
    // directory
    if (PXR_NS::UsdStage::IsSupportedFile(stage_url))
    {
        stage = PXR_NS::UsdStage::Open(stage_url);
        auto prim = stage->GetDefaultPrim();
        if (prim.IsValid())
        {
            const fs::path root{ folder_name };
            if (fs::exists(root) && fs::is_directory(root))
            {
                // std::cout << "Meters per unit: " << std::setprecision(5) << UsdGeomGetStageMetersPerUnit(stage) <<
                // std::endl; //default Meters per unit: 0.01

                Timer app_timer;

                // update stage properties
                PXR_NS::UsdGeomSetStageUpAxis(stage, PXR_NS::UsdGeomTokens->y);

                std::string path = folder_name;
                if (recursive)
                {

                    for (const auto& entry : fs::recursive_directory_iterator(path))
                    {
                        // std::cout << "Passed file path: " << entry.path().string() << std::endl;
                        // check whether:
                        //  user has read permissions on entry path
                        //  entry is a regular file
                        //  file has the .geojson file extension
                        if (((fs::status(entry.path().string()).permissions() & fs::perms::owner_read) != fs::perms::none) &&
                            (fs::is_regular_file(entry)) && (entry.path().extension().string() == ".geojson"))
                        {
                            // std::cout << "Passed file path: " << entry.path().string() << std::endl;
                            ParseGeoJSON(entry.path().string());
                        }
                    }
                }
                else
                {
                    for (const auto& entry : fs::directory_iterator(path))
                    {
                        std::cout << "Passed file path: " << entry.path().string() << std::endl;
                        // check whether:
                        //  user has read permissions on entry path
                        //  entry is a regular file
                        //  file has the .geojson file extension
                        if (((fs::status(entry.path().string()).permissions() & fs::perms::owner_read) != fs::perms::none) &&
                            (fs::is_regular_file(entry)) && (entry.path().extension().string() == ".geojson"))
                        {
                            ParseGeoJSON(entry.path().string());
                        }
                    }
                }

                // path = "./1kmE4334N3375.geojson";
                // ParseGeoJSON(path);

                // path = "./Rail_Track_Line_3_Projected_Sel_PairID.geojson";
                // ParseGeoJSON(path);

                std::cout << "Generating geometry..." << std::endl;

                if (features.size() > 0)
                {
                    // CreateCenterRail();
                    // TODO: folder name or single file name when we switch to File Picker?
                    const fs::path root{ folder_name };
                    std::string folderName = root.filename().string();
                    cleanNameForUSD(folderName);

                    // Create a top prim for this file conversion
                    PXR_NS::SdfPath fileXFormPath = prim.GetPath()
                                                        .AppendChild(PXR_NS::TfToken("Geospatial"))
                                                        .AppendChild(PXR_NS::TfToken("GeoJSON"))
                                                        .AppendChild(PXR_NS::TfToken(folderName))
                                                        .AppendChild(PXR_NS::TfToken("Features"));
                    PXR_NS::UsdPrim filePrim = stage->GetPrimAtPath(fileXFormPath);
                    if (!filePrim)
                    {
                        UsdGeomXform xForm = UsdGeomXform::Define(stage, fileXFormPath);
                        try
                        {
                            xForm.AddTranslateOp(PXR_NS::UsdGeomXformOp::PrecisionDouble).Set(PXR_NS::GfVec3d(0.0));
                            xForm.AddRotateXYZOp(PXR_NS::UsdGeomXformOp::PrecisionDouble).Set(PXR_NS::GfVec3d(0.0));
                            xForm.AddScaleOp(PXR_NS::UsdGeomXformOp::PrecisionDouble).Set(PXR_NS::GfVec3d(1.0));
                        }
                        catch (...)
                        {
                            std::cout << "Prim already has xFormOps" << std::endl;
                        }
                        filePrim = xForm.GetPrim();
                    }

                    // CreateCenterRail();
                    for (int i = 0; i < features.size(); i++)
                    {
                        if (i == 0)
                        {
                            firstCoordinate =
                                Coordinate(features[i]->coordinates[0].longitude, features[i]->coordinates[0].latitude,
                                           features[i]->coordinates[0].altitude);
                            GfVec3d firstCoordinateConverted = GfVec3d(
                                static_cast<double>(-1.0 * 1000.0 *
                                                    (getDistanceFromLatLonInKm(
                                                        0.0, 0.0, 0.0, features[i]->coordinates[0].longitude))), // lat(deg)
                                                                                                                 // ->
                                                                                                                 // km
                                static_cast<double>(features[i]->coordinates[0].altitude), // y-axis
                                static_cast<double>(
                                    1000.0 * (getDistanceFromLatLonInKm(
                                                 0.0, 0.0, 0.0, features[i]->coordinates[0].longitude))) // long(deg)
                                                                                                         // -> km
                            );
                            xformUtils::setLocalTransformSRT(/* USD Prim */ filePrim,
                                                             /* translation */ firstCoordinateConverted,
                                                             /* rotation */ GfVec3d(0.0),
                                                             /* gDefaultRotationOrder */ gDefaultRotationOrder,
                                                             /* gDefaultScale */ gDefaultScale);
                            PXR_NS::UsdAttribute attrFirstCoor =
                                filePrim.CreateAttribute(PXR_NS::TfToken("omni:kit:converter:geojson:first_coordinate"),
                                                         PXR_NS::SdfValueTypeNames->Vector3d, true);
                            attrFirstCoor.Set(firstCoordinateConverted);
                        }
                        // for (int j = 0; j < features[i]->coordinates.size(); j++){
                        //     //PXR_NS::UsdGeomMesh mesh = CreateRailways(features[i]->coordinates[j], rootPrimPath, i,
                        //     j);

                        // }
                        // if (features[i]->propertyType == "Rail_Center")
                        //     PXR_NS::UsdGeomBasisCurves mesh = CreateRailways(features[i], rootPrimPath, i);
                        // if (features[i]->propertyType == "Rail_Left" || features[i]->propertyType == "Rail_Right" ||
                        // features[i]->geometryType == "Polygon") CreateRailways(features[i], prim.GetPath(), i);
                        if (features[i]->coordinates.size() > 0)
                            // CreateRailways(features[i], prim.GetPath(), features[i]->object_id);
                            CreateRailways(features[i], filePrim.GetPath(), features[i]->object_id);
                    }
                    // PXR_NS::UsdGeomSetStageUpAxis(stage, PXR_NS::UsdGeomTokens->y);
                    stage->Save();
                }

                features.clear();

                app_timer.stop();
                std::cout << "Application Done [" << app_timer.get_elapsed_s() << "s]\n";
                return 0; // to change
            }
            else
            {
                return -3;
            }
        }
        return -2;
    }
    else
    {
        return -1;
    }
}


// int other_QueryAndGenerate(double const center_lat, double const center_long, double const height, double const
// width)
//{
//    return 12345;
//}

// PXR_NAMESPACE_CLOSE_SCOPE
