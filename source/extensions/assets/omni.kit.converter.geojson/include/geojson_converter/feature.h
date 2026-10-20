// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
#include <map>
#include <string>
#include <unordered_map>
#include <vector>

class Coordinate
{
public:
    Coordinate(double lo, double la, double el)
    {
        longitude = lo;
        latitude = la;
        altitude = el;
        roll = 0.0;
    }
    double latitude;
    double longitude;
    double altitude;
    double roll;

private:
};

class Feature
{
public:
    // geometry
    std::string geometryType;
    std::vector<Coordinate> coordinates;

    // properties
    // std::map<std::string, std::string> properties;
    std::string object_id;
    std::string propertyType;
    std::string material;
    std::string pairID;
    double height;

    // crs
    std::string crs; // e.g. "EPSG:4326"

    // property vectors
    // property name, property value
    std::unordered_map<std::string, bool> boolProperties;
    std::unordered_map<std::string, double> doubleProperties;
    std::unordered_map<std::string, int> intProperties;
    std::unordered_map<std::string, std::string> stringProperties;

    std::unordered_map<std::string, PXR_NS::VtArray<PXR_NS::GfVec3d>> GfVec3dArrayProperties;


private:
};

class LineString : public Feature
{
public:
private:
};

class Polygon : public Feature
{
public:
    double height;
    std::vector<std::vector<Coordinate>> coordinatesLists;

private:
};

class MultiPolygon : public Feature
{
public:
    // std::vector<Polygon*> polygonLists;
private:
};
