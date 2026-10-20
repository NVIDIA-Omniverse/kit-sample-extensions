// SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
#pragma once

#include <carb/Defines.h>
#include <carb/Types.h>

#include <gsl/span>
#include <omni/ext/IExt.h>
#include <omni/kit/SettingsUtils.h>

#include <algorithm>
#include <numeric>
#include <type_traits>


// TODO: other interface definitions that use pxr in their public API do not appear to include the pxr headers, instead
//  depending on the client to include them prior to this header. is that right?
#include <omni/geometry/Curves.h>
#include <omni/graph/core/iComputeGraph.h>
#include <omni/graph/core/tuple.h>
#include <omni/math/linalg/SafeCast.h>
#include <omni/math/linalg/vec.h>

// clang-format off
#include "UsdPCH.h"
// clang-format on

namespace omni
{
namespace renderer
{

constexpr const char* const kSettingsPointWidth = PERSISTENT_SETTINGS_PREFIX "/exts/omni.scene.visualization/pointWidth";
constexpr const char* const kSettingsLineWidth = PERSISTENT_SETTINGS_PREFIX "/exts/omni.scene.visualization/lineWidth";
constexpr const char* const kSettingsApplyToDescendants =
    PERSISTENT_SETTINGS_PREFIX "/exts/omni.scene.visualization/applyToDescendants";
constexpr const char* const kSettingsUseSceneVisPrim =
    PERSISTENT_SETTINGS_PREFIX "/exts/omni.scene.visualization/useSceneVisPrim";
constexpr const char* const kSettingsUseWidthsPrimvar =
    PERSISTENT_SETTINGS_PREFIX "/exts/omni.scene.visualization/useWidthsPrimvar";

// this interface allows the immediate drawing (for the current frame only) by giving the caller
// a IDrawingInterface instance. it also allows the caller to record data via the same
// IDrawingInterface, and then draw it at a given transform perpetually until told to stop
class ISceneVisualization
{
public:
    CARB_PLUGIN_INTERFACE("omni::renderer::ISceneVisualization", 0, 1)

    class IDrawingInterface;

    struct IDrawCallback
    {
        virtual void Draw(IDrawingInterface& drawingInterface) const = 0;
    };


    using RecordingHandle = size_t;
    using InstanceHandle = size_t;
    static const RecordingHandle INVALID_RECORDING_HANDLE = 0;
    static const InstanceHandle INVALID_INSTANCE_HANDLE = 0;

    // limitation with immediate drawing (due to IDebugDraw) - all geometry must be in world coordinates
    //  can potentially allow a transform, but with a performance penalty.
    virtual void DrawImmediate(const IDrawCallback& drawCallback) = 0;

    // recorded drawing - record drawing commands, then begin/end drawing with an associated transform
    //  (simply recording a drawing function does not actually put anything on screen)
    virtual RecordingHandle Record(const IDrawCallback& drawCallback, uint32_t uid) = 0;
    virtual void DestroyRecording(RecordingHandle handle) = 0;

    // establish/terminate drawing of a recording given some transform. natively accepts a Float44,
    //  but template version accepts anything with a ToFloat44 overload (other carb types, pxr, etc)
    struct Float44
    {
        carb::Float4 rows[4];
        static const Float44 Identity()
        {
            return { carb::Float4{ 1, 0, 0, 0 }, carb::Float4{ 0, 1, 0, 0 }, carb::Float4{ 0, 0, 1, 0 },
                     carb::Float4{ 0, 0, 0, 1 } };
        }
    };

    template <typename MatrixTypeT>
    void EstablishDrawing(RecordingHandle handle, const MatrixTypeT& matrixIn)
    {
        Float44 matrix = Utils::ToFloat44(matrixIn);
        EstablishDrawing(handle, matrix);
    }
    virtual void EstablishDrawing(RecordingHandle handle, const Float44& matrix) = 0;
    virtual void TerminateDrawing(RecordingHandle handle) = 0;

    /////////////////////////////////////////////////////////////////////
    // common interface for all basic drawing commands - this abstracts "immediate" vs
    //  "retained" or cached modes
    class IDrawingInterface
    {
    public:
        /////////////////////////
        // easy interface - pass some points (pxr/carb/BulkAccessor types supported), and draw them as is.
        //  see Utils below for type conversion overload set, if one is missing

        // for line & point drawing, the function will use the color from the input color array if available.
        //  if colors are not specified, the points/lines are drawn as white. if they are provided but colorCount
        //  is less than pointCount, the last color in the list will be used for any index > colorCount. this
        //  also naturally lets you color a set of lines/points by passing a single color.

        // draw points
        template <typename PosType, typename ColorType>
        void DrawPoints(const PosType* points,
                        size_t pointCount,
                        const ColorType* colors,
                        size_t colorCount,
                        const float* widths,
                        size_t widthCount);

        template <typename PosType, typename ColorType>
        void DrawLineStrip(const PosType* points,
                           size_t pointCount,
                           const ColorType* colors,
                           size_t colorCount,
                           const float* widths,
                           size_t widthCount);

        // this interface is intended for situations where the lines are represented by
        //  positions and directions, which is often the case (normals, etc).
        template <typename PosType, typename DirType, typename ColorType>
        void DrawLines(const PosType* points,
                       size_t pointCount,
                       const DirType* directions,
                       size_t directionCount,
                       const ColorType* colors,
                       size_t colorCount,
                       const float* widths,
                       size_t widthCount);

        template <typename PosType, typename ColorType>
        void DrawIndexedLines(const PosType* points,
                              const uint32_t* indices,
                              size_t indicesCount,
                              const ColorType* colors,
                              size_t colorCount,
                              const float* widths,
                              size_t widthCount);

        /////////////////////////
        // harder interface, but lets you specify how to retrieve components
        //  useful for things like normalizing directions so they arent crazy long/short, or
        //  interpretting directions as colors via normalizing them. above simple interface is
        //  implemented in terms of this
        template <typename PosType, typename ColorType, typename PosConversion, typename ColorConversion>
        void DrawPoints(const PosType* points,
                        size_t pointCount,
                        const PosConversion& posConversion,
                        const ColorType* colors,
                        size_t colorCount,
                        const ColorConversion& colorConversion,
                        const float* widths,
                        size_t widthCount);

        template <typename PosType, typename ColorType, typename PosConversion, typename ColorConversion>
        void DrawLineStrip(const PosType* points,
                           size_t pointCount,
                           const PosConversion& posConversion,
                           const ColorType* colors,
                           size_t colorCount,
                           const ColorConversion& colorConversion,
                           const float* widths,
                           size_t widthCount);

        template <typename PosType, typename ColorType, typename PosConversion, typename ColorConversion>
        void DrawLineLoop(const PosType* points,
                          size_t pointCount,
                          const PosConversion& posConversion,
                          const ColorType* colors,
                          size_t colorCount,
                          const ColorConversion& colorConversion,
                          const float* widths,
                          size_t widthCount);

        template <typename PosType, typename DirType, typename ColorType, typename PosConversion, typename DirConversion, typename ColorConversion>
        void DrawLines(const PosType* points,
                       size_t pointCount,
                       const PosConversion& posConversion,
                       const DirType* directions,
                       size_t directionCount,
                       const DirConversion& dirConversion,
                       const ColorType* colors,
                       size_t colorCount,
                       const ColorConversion& colorConversion,
                       const float* widths,
                       size_t widthCount);

        template <typename PosType, typename ColorType, typename PosConversion, typename ColorConversion>
        void DrawIndexedLines(const PosType* points,
                              const PosConversion& posConversion,
                              const uint32_t* indices,
                              size_t indicesCount,
                              const ColorType* colors,
                              size_t colorCount,
                              const ColorConversion& colorConversion,
                              const float* widths,
                              size_t widthCount);


        struct IPointDataFetcher
        {
            virtual void Fetch(size_t index, carb::Float3& pointOut, carb::ColorRgba& colorOut, float& widthOut) const = 0;
        };

        struct ILineDataFetcher
        {
            virtual void Fetch(size_t index,
                               carb::Float3& pointOut,
                               carb::Float3& directionOut,
                               carb::ColorRgba& colorOut,
                               float& widthOut) const = 0;
        };

        struct ILineStripDataFetcher
        {
            virtual void Fetch(size_t index, carb::Float3& pointOut, carb::ColorRgba& colorOut, float& widthOut) const = 0;
        };

        struct IIndexedLineDataFetcher
        {
            virtual void Fetch(size_t index, carb::Float3& pointOut, carb::ColorRgba& colorOut, float& widthOut) const = 0;
        };

        virtual void DrawPointsImp(size_t pointCount, const IPointDataFetcher& iPointFetcher) = 0;
        virtual void DrawLinesImp(size_t lineCount, const ILineDataFetcher& iLineFetcher) = 0;
        virtual void DrawLineStripImp(size_t lineCount, const ILineStripDataFetcher& iLineFetcher) = 0;
        virtual void DrawIndexedLinesImp(size_t lineCount, const IIndexedLineDataFetcher& iLineFetcher) = 0;
    };


    ///////////////////////////////////////////
    // type conversions
    // these types allow automatic conversion between the various type systems. you can make your own
    //  and pass that in, as long as it has a templated operator() as these do.

    // default interpreters - just convert types, leaving data as is
    struct DefaultVecConversion
    {
        template <typename InputType>
        carb::Float3 operator()(const InputType& data) const
        {
            return Utils::ToFloat3(data);
        }
    };

    struct DefaultColorConversion
    {
        template <typename InputType>
        carb::ColorRgba operator()(const InputType& data) const
        {
            return Utils::ToColorRgba(data);
        }
    };

    // some common operations that manipulate data

    // scale display vector by a factor
    struct ScaledFloat3
    {
        template <typename InputType>
        carb::Float3 operator()(const InputType& data) const
        {
            carb::Float3 float3 = Utils::ToFloat3(data);
            carb::Float3 scaled = { float3.x * rescale, float3.y * rescale, float3.z * rescale };
            return scaled;
        }
        const float rescale = 1;
    };

    // generate a normalized vec3 from an unnormalized vec3
    // scale multipler allowed, since unit vectors may be too small to see
    struct NormalizeFloat3
    {
        template <typename InputType>
        carb::Float3 operator()(const InputType& data) const
        {
            carb::Float3 float3 = Utils::ToFloat3(data);
            float lengthSq = float3.x * float3.x + float3.y * float3.y + float3.z * float3.z, length = sqrt(lengthSq);
            carb::Float3 scaledNormalized = { float3.x / length * rescale, float3.y / length * rescale,
                                              float3.z / length * rescale };
            return scaledNormalized;
        }
        const float rescale = 1;
    };

    // generate a color (vec4) by normalizing an vec3
    struct ColorFromUnnormalized
    {
        template <typename InputType>
        carb::ColorRgba operator()(const InputType& data) const
        {
            carb::Float3 float3 = Utils::ToFloat3(data);
            float lengthSq = float3.x * float3.x + float3.y * float3.y + float3.z * float3.z, length = sqrt(lengthSq);
            carb::ColorRgba normalized = { float3.x / length, float3.y / length, float3.z / length, 1.0f };
            return normalized;
        }
    };

    // overloads for converting the various type systems/types into the underlying Draw*Imp() type protocol
    // (carb::FloatX)
    //  add overloads here for any missing types.
    struct Utils
    {
        // float3 (points/normals)
        static carb::Float3 ToFloat3(const pxr::GfVec3f& data)
        {
            return carb::Float3{ data[0], data[1], data[2] };
        }
        static carb::Float3 ToFloat3(const pxr::GfVec3d& data)
        {
            return carb::Float3{ float(data[0]), float(data[1]), float(data[2]) };
        }
        static carb::Float3 ToFloat3(const carb::Float3& data)
        {
            return data;
        }
        template <typename T>
        static carb::Float3 ToFloat3(const omni::graph::core::tuple<T, 3>& data)
        {
            return carb::Float3{ float(data[0]), float(data[1]), float(data[2]) };
        }
        static carb::Float3 ToFloat3(const omni::math::linalg::vec3f& data)
        {
            return carb::Float3{ data[0], data[1], data[2] };
        }
        static carb::Float3 ToFloat3(const omni::math::linalg::vec3d& data)
        {
            return carb::Float3{ float(data[0]), float(data[1]), float(data[2]) };
        }

        // colors
        static carb::ColorRgba ToColorRgba(const pxr::GfVec3f& data)
        {
            return carb::ColorRgba{ data[0], data[1], data[2], 1.0f };
        }
        static carb::ColorRgba ToColorRgba(const pxr::GfVec4f& data)
        {
            return carb::ColorRgba{ data[0], data[1], data[2], data[3] };
        }
        static carb::ColorRgba ToColorRgba(const carb::Float3& data)
        {
            return carb::ColorRgba{ data.x, data.y, data.z, 1.0f };
        }
        static carb::ColorRgba ToColorRgba(const carb::ColorRgba& data)
        {
            return data;
        }
        template <typename T>
        static carb::ColorRgba ToColorRgba(const omni::graph::core::tuple<T, 4>& data)
        {
            return carb::ColorRgba{ float(data[0]), float(data[1]), float(data[2]), float(data[3]) };
        }
        static carb::ColorRgba ToColorRgba(const omni::math::linalg::vec3f& data)
        {
            return carb::ColorRgba{ data[0], data[1], data[2], 1.0f };
        }
        static carb::ColorRgba ToColorRgba(const omni::math::linalg::vec4f& data)
        {
            return carb::ColorRgba{ data[0], data[1], data[2], data[3] };
        }


        static Float44 ToFloat44(const pxr::GfMatrix4d& data)
        {
            pxr::GfMatrix4f matrixf(data);
            return ToFloat44(matrixf);
        }
        static Float44 ToFloat44(const pxr::GfMatrix4f& data)
        {
            float matrix[4][4];
            data.Get(matrix);
            return Float44{ carb::Float4{ matrix[0][0], matrix[0][1], matrix[0][2], matrix[0][3] },
                            carb::Float4{ matrix[1][0], matrix[1][1], matrix[1][2], matrix[1][3] },
                            carb::Float4{ matrix[2][0], matrix[2][1], matrix[2][2], matrix[2][3] },
                            carb::Float4{ matrix[3][0], matrix[3][1], matrix[3][2], matrix[3][3] } };
        }
    };
};


// this interface allows a node to be assoicated with a function that knows how to draw it. this
//  node will be drawn perpetually until instructed to stop. the prim's draw function will be called
//  whenver the underlying node data may have changedd. this drawing will be recorded, allowing
//  cached draws each frame without reevaluating the draw function if the prim has not changed
class IPrimVisualizer
{
public:
    CARB_PLUGIN_INTERFACE("omni::renderer::IPrimVisualizer", 0, 1)

    using RegistrationHandle = size_t;
    static const RegistrationHandle INVALID_REGISTRATION_HANDLE = 0;

    struct IDrawCallback
    {
        virtual void Draw(ISceneVisualization::IDrawingInterface& drawingInterface, PXR_NS::SdfPath primPath) const = 0;
    };


    virtual RegistrationHandle AddPrimDraw(PXR_NS::SdfPath primPath, const IDrawCallback* drawCallback) = 0;
    virtual void ForcePrimDirty(RegistrationHandle handle) = 0; // returns interface provied during AddNodeDraw
    virtual const IDrawCallback* RemovePrimDraw(RegistrationHandle handle) = 0;

    // this is a helper for situations where state cannot be maintained or is cumbersome, such
    //  as within a compute node callback
    virtual RegistrationHandle LookupRegistrationHandle(PXR_NS::SdfPath primPath, const IDrawCallback* drawCallback) = 0;
};


// this interface allows a node to be assoicated with a function that knows how to draw it. this
//  node will be drawn perpetually until instructed to stop. the node's draw function will be called
//  whenver the underlying node data may have changed (currently, every frame).
class INodeVisualizer
{
public:
    CARB_PLUGIN_INTERFACE("omni::renderer::INodeVisualizer", 0, 1)

    using RegistrationHandle = size_t;
    static const RegistrationHandle INVALID_REGISTRATION_HANDLE = 0;

    struct IDrawCallback
    {
        virtual void Draw(ISceneVisualization::IDrawingInterface& drawingInterface,
                          const omni::graph::core::NodeObj& nodeObj) const = 0;
    };

    // associates a node instance to an object capable of drawing it.
    virtual RegistrationHandle AddNodeDraw(const omni::graph::core::NodeObj& nodeObj,
                                           const IDrawCallback* drawCallback) = 0;
    virtual void ForceNodeDirty(RegistrationHandle handle) = 0; // returns interface provied during AddNodeDraw
    virtual const IDrawCallback* RemoveNodeDraw(RegistrationHandle handle) = 0; // returns interface provied during
                                                                                // AddNodeDraw

    // this is a helper for situations where state cannot be maintained or is cumbersome, such
    //  as within a compute node callback
    virtual RegistrationHandle LookupRegistrationHandle(const omni::graph::core::NodeObj& nodeObj,
                                                        const IDrawCallback* drawCallback) = 0;
};

// easy interface for applying point/normal/wireframe visualization to the current selection. toggle fetches the current
// setting
//  of the first item in the selection, and applies that toggle to all others in the selection. can register types
//  (currently nodes only) to "teach" this class how to draw something when it is found in the selection.
class ISceneDeclutter
{
public:
    CARB_PLUGIN_INTERFACE("omni::renderer::ISceneDeclutter", 0, 2)

    virtual void TogglePoints() = 0;
    virtual void ToggleNormals() = 0;
    virtual void ToggleWireframe() = 0;
    virtual void ToggleTangents() = 0;
    virtual void ToggleUseVertexColor() = 0;

    struct Options
    {
        bool drawPoints = false;
        bool drawNormals = false;
        bool drawWireframe = false;
        bool drawTangents = false;
        bool useVertexColor = false;
        bool useWidthsPrimvar = false;
        bool isSelected = false;
        float pointWidth = 1.f;
        float lineWidth = 1.f;
    };

    typedef void (*DrawNodeFuncPtr)(ISceneVisualization::IDrawingInterface& drawingInterface,
                                    const omni::graph::core::NodeObj& nodeObj,
                                    const Options& options);
    virtual void RegisterDrawableNodeType(const omni::graph::core::NodeTypeObj& nodeType, DrawNodeFuncPtr drawFuncPtr) = 0;

    // same for nodes, but prim types instead?
    typedef void (*DrawPrimFuncPtr)(ISceneVisualization::IDrawingInterface& drawingInterface,
                                    pxr::UsdPrim prim,
                                    const Options& options);
    virtual void RegisterDrawablePrimType(const pxr::TfToken& primType, DrawPrimFuncPtr drawFuncPtr) = 0;
};

struct MeshUtils
{
    // type-agnostic function for drawing mesh data, but with some support functions for USD (should add equivalents for
    // Fabric as well)

    static const size_t CURVE_STEPS_PER_SEGMENT = 30;

    enum Interpolation
    {
        CONSTANT, //  1 value per entire prim
        UNIFORM, // 1 value per face
        VERTEX, // 1 value per vertex
        FACEVARYING, // 1 value per face point
        UNKNOWN // error
    };

    // these function objects encapsulate the retrieval of data based on interpolation type, allowing more generalized
    // draw functions
    //  and much faster code by enabling inlining/etc
    template <typename DataTypeT>
    struct DataSourceEmpty_T
    {
        typedef DataTypeT OutputDataType; // required
        OutputDataType operator[](size_t /*unused*/) const // required
        {
            CARB_ASSERT(0 && "Attempting to retrieve data from an empty source");
            return DataTypeT();
        }
    };
    template <typename DataTypeT>
    struct DataSourceConstant_T
    {
        typedef DataTypeT OutputDataType; // required
        OutputDataType operator[](size_t /*unused*/) const // required
        {
            return source;
        }
        const DataTypeT source;
    };
    template <typename DataTypeT>
    struct DataSourcePerVertex_T
    {
        typedef DataTypeT OutputDataType; // required
        OutputDataType operator[](size_t index) const // required
        {
            index = std::min(index, faceVertexIndexCount - 1);
            size_t pointIndex = faceVertexIndices[index];
            pointIndex = std::min(pointIndex, sourceArrayCount - 1);
            return sourceArray[pointIndex];
        }
        const int* faceVertexIndices = nullptr;
        size_t faceVertexIndexCount = 0;
        const DataTypeT* sourceArray = nullptr;
        size_t sourceArrayCount = 0;
    };
    template <typename DataTypeT>
    struct DataSourceFaceVarying_T
    {
        typedef DataTypeT OutputDataType; // required
        OutputDataType operator[](size_t index) const // required
        {
            index = std::min(index, sourceArrayCount - 1);
            return sourceArray[index];
        }
        const DataTypeT* sourceArray = nullptr;
        size_t sourceArrayCount = 0;
    };
    // TODO: constant etc, as needed


    // mesh drawing must consider the interpolation of colors as well as normals. DataSources are chosen incrementally,
    // to offload the generation of permutations
    //  onto the compiler. DrawMeshFromUSD first gathers the attributes and their interpolation modes, then chooses the
    //  color source, then chooses the normal source, and finally draws the mesh.
    // callers can step into this sequence at any point, for example if they have an alternate color source (rgba, vs
    // the kit standard of rg & ba). this is why
    //  color source is chosen first in the sequence, so that callers can skip this and still leverate the normals
    //  source selection
    static void DrawMeshFromUSD(ISceneVisualization::IDrawingInterface& drawingInterface,
                                pxr::UsdPrim prim,
                                const ISceneDeclutter::Options& options);

    template <typename PointTypeT, typename NormalTypeT, typename ColorTypeT, typename OpacityTypeT>
    static void DrawMeshFromUSD_ChooseColorSource(ISceneVisualization::IDrawingInterface& drawingInterface,
                                                  size_t faceCount,
                                                  const int* faceVertexIndices,
                                                  const size_t faceVertexIndexCount,
                                                  const int* faceVertexCounts,
                                                  const size_t faceVertexCountsSize,
                                                  const PointTypeT* points,
                                                  const size_t pointCount,
                                                  const NormalTypeT* normals,
                                                  const size_t normalsCount,
                                                  const Interpolation normalsInterpolation,
                                                  const ColorTypeT* colors,
                                                  const size_t colorCount,
                                                  const Interpolation colorInterpolation,
                                                  const int* colorIndices,
                                                  const size_t colorIndicesCount,
                                                  const OpacityTypeT* opacities,
                                                  const size_t opacityCount,
                                                  const Interpolation opacityInterpolation,
                                                  const int* opacityIndices,
                                                  const size_t opacityIndicesCount,
                                                  const ISceneDeclutter::Options& options);

    template <typename PointTypeT, typename NormalTypeT, typename ColorSourceTypeT>
    static void DrawMeshFromUSD_ChooseNormalSource(ISceneVisualization::IDrawingInterface& drawingInterface,
                                                   size_t faceCount,
                                                   const int* faceVertexIndices,
                                                   size_t faceVertexIndexCount,
                                                   const int* faceVertexCounts,
                                                   size_t faceVertexCountsSize,
                                                   const PointTypeT* points,
                                                   size_t pointCount,
                                                   const NormalTypeT* normals,
                                                   size_t normalsCount,
                                                   Interpolation normalsInterpolation,
                                                   const ColorSourceTypeT& colorsSource,
                                                   const ISceneDeclutter::Options& options);

    template <typename PointTypeT, typename NormalSourceTypeT, typename ColorSourceTypeT>
    static void DrawMesh(ISceneVisualization::IDrawingInterface& drawingInterface,
                         size_t faceCount,
                         const int* faceVertexIndices,
                         size_t faceVertexIndexCount,
                         const int* faceVertexCounts,
                         size_t faceVertexCountsSize,
                         const PointTypeT* points,
                         size_t pointCount,
                         const NormalSourceTypeT& normals,
                         const ColorSourceTypeT& colors,
                         const ISceneDeclutter::Options& options);

    static void DrawBasisCurvesFromUSD(ISceneVisualization::IDrawingInterface& drawingInterface,
                                       pxr::UsdPrim prim,
                                       const ISceneDeclutter::Options& options);

    static Interpolation DecodeInterpolationToken(pxr::TfToken interpolationToken);

    template <typename ValueType>
    static bool GetValueFromAttribute(pxr::UsdPrim prim,
                                      pxr::TfToken attributeName,
                                      ValueType& value,
                                      Interpolation* interpolation = nullptr,
                                      pxr::VtArray<int>* indices = nullptr);
};


///////////////////////////////////////
// ISceneVisualization


template <typename PosType, typename ColorType>
void ISceneVisualization::IDrawingInterface::DrawPoints(const PosType* points,
                                                        size_t pointCount,
                                                        const ColorType* colors,
                                                        size_t colorCount,
                                                        const float* widths,
                                                        size_t widthCount)
{
    // Could templatize over WidthType too but right now it doesn't matter...
    DrawPoints(
        points, pointCount, DefaultVecConversion(), colors, colorCount, DefaultColorConversion(), widths, widthCount);
}


template <typename PosType, typename DirType, typename ColorType>
void ISceneVisualization::IDrawingInterface::DrawLines(const PosType* points,
                                                       size_t pointCount,
                                                       const DirType* directions,
                                                       size_t directionCount,
                                                       const ColorType* colors,
                                                       size_t colorCount,
                                                       const float* widths,
                                                       size_t widthCount)
{
    DrawLines(points, pointCount, DefaultVecConversion(), directions, directionCount, DefaultVecConversion(), colors,
              colorCount, DefaultColorConversion(), widths, widthCount);
}

template <typename PosType, typename ColorType>
void ISceneVisualization::IDrawingInterface::DrawIndexedLines(const PosType* points,
                                                              const uint32_t* indices,
                                                              size_t indicesCount,
                                                              const ColorType* colors,
                                                              size_t colorCount,
                                                              const float* widths,
                                                              size_t widthCount)
{
    DrawIndexedLines(points, DefaultVecConversion(), indices, indicesCount, colors, colorCount,
                     DefaultColorConversion(), widths, widthCount);
}

template <typename PosType, typename ColorType>
void ISceneVisualization::IDrawingInterface::DrawLineStrip(const PosType* points,
                                                           size_t pointCount,
                                                           const ColorType* colors,
                                                           size_t colorCount,
                                                           const float* widths,
                                                           size_t widthCount)
{
    DrawLineStrip(
        points, pointCount, DefaultVecConversion(), colors, colorCount, DefaultColorConversion(), widths, widthCount);
}


template <typename PosType, typename ColorType, typename PosConversion, typename ColorConversion>
void ISceneVisualization::IDrawingInterface::DrawPoints(const PosType* points,
                                                        size_t pointCount,
                                                        const PosConversion& posConversion,
                                                        const ColorType* colors,
                                                        size_t colorCount,
                                                        const ColorConversion& colorConversion,
                                                        const float* widths,
                                                        size_t widthCount)
{
    struct PointDataFetcher : IPointDataFetcher
    {
        // would be cleaner with c++17
        struct Data
        {
            const PosType* const points;
            const ColorType* const colors;
            const size_t colorCount;
            const float* const widths;
            const size_t widthCount;

            const PosConversion& posConversion;
            const ColorConversion& colorConversion;
        };

        PointDataFetcher(const Data& dataIn) : data(dataIn)
        {
        }

        virtual void Fetch(size_t index, carb::Float3& pointOut, carb::ColorRgba& colorOut, float& widthOut) const override
        {
            pointOut = data.posConversion(data.points[index]);

            if (data.colors)
            {
                // if not enough colors, take the last one (also elegantly handles colorCount==1)
                size_t colorIndex = index < data.colorCount ? index : data.colorCount - 1;
                colorOut = data.colorConversion(data.colors[colorIndex]);
            }
            else
            {
                colorOut = carb::ColorRgba{ 1, 1, 1, 1 };
            }

            if (data.widths)
            {
                size_t widthIndex = index < data.widthCount ? index : data.widthCount - 1;
                widthOut = data.widths[widthIndex];
            }
            else
            {
                widthOut = 1.f;
            }
        }

        const Data& data;
    };

    typename PointDataFetcher::Data data = { points,     colors,        colorCount,     widths,
                                             widthCount, posConversion, colorConversion };
    PointDataFetcher fetcher(data);

    DrawPointsImp(pointCount, fetcher);
}


template <typename PosType, typename ColorType, typename PosConversion, typename ColorConversion>
void ISceneVisualization::IDrawingInterface::DrawLineStrip(const PosType* points,
                                                           size_t pointCount,
                                                           const PosConversion& posConversion,
                                                           const ColorType* colors,
                                                           size_t colorCount,
                                                           const ColorConversion& colorConversion,
                                                           const float* widths,
                                                           size_t widthCount)
{
    // TODO: this is identical to PointDataFetcher above
    struct LineDataFetcher : ILineStripDataFetcher
    {
        // would be cleaner with c++17
        struct Data
        {
            const PosType* const points;
            const ColorType* const colors;
            const size_t colorCount;
            const float* const widths;
            const size_t widthCount;

            const PosConversion& posConversion;
            const ColorConversion& colorConversion;
        };

        LineDataFetcher(const Data& dataIn) : data(dataIn)
        {
        }
        virtual void Fetch(size_t index, carb::Float3& pointOut, carb::ColorRgba& colorOut, float& widthOut) const override
        {
            pointOut = data.posConversion(data.points[index]);

            if (data.colors)
            {
                // if not enough colors, take the last one (also elegantly handles colorCount==1)
                size_t colorIndex = index < data.colorCount ? index : data.colorCount - 1;
                colorOut = data.colorConversion(data.colors[colorIndex]);
            }
            else
            {
                colorOut = carb::ColorRgba{ 1, 1, 1, 1 };
            }

            if (data.widths)
            {
                size_t widthIndex = index < data.widthCount ? index : data.widthCount - 1;
                widthOut = data.widths[widthIndex];
            }
            else
            {
                widthOut = 1.f;
            }
        }
        const Data& data;
    };

    typename LineDataFetcher::Data data = { points,     colors,        colorCount,     widths,
                                            widthCount, posConversion, colorConversion };
    LineDataFetcher fetcher(data);

    DrawLineStripImp(pointCount, fetcher);
}


template <typename PosType, typename ColorType, typename PosConversion, typename ColorConversion>
void ISceneVisualization::IDrawingInterface::DrawLineLoop(const PosType* points,
                                                          size_t pointCount,
                                                          const PosConversion& posConversion,
                                                          const ColorType* colors,
                                                          size_t colorCount,
                                                          const ColorConversion& colorConversion,
                                                          const float* widths,
                                                          size_t widthCount)
{
    struct LineDataFetcher : ILineStripDataFetcher
    {
        // would be cleaner with c++17
        struct Data
        {
            const PosType* const points;
            const size_t pointCount;
            const ColorType* const colors;
            const size_t colorCount;
            const float* const widths;
            const size_t widthCount;

            const PosConversion& posConversion;
            const ColorConversion& colorConversion;
        };

        LineDataFetcher(const Data& dataIn) : data(dataIn)
        {
        }
        virtual void Fetch(size_t index, carb::Float3& pointOut, carb::ColorRgba& colorOut, float& widthOut) const override
        {
            size_t wrappedIndex = index % data.pointCount;

            pointOut = data.posConversion(data.points[wrappedIndex]);

            if (data.colors)
            {
                // if not enough colors, take the last one (also elegantly handles colorCount==1)
                size_t colorIndex = wrappedIndex < data.colorCount ? wrappedIndex : data.colorCount - 1;
                colorOut = data.colorConversion(data.colors[colorIndex]);
            }
            else
            {
                colorOut = carb::ColorRgba{ 1, 1, 1, 1 };
            }

            if (data.widths)
            {
                size_t widthIndex = wrappedIndex < data.widthCount ? wrappedIndex : data.widthCount - 1;
                widthOut = data.widths[widthIndex];
            }
            else
            {
                widthOut = 1.f;
            }
        }
        const Data& data;
    };

    typename LineDataFetcher::Data data = { points, pointCount, colors,        colorCount,
                                            widths, widthCount, posConversion, colorConversion };
    LineDataFetcher fetcher(data);

    // add an additional line from end to beginning
    DrawLineStripImp(pointCount + 1, fetcher);
}


template <typename PosType, typename DirType, typename ColorType, typename PosConversion, typename DirConversion, typename ColorConversion>
void ISceneVisualization::IDrawingInterface::DrawLines(const PosType* points,
                                                       size_t pointCount,
                                                       const PosConversion& posConversion,
                                                       const DirType* directions,
                                                       size_t directionCount,
                                                       const DirConversion& dirConversion,
                                                       const ColorType* colors,
                                                       size_t colorCount,
                                                       const ColorConversion& colorConversion,
                                                       const float* widths,
                                                       size_t widthCount)
{
    struct LineDataFetcher : ILineDataFetcher
    {
        // would be cleaner with c++17
        struct Data
        {
            const PosType* const points;
            const DirType* const directions;
            const ColorType* const colors;
            const size_t colorCount;
            const float* const widths;
            const size_t widthCount;

            const PosConversion& posConversion;
            const DirConversion& dirConversion;
            const ColorConversion& colorConversion;
        };

        LineDataFetcher(const Data& dataIn) : data(dataIn)
        {
        }
        virtual void Fetch(size_t index,
                           carb::Float3& pointOut,
                           carb::Float3& directionOut,
                           carb::ColorRgba& colorOut,
                           float& widthOut) const override
        {
            pointOut = data.posConversion(data.points[index]);
            directionOut = data.dirConversion(data.directions[index]);

            if (data.colors)
            {
                // if not enough colors, take the last one (also elegantly handles colorCount==1)
                size_t colorIndex = index < data.colorCount ? index : data.colorCount - 1;
                colorOut = data.colorConversion(data.colors[colorIndex]);
            }
            else
            {
                colorOut = carb::ColorRgba{ 1, 1, 1, 1 };
            }

            if (data.widths)
            {
                size_t widthIndex = index < data.widthCount ? index : data.widthCount - 1;
                widthOut = data.widths[widthIndex];
            }
            else
            {
                widthOut = 1.f;
            }
        }
        const Data& data;
    };

    typename LineDataFetcher::Data data = { points,     directions,    colors,        colorCount,     widths,
                                            widthCount, posConversion, dirConversion, colorConversion };
    LineDataFetcher fetcher(data);

    size_t lineCount = std::min(pointCount, directionCount);
    DrawLinesImp(lineCount, fetcher);
}


template <typename PosType, typename ColorType, typename PosConversion, typename ColorConversion>
void ISceneVisualization::IDrawingInterface::DrawIndexedLines(const PosType* points,
                                                              const PosConversion& posConversion,
                                                              const uint32_t* indices,
                                                              size_t indicesCount,
                                                              const ColorType* colors,
                                                              size_t colorCount,
                                                              const ColorConversion& colorConversion,
                                                              const float* widths,
                                                              size_t widthCount)
{
    struct LineDataFetcher : IIndexedLineDataFetcher
    {
        // would be cleaner with c++17
        struct Data
        {
            const PosType* const points;
            const uint32_t* indices;
            const ColorType* const colors;
            const size_t colorCount;
            const float* const widths;
            const size_t widthCount;

            const PosConversion& posConversion;
            const ColorConversion& colorConversion;
        };

        LineDataFetcher(const Data& dataIn) : data(dataIn)
        {
        }
        virtual void Fetch(size_t index, carb::Float3& pointOut, carb::ColorRgba& colorOut, float& widthOut) const override
        {
            const size_t pIndex = data.indices[index];
            pointOut = data.posConversion(data.points[pIndex]);

            if (data.colors)
            {
                // if not enough colors, take the last one (also elegantly handles colorCount==1)
                size_t colorIndex = pIndex < data.colorCount ? pIndex : data.colorCount - 1;
                colorOut = data.colorConversion(data.colors[colorIndex]);
            }
            else
            {
                colorOut = carb::ColorRgba{ 1, 1, 1, 1 };
            }

            if (data.widths)
            {
                size_t widthIndex = pIndex < data.widthCount ? pIndex : data.widthCount - 1;
                widthOut = data.widths[widthIndex];
            }
            else
            {
                widthOut = 1.f;
            }
        }
        const Data& data;
    };

    typename LineDataFetcher::Data data = { points, indices,    colors,        colorCount,
                                            widths, widthCount, posConversion, colorConversion };
    LineDataFetcher fetcher(data);
    DrawIndexedLinesImp(indicesCount, fetcher);
}


//////////////////////////////////////////
// MeshUtils


inline MeshUtils::Interpolation MeshUtils::DecodeInterpolationToken(pxr::TfToken interpolationToken)
{
    if (interpolationToken == pxr::UsdGeomTokens->constant)
        return CONSTANT;
    else if (interpolationToken == pxr::UsdGeomTokens->uniform)
        return UNIFORM;
    else if (interpolationToken == pxr::UsdGeomTokens->vertex)
        return VERTEX;
    else if (interpolationToken == pxr::UsdGeomTokens->faceVarying)
        return FACEVARYING;
    else
        return UNKNOWN;
}

template <typename ValueType>
inline bool MeshUtils::GetValueFromAttribute(pxr::UsdPrim prim,
                                             pxr::TfToken attributeName,
                                             ValueType& value,
                                             Interpolation* interpolation /* = nullptr*/,
                                             pxr::VtArray<int>* indices /* = nullptr*/)
{
    bool valueFound = false;
    pxr::UsdAttribute attr = prim.GetAttribute(attributeName);
    if (attr)
    {
        valueFound = attr.Get(&value);

        if (interpolation)
        {
            pxr::TfToken interpolationToken;
            attr.GetMetadata(pxr::UsdGeomTokens->interpolation, &interpolationToken);
            *interpolation = DecodeInterpolationToken(interpolationToken);
        }

        if (indices)
        {
            pxr::TfToken indicesToken(attributeName.GetString() + ":indices");
            bool indicesFound = false;
            attr = prim.GetAttribute(indicesToken);
            if (attr)
            {
                indicesFound = attr.Get(indices);
            }
            if (!indicesFound)
            {
                indices->resize(value.size());
                std::iota(indices->begin(), indices->end(), 0);
            }
        }
    }

    return valueFound;
}

inline void MeshUtils::DrawMeshFromUSD(ISceneVisualization::IDrawingInterface& drawingInterface,
                                       pxr::UsdPrim prim,
                                       const ISceneDeclutter::Options& options)
{
    pxr::VtArray<int> faceVertexCounts, faceVertexIndices;
    pxr::VtArray<pxr::GfVec3f> points;
    if (GetValueFromAttribute(prim, pxr::UsdGeomTokens->faceVertexCounts, faceVertexCounts) &&
        GetValueFromAttribute(prim, pxr::UsdGeomTokens->faceVertexIndices, faceVertexIndices) &&
        GetValueFromAttribute(prim, pxr::UsdGeomTokens->points, points))
    {
        pxr::VtArray<pxr::GfVec3f> normals;
        Interpolation normalsInterpolation;
        GetValueFromAttribute(prim, pxr::UsdGeomTokens->normals, normals, &normalsInterpolation);

        Interpolation colorInterpolation, opacityInterpolation;
        pxr::VtArray<pxr::GfVec3f> colors;
        pxr::VtArray<float> opacities;
        pxr::VtArray<int> colorIndices, opacityIndices;
        GetValueFromAttribute(prim, pxr::UsdGeomTokens->primvarsDisplayColor, colors, &colorInterpolation, &colorIndices);
        GetValueFromAttribute(
            prim, pxr::UsdGeomTokens->primvarsDisplayOpacity, opacities, &opacityInterpolation, &opacityIndices);

        DrawMeshFromUSD_ChooseColorSource(drawingInterface, faceVertexCounts.size(), faceVertexIndices.data(),
                                          faceVertexIndices.size(), faceVertexCounts.data(), faceVertexCounts.size(),
                                          points.data(), points.size(), normals.data(), normals.size(),
                                          normalsInterpolation, colors.data(), colors.size(), colorInterpolation,
                                          colorIndices.data(), colorIndices.size(), opacities.data(), opacities.size(),
                                          opacityInterpolation, opacityIndices.data(), opacityIndices.size(), options);
    }
}

template <typename PointTypeT, typename NormalTypeT, typename ColorTypeT, typename OpacityTypeT>
void MeshUtils::DrawMeshFromUSD_ChooseColorSource(ISceneVisualization::IDrawingInterface& drawingInterface,
                                                  size_t faceCount,
                                                  const int* faceVertexIndices,
                                                  const size_t faceVertexIndexCount,
                                                  const int* faceVertexCounts,
                                                  const size_t faceVertexCountsSize,
                                                  const PointTypeT* points,
                                                  const size_t pointCount,
                                                  const NormalTypeT* normals,
                                                  size_t normalsCount,
                                                  const Interpolation normalsInterpolation,
                                                  const ColorTypeT* colors,
                                                  size_t colorCount,
                                                  const Interpolation colorInterpolation,
                                                  const int* colorIndices,
                                                  const size_t colorIndicesCount,
                                                  const OpacityTypeT* opacities,
                                                  const size_t opacityCount,
                                                  const Interpolation opacityInterpolation,
                                                  const int* opacityIndices,
                                                  const size_t opacityIndicesCount,
                                                  const ISceneDeclutter::Options& options)
{
    // if color and opacity interpolations don't match, don't trust the data.
    bool useVertexColors = options.useVertexColor && colorInterpolation == opacityInterpolation &&
                           std::min(colorIndicesCount, opacityIndicesCount) > 0;
    if (options.isSelected)
    {
        pxr::GfVec3f orange(1.f, 0.5f, 0.f);
        DataSourceConstant_T<pxr::GfVec3f> colorSource{ orange };
        DrawMeshFromUSD_ChooseNormalSource(drawingInterface, faceCount, faceVertexIndices, faceVertexIndexCount,
                                           faceVertexCounts, faceVertexCountsSize, points, pointCount, normals,
                                           normalsCount, normalsInterpolation, colorSource, options);
    }
    else if (useVertexColors && colorInterpolation == FACEVARYING)
    {
        struct CombineColorFaceVarying
        {
            // TODO: we probably should not use pixar types here ,
            //  but we need to know the 4-element equivalent of ColorTypeT
            typedef pxr::GfVec4f OutputDataType; // required
            OutputDataType operator[](size_t index) const // required
            {
                // N.B. index is a face-vertex index
                const auto& c = colors[colorIndices[std::min(index, colorIndicesCount - 1)]];
                const auto& o = opacities[opacityIndices[std::min(index, opacityIndicesCount - 1)]];
                return pxr::GfVec4f(c[0], c[1], c[2], o);
            }
            const ColorTypeT* colors;
            const OpacityTypeT* opacities;
            const int* colorIndices;
            const int* opacityIndices;
            size_t colorIndicesCount;
            size_t opacityIndicesCount;
        };

        CombineColorFaceVarying colorSource = { colors,         opacities,         colorIndices,
                                                opacityIndices, colorIndicesCount, opacityIndicesCount };
        DrawMeshFromUSD_ChooseNormalSource(drawingInterface, faceCount, faceVertexIndices, faceVertexIndexCount,
                                           faceVertexCounts, faceVertexCountsSize, points, pointCount, normals,
                                           normalsCount, normalsInterpolation, colorSource, options);
    }
    else if (useVertexColors && colorInterpolation == VERTEX)
    {
        struct CombineColorPerVertex
        {
            // TODO: we probably should not use pixar types here ,
            //  but we need to know the 4-element equivalent of ColorTypeT
            typedef pxr::GfVec4f OutputDataType; // required
            OutputDataType operator[](size_t index) const // required
            {
                // N.B. index is a face-vertex index
                index = std::min(index, faceVertexIndexCount - 1);
                index = (size_t)faceVertexIndices[index]; // now index is a vertex index

                const auto& c = colors[colorIndices[std::min(index, colorIndicesCount - 1)]];
                const auto& o = opacities[opacityIndices[std::min(index, opacityIndicesCount - 1)]];
                return pxr::GfVec4f(c[0], c[1], c[2], o);
            }
            const int* faceVertexIndices;
            size_t faceVertexIndexCount;
            const ColorTypeT* colors;
            const OpacityTypeT* opacities;
            const int* colorIndices;
            const int* opacityIndices;
            size_t colorIndicesCount;
            size_t opacityIndicesCount;
        };

        CombineColorPerVertex colorSource = { faceVertexIndices, faceVertexIndexCount, colors,
                                              opacities,         colorIndices,         opacityIndices,
                                              colorIndicesCount, opacityIndicesCount };
        DrawMeshFromUSD_ChooseNormalSource(drawingInterface, faceCount, faceVertexIndices, faceVertexIndexCount,
                                           faceVertexCounts, faceVertexCountsSize, points, pointCount, normals,
                                           normalsCount, normalsInterpolation, colorSource, options);
    }
    else // bad data, or options.useVertexColors == false, or maybe (TODO) uniform interpolation
    {
        pxr::GfVec3f white(1);
        DataSourceConstant_T<pxr::GfVec3f> colorSource{ white };
        DrawMeshFromUSD_ChooseNormalSource(drawingInterface, faceCount, faceVertexIndices, faceVertexIndexCount,
                                           faceVertexCounts, faceVertexCountsSize, points, pointCount, normals,
                                           normalsCount, normalsInterpolation, colorSource, options);
    }
}


template <typename PointTypeT, typename NormalTypeT, typename ColorSourceTypeT>
void MeshUtils::DrawMeshFromUSD_ChooseNormalSource(ISceneVisualization::IDrawingInterface& drawingInterface,
                                                   size_t faceCount,
                                                   const int* faceVertexIndices,
                                                   size_t faceVertexIndexCount,
                                                   const int* faceVertexCounts,
                                                   size_t faceVertexCountsSize,
                                                   const PointTypeT* points,
                                                   size_t pointCount,
                                                   const NormalTypeT* normals,
                                                   size_t normalsCount,
                                                   Interpolation normalsInterpolation,
                                                   const ColorSourceTypeT& colorsSource,
                                                   const ISceneDeclutter::Options& options)
{
    if (normalsCount > 0 && normalsInterpolation == FACEVARYING)
    {
        DataSourceFaceVarying_T<NormalTypeT> normalsSource = { normals, normalsCount };
        DrawMesh(drawingInterface, faceCount, faceVertexIndices, faceVertexIndexCount, faceVertexCounts,
                 faceVertexCountsSize, points, pointCount, normalsSource, colorsSource, options);
    }
    else if (normalsCount > 0 && normalsInterpolation == VERTEX)
    {
        DataSourcePerVertex_T<NormalTypeT> normalsSource = { faceVertexIndices, faceVertexIndexCount, normals,
                                                             normalsCount };
        DrawMesh(drawingInterface, faceCount, faceVertexIndices, faceVertexIndexCount, faceVertexCounts,
                 faceVertexCountsSize, points, pointCount, normalsSource, colorsSource, options);
    }
    else // bad data, or maybe (TODO) constant or uniform
    {
        DataSourceEmpty_T<NormalTypeT> normalsSource;
        ISceneDeclutter::Options optionsNormalsDisabled(options);
        optionsNormalsDisabled.drawNormals = false;

        DrawMesh(drawingInterface, faceCount, faceVertexIndices, faceVertexIndexCount, faceVertexCounts,
                 faceVertexCountsSize, points, pointCount, normalsSource, colorsSource, optionsNormalsDisabled);
    }
}


template <typename PointTypeT, typename NormalSourceTypeT, typename ColorSourceTypeT>
void MeshUtils::DrawMesh(ISceneVisualization::IDrawingInterface& drawingInterface,
                         size_t faceCount,
                         const int* faceVertexIndices,
                         size_t faceVertexIndexCount,
                         const int* faceVertexCounts,
                         size_t faceVertexCountsSize,
                         const PointTypeT* points,
                         size_t pointCount,
                         const NormalSourceTypeT& normals,
                         const ColorSourceTypeT& colors,
                         const ISceneDeclutter::Options& options)
{
    int currentPointIndex = 0;
    for (size_t face = 0; face < faceCount; face++)
    {
        // faceVertexCounts can optionally be one, if it is uniform (procedurally generated data)
        bool uniformVerticesPerFace = (faceVertexCountsSize == 1);
        int numVerticesThisFace = uniformVerticesPerFace ? faceVertexCounts[0] : faceVertexCounts[face];

        if (options.drawPoints)
        {
            // TODO: we're drawing vertices multiple times because colors are per-vertex per-face.
            // Otherwise we could loop over vertices instead of faces.
            for (int facePointIndex = 0; facePointIndex < numVerticesThisFace; ++facePointIndex)
            {
                // HACK - until points are supported by DebugDraw (or until we replace with SceneRenderer interface),
                // draw points
                //  as tiny lines.
                size_t thisPointIndex = currentPointIndex + facePointIndex;
                const PointTypeT& point = points[faceVertexIndices[thisPointIndex]];
                const typename ColorSourceTypeT::OutputDataType& color = colors[thisPointIndex];

                drawingInterface.DrawPoints(&point, 1, ISceneVisualization::DefaultVecConversion(), &color, 1,
                                            ISceneVisualization::DefaultColorConversion(), &options.pointWidth, 1);
            }
        }

        if (options.drawNormals)
        {
            PointTypeT pointsAccumulated(0);
            typename NormalSourceTypeT::OutputDataType normalsAccumulated(0);
            typename ColorSourceTypeT::OutputDataType colorsAccumulated(0);

            for (int facePointIndex = 0; facePointIndex < numVerticesThisFace; facePointIndex++)
            {
                size_t thisPointIndex = currentPointIndex + facePointIndex;
                pointsAccumulated += points[faceVertexIndices[thisPointIndex]];

                normalsAccumulated += normals[thisPointIndex];
                colorsAccumulated += colors[thisPointIndex];
            }
            // draw the tri's avg normal line at its center
            if (numVerticesThisFace != 0)
            {
                auto divisor = (typename std::remove_reference<decltype(pointsAccumulated[0])>::type)numVerticesThisFace;
                pointsAccumulated /= divisor;
                normalsAccumulated /= divisor;
                colorsAccumulated /= divisor;
            }
            PointTypeT faceCenter = pointsAccumulated;
            typename NormalSourceTypeT::OutputDataType faceNormal = (normalsAccumulated.GetNormalized()) * 4;
            typename ColorSourceTypeT::OutputDataType faceColor = colorsAccumulated;

            drawingInterface.DrawLines(&faceCenter, 1, ISceneVisualization::DefaultVecConversion(), &faceNormal, 1,
                                       ISceneVisualization::DefaultVecConversion(), // make a bit bigger, easier to see.
                                       &faceColor, 1, ISceneVisualization::DefaultColorConversion(), &options.lineWidth,
                                       1);
        }

        if (options.drawWireframe)
        {
            // this sucks, one segment at a time. policy class could possibly allow the compiler
            //  to unroll this for known vert/face situations (like triangulated meshes).
            // otherwise, use a vector that eventually resizes to worst case
            for (int facePointIndex = 0; facePointIndex < numVerticesThisFace; ++facePointIndex)
            {
                size_t thisPointIndex = currentPointIndex + facePointIndex,
                       nextPointIndex = currentPointIndex + (facePointIndex + 1) % numVerticesThisFace;
                PointTypeT ptPair[2] = { points[faceVertexIndices[thisPointIndex]],
                                         points[faceVertexIndices[nextPointIndex]] };

                typename ColorSourceTypeT::OutputDataType colorPair[2] = { colors[thisPointIndex],
                                                                           colors[nextPointIndex] };

                drawingInterface.DrawLineStrip(&ptPair[0], 2, ISceneVisualization::DefaultVecConversion(), &colorPair[0],
                                               2, ISceneVisualization::DefaultColorConversion(), &options.lineWidth, 1);
            }
        }

        if (options.drawTangents)
        {
            CARB_LOG_WARN_ONCE("Tangent visualization currently unsupported for Mesh prims.");
        }

        currentPointIndex += numVerticesThisFace;
    }
}

template <typename T>
void ExtractBasisCurvesPrimvar(pxr::UsdGeomPrimvarsAPI primvarsAPI,
                               const pxr::TfToken& token,
                               const T& defaultValue,
                               pxr::VtArray<T>& primvarData,
                               pxr::VtArray<int>& primvarIndices,
                               pxr::TfToken& primvarInterpolation)
{
    primvarInterpolation = pxr::UsdGeomTokens->constant;
    if (primvarsAPI.HasPrimvar(token))
    {
        pxr::UsdGeomPrimvar primvar = primvarsAPI.GetPrimvar(token);
        primvar.Get(&primvarData);
        primvarInterpolation = primvar.GetInterpolation();
        if (primvar.IsIndexed())
        {
            primvar.GetIndicesAttr().Get(&primvarIndices);
        }
    }
    if (primvarData.empty())
    {
        primvarData.push_back(defaultValue);
    }
    if (primvarIndices.empty())
    {
        primvarIndices.resize(primvarData.size());
        std::iota(primvarIndices.begin(), primvarIndices.end(), 0);
    }
}

template <typename T>
void GenerateRenderingData(const omni::geometry::curves::SplineCurve& curve,
                           const pxr::TfToken& typeToken,
                           const pxr::VtArray<T>& data,
                           const pxr::VtArray<int>& indices,
                           const pxr::TfToken& interpolation,
                           const size_t curveIdx,
                           const size_t cvOffset,
                           const size_t spanOffset,
                           const T& defaultValue,
                           const size_t cvCount,
                           const size_t tessellationCount,
                           const size_t curveStepsPerSegment,
                           std::vector<T>* cvData,
                           std::vector<T>* tessellatedData)
{
    CARB_ASSERT(!data.empty() && !indices.empty());
    if (cvData != nullptr)
    {
        cvData->resize(cvCount);
        if (interpolation == pxr::UsdGeomTokens->constant)
        {
            // should be data[0], but to keep a consistent discipline
            // we'll never index into data directly in this function
            const int& idx = indices[0];
            const T& t = data[idx];
            for (auto& cvT : *cvData)
            {
                cvT = t;
            }
        }
        else if (interpolation == pxr::UsdGeomTokens->uniform)
        {
            const int& idx = curveIdx < indices.size() ? indices[curveIdx] : indices[0];
            CARB_ASSERT(idx < data.size());
            const T& t = data[idx];
            for (auto& cvT : *cvData)
            {
                cvT = t;
            }
        }
        else if (interpolation == pxr::UsdGeomTokens->vertex)
        {
            for (size_t i = 0; i < cvData->size(); i++)
            {
                const int& idx = (cvOffset + i) < indices.size() ? indices[cvOffset + i] : indices[0];
                CARB_ASSERT(idx < data.size());
                (*cvData)[i] = data[idx];
            }
        }
        else
        {
            // varying -> XXX not dealing with this case for control point visualization...
            // faceVarying -> invalid interpolation for curves anyway
            for (auto& cvT : *cvData)
            {
                cvT = defaultValue;
            }
        }
    }

    if (tessellatedData != nullptr)
    {
        if (typeToken == pxr::UsdGeomTokens->linear)
        {
            tessellatedData->resize(cvCount); // N.B. cvCount, not tessellationCount for linear curve

            if (interpolation == pxr::UsdGeomTokens->constant)
            {
                // should be data[0], but to keep a consistent discipline
                // we'll never index into data directly in this function
                const int& idx = indices[0];
                const T& t = data[idx];
                for (auto& cvT : *tessellatedData)
                {
                    cvT = t;
                }
            }
            else if (interpolation == pxr::UsdGeomTokens->uniform)
            {
                const int& idx = curveIdx < indices.size() ? indices[curveIdx] : indices[0];
                CARB_ASSERT(idx < data.size());
                const T& t = data[idx];
                for (auto& cvT : *tessellatedData)
                {
                    cvT = t;
                }
            }
            else if (interpolation == pxr::UsdGeomTokens->vertex ||
                     interpolation == pxr::UsdGeomTokens->varying) // treated
                                                                   // the
                                                                   // same
                                                                   // as
                                                                   // vertex
                                                                   // for
                                                                   // linear
                                                                   // curves
            {
                for (size_t i = 0; i < tessellatedData->size(); i++)
                {
                    const int idx = cvOffset + i < indices.size() ? indices[cvOffset + i] : indices[0];
                    CARB_ASSERT(idx < data.size());
                    (*tessellatedData)[i] = data[idx];
                }
            }
            else
            {
                // faceVarying -> invalid interpolation for curves anyway
                for (auto& tessellatedT : *tessellatedData)
                {
                    tessellatedT = defaultValue;
                }
            }
        }
        else
        {
            tessellatedData->resize(tessellationCount);

            if (interpolation == pxr::UsdGeomTokens->constant)
            {
                // should be data[0], but to keep a consistent discipline
                // we'll never index into data directly in this function
                const int& idx = indices[0];
                const T& t = data[idx];
                for (auto& cvT : *tessellatedData)
                {
                    cvT = t;
                }
            }
            else if (interpolation == pxr::UsdGeomTokens->uniform)
            {
                const int& idx = curveIdx < indices.size() ? indices[curveIdx] : indices[0];
                CARB_ASSERT(idx < data.size());
                const T& t = data[idx];
                for (auto& cvT : *tessellatedData)
                {
                    cvT = t;
                }
            }
            else if (interpolation == pxr::UsdGeomTokens->vertex)
            {
                std::vector<T> flatData;
                std::transform(
                    indices.begin(), indices.end(), std::back_inserter(flatData), [&](int id) { return data[id]; });

                curve.tessellate(flatData.data(), flatData.size(), *tessellatedData, curveStepsPerSegment, false);
            }
            else if (interpolation == pxr::UsdGeomTokens->varying)
            {
                for (size_t i = 0; i < tessellatedData->size(); i++)
                {
                    const size_t segmentIdx = i / curveStepsPerSegment;
                    const int idx =
                        spanOffset + segmentIdx < indices.size() ? indices[spanOffset + segmentIdx] : indices[0];
                    CARB_ASSERT(idx < data.size());
                    (*tessellatedData)[i] = data[idx];
                }
            }
            else
            {
                // faceVarying -> invalid interpolation for curves anyway
                for (auto& tessellatedT : *tessellatedData)
                {
                    tessellatedT = defaultValue;
                }
            }
        }
    }
}


inline void MeshUtils::DrawBasisCurvesFromUSD(ISceneVisualization::IDrawingInterface& drawingInterface,
                                              pxr::UsdPrim prim,
                                              const ISceneDeclutter::Options& options)
{
    using omni::math::linalg::safeCastToOmni;
    using omni::math::linalg::vec3f;
    using omni::math::linalg::vec4f;
    using namespace omni::geometry::curves;

    pxr::UsdGeomBasisCurves basisCurvesPrim(prim);
    if (!basisCurvesPrim)
    {
        return;
    }

    pxr::VtArray<pxr::GfVec3f> pointsUSD;
    if (!GetValueFromAttribute(prim, pxr::UsdGeomTokens->points, pointsUSD))
    {
        return;
    }

    // for colors -- see section on Primvar Interpolation:
    // https://graphics.pixar.com/usd/dev/api/class_usd_geom_basis_curves.html
    // in particular:
    // constant -- color applies to entire prim
    // uniform -- colors are specified per-curve
    // vertex -- cubic interpolation (for cubic curves) -- number of colors == number of control points
    // varying -- segment varying data (number of segments in curve, which depends on wrap setting)
    // faceVarying -- N/A

    pxr::UsdGeomPrimvarsAPI primvarsAPI(prim);
    if (!primvarsAPI)
    {
        return;
    }

    pxr::VtArray<pxr::GfVec3f> colors;
    pxr::VtArray<int> colorIndices;
    pxr::TfToken colorInterpolation;

    pxr::VtArray<float> opacities;
    pxr::VtArray<int> opacityIndices;
    pxr::TfToken opacityInterpolation;

    pxr::VtArray<pxr::GfVec3f> normals;
    pxr::VtArray<int> normalIndices;
    pxr::TfToken normalInterpolation;

    pxr::VtArray<float> widths;
    pxr::VtArray<int> widthIndices;
    pxr::TfToken widthInterpolation;

    if (options.useVertexColor)
    {
        ExtractBasisCurvesPrimvar(primvarsAPI, pxr::UsdGeomTokens->primvarsDisplayColor, pxr::GfVec3f(1.f, 1.f, 1.f),
                                  colors, colorIndices, colorInterpolation);
        ExtractBasisCurvesPrimvar(primvarsAPI, pxr::UsdGeomTokens->primvarsDisplayOpacity, 1.f, opacities,
                                  opacityIndices, opacityInterpolation);
    }

    if (options.drawNormals)
    {
        pxr::UsdAttribute attr = basisCurvesPrim.GetNormalsAttr();
        attr.Get(&normals);
        normalInterpolation = basisCurvesPrim.GetNormalsInterpolation();
        if (normals.empty())
        {
            normals.push_back(pxr::GfVec3f(0.f, 0.f, 0.f));
        }
        normalIndices.resize(normals.size());
        std::iota(normalIndices.begin(), normalIndices.end(), 0);
    }

    if (options.useWidthsPrimvar)
    {
        pxr::UsdAttribute attr = basisCurvesPrim.GetWidthsAttr();
        attr.Get(&widths);
        widthInterpolation = basisCurvesPrim.GetWidthsInterpolation();
        if (widths.empty())
        {
            widths.push_back(options.lineWidth);
        }
        widthIndices.resize(widths.size());
        std::iota(widthIndices.begin(), widthIndices.end(), 0);
    }

    std::vector<vec3f> points(safeCastToOmni(pointsUSD.data()), safeCastToOmni(pointsUSD.data() + pointsUSD.size()));


    pxr::TfToken basisToken;
    basisCurvesPrim.GetBasisAttr().Get(&basisToken);
    pxr::TfToken wrapToken;
    basisCurvesPrim.GetWrapAttr().Get(&wrapToken);
    pxr::TfToken typeToken;
    basisCurvesPrim.GetTypeAttr().Get(&typeToken);

    eBasisCurveWrap wrapType = eBasisCurveWrap::Pinned;
    if (wrapToken == pxr::UsdGeomTokens->nonperiodic)
    {
        wrapType = eBasisCurveWrap::NonPeriodic;
    }
    else if (wrapToken == pxr::UsdGeomTokens->periodic)
    {
        wrapType = eBasisCurveWrap::Periodic;
    }
    else if (wrapToken == pxr::UsdGeomTokens->pinned)
    {
        wrapType = eBasisCurveWrap::Pinned;
    }

    eBasisCurveType curveType;
    if (basisToken == pxr::UsdGeomTokens->bspline)
    {
        curveType = eBasisCurveType::BSpline;
    }
    else if (basisToken == pxr::UsdGeomTokens->bezier)
    {
        curveType = eBasisCurveType::Bezier;
    }
    else if (basisToken == pxr::UsdGeomTokens->catmullRom)
    {
        curveType = eBasisCurveType::CatmullRom;
    }
    else
    {
        return;
    }

    pxr::VtIntArray curveVertexCounts;
    if (!GetValueFromAttribute(prim, pxr::UsdGeomTokens->curveVertexCounts, curveVertexCounts))
    {
        curveVertexCounts.push_back((int)points.size());
    }

    pxr::GfVec3f uniformColor(1.f);

    if (options.isSelected)
    {
        uniformColor = pxr::GfVec3f(1.f, 0.5f, 0.f);
    }

    size_t startIdx = 0;
    size_t spanStartIdx = 0;
    for (size_t i = 0; i < curveVertexCounts.size(); i++)
    {
        const size_t count = curveVertexCounts[i];
        gsl::span<vec3f> controlPoints(points.data() + startIdx, count);
        SplineCurve curve(wrapType, curveType);
        const size_t tessellationCount =
            curve.getTessellationPointCount(controlPoints.size(), CURVE_STEPS_PER_SEGMENT, false);

        std::vector<pxr::GfVec4f> cvRGBA, tessellatedRGBA;
        if (options.isSelected)
        {
            cvRGBA.push_back(pxr::GfVec4f(1.f, 0.5f, 0.f, 1.f));
            tessellatedRGBA.push_back(pxr::GfVec4f(1.f, 0.5f, 0.f, 1.f));
        }
        else if (options.useVertexColor)
        {
            std::vector<pxr::GfVec3f> cvColors, tessellatedColors;
            std::vector<float> cvOpacities, tessellatedOpacities;
            GenerateRenderingData(curve, typeToken, colors, colorIndices, colorInterpolation, i, startIdx, spanStartIdx,
                                  pxr::GfVec3f(1.f, 1.f, 1.f), controlPoints.size(), tessellationCount,
                                  CURVE_STEPS_PER_SEGMENT, options.drawPoints ? &cvColors : nullptr,
                                  options.drawWireframe ? &tessellatedColors : nullptr);

            GenerateRenderingData(curve, typeToken, opacities, opacityIndices, opacityInterpolation, i, startIdx,
                                  spanStartIdx, 1.f, controlPoints.size(), tessellationCount, CURVE_STEPS_PER_SEGMENT,
                                  options.drawPoints ? &cvOpacities : nullptr,
                                  options.drawWireframe ? &tessellatedOpacities : nullptr);

            CARB_ASSERT(cvColors.size() == cvOpacities.size() && tessellatedColors.size() == tessellatedOpacities.size());
            cvRGBA.resize(cvColors.size());
            tessellatedRGBA.resize(tessellatedColors.size());
            for (size_t i = 0; i < cvRGBA.size(); i++)
            {
                cvRGBA[i] = pxr::GfVec4f(cvColors[i][0], cvColors[i][1], cvColors[i][2], cvOpacities[i]);
            }
            for (size_t i = 0; i < tessellatedRGBA.size(); i++)
            {
                tessellatedRGBA[i] = pxr::GfVec4f(
                    tessellatedColors[i][0], tessellatedColors[i][1], tessellatedColors[i][2], tessellatedOpacities[i]);
            }
        }
        else
        {
            cvRGBA.push_back(pxr::GfVec4f(1.f, 1.f, 1.f, 1.f));
            tessellatedRGBA.push_back(pxr::GfVec4f(1.f, 1.f, 1.f, 1.f));
        }

        std::vector<float> cvWidths, tessellatedWidths;
        if (options.useWidthsPrimvar)
        {
            GenerateRenderingData(curve, typeToken, widths, widthIndices, widthInterpolation, i, startIdx, spanStartIdx,
                                  1.f, controlPoints.size(), tessellationCount, CURVE_STEPS_PER_SEGMENT,
                                  options.drawPoints ? &cvWidths : nullptr,
                                  options.drawWireframe ? &tessellatedWidths : nullptr);
            // let's not scale width by the lineWidth param... use widths if they're present;
            // otherwise use the lineWidth value.
            for (auto& w : cvWidths)
            {
                w *= options.pointWidth;
            }
            for (auto& w : tessellatedWidths)
            {
                w *= options.lineWidth;
            }
        }
        else
        {
            cvWidths.push_back(options.lineWidth);
            tessellatedWidths.push_back(options.lineWidth);
        }

        std::vector<pxr::GfVec3f> cvNormals, tessellatedNormals;
        if (options.drawNormals)
        {
            GenerateRenderingData(curve, typeToken, normals, normalIndices, normalInterpolation, i, startIdx,
                                  spanStartIdx, pxr::GfVec3f(0.f, 0.f, 0.f), controlPoints.size(), tessellationCount,
                                  CURVE_STEPS_PER_SEGMENT,
                                  false ? &cvNormals : nullptr, // XXX per-cv normals don't necessarily mean anything;
                                                                // we won't use them here
                                  options.drawNormals ? &tessellatedNormals : nullptr);
        }

        // Ok... now actually draw stuff
        if (options.drawPoints)
        {
            drawingInterface.DrawPoints(points.data(), points.size(), ISceneVisualization::DefaultVecConversion(),
                                        cvRGBA.data(), cvRGBA.size(), ISceneVisualization::DefaultColorConversion(),
                                        cvWidths.data(), cvWidths.size());
        }

        if (typeToken == pxr::UsdGeomTokens->linear)
        {
            if (options.drawWireframe)
            {
                if (wrapToken == PXR_NS::UsdGeomTokens->periodic)
                {
                    drawingInterface.DrawLineLoop(controlPoints.data(), controlPoints.size(),
                                                  ISceneVisualization::DefaultVecConversion(), tessellatedRGBA.data(),
                                                  tessellatedRGBA.size(), ISceneVisualization::DefaultColorConversion(),
                                                  tessellatedWidths.data(), tessellatedWidths.size());
                }
                else
                {
                    drawingInterface.DrawLineStrip(controlPoints.data(), controlPoints.size(),
                                                   ISceneVisualization::DefaultVecConversion(), tessellatedRGBA.data(),
                                                   tessellatedRGBA.size(), ISceneVisualization::DefaultColorConversion(),
                                                   tessellatedWidths.data(), tessellatedWidths.size());
                }
            }
            if (options.drawNormals)
            {
                drawingInterface.DrawLines(controlPoints.data(), controlPoints.size(),
                                           ISceneVisualization::DefaultVecConversion(), tessellatedNormals.data(),
                                           tessellatedNormals.size(), ISceneVisualization::DefaultVecConversion(),
                                           tessellatedRGBA.data(), tessellatedRGBA.size(),
                                           ISceneVisualization::DefaultColorConversion(), &options.lineWidth, 1);
            }
        }
        else
        {
            std::vector<vec3f> tessellatedPositions;
            curve.tessellate(
                controlPoints.data(), controlPoints.size(), tessellatedPositions, CURVE_STEPS_PER_SEGMENT, false);

            if (options.drawWireframe)
            {
                if (wrapToken == PXR_NS::UsdGeomTokens->periodic)
                {
                    drawingInterface.DrawLineLoop(tessellatedPositions.data(), tessellatedPositions.size(),
                                                  ISceneVisualization::DefaultVecConversion(), tessellatedRGBA.data(),
                                                  tessellatedRGBA.size(), ISceneVisualization::DefaultColorConversion(),
                                                  tessellatedWidths.data(), tessellatedWidths.size());
                }
                else
                {
                    drawingInterface.DrawLineStrip(tessellatedPositions.data(), tessellatedPositions.size(),
                                                   ISceneVisualization::DefaultVecConversion(), tessellatedRGBA.data(),
                                                   tessellatedRGBA.size(), ISceneVisualization::DefaultColorConversion(),
                                                   tessellatedWidths.data(), tessellatedWidths.size());
                }
            }

            if (options.drawNormals)
            {
                drawingInterface.DrawLines(tessellatedPositions.data(), tessellatedPositions.size(),
                                           ISceneVisualization::DefaultVecConversion(), tessellatedNormals.data(),
                                           tessellatedNormals.size(), ISceneVisualization::DefaultVecConversion(),
                                           tessellatedRGBA.data(), tessellatedRGBA.size(),
                                           ISceneVisualization::DefaultColorConversion(), &options.lineWidth, 1);
            }
        }

        if (options.drawTangents)
        {
            if (basisToken == pxr::UsdGeomTokens->bezier && typeToken == pxr::UsdGeomTokens->cubic)
            {
                const size_t degree = 3; // TODO: generalize, at least to linear as well
                if (controlPoints.size() >= degree)
                {
                    for (size_t j = 0; j < controlPoints.size() - degree + 1; j += degree)
                    {
                        const vec3f& x0 = controlPoints[j];
                        const vec3f v0 = controlPoints[j + 1] - x0;

                        bool wrapEndPoint = false;
                        // special case for the last tangent of periodic curve when endpoint is not repeated in data
                        if (wrapToken == PXR_NS::UsdGeomTokens->periodic && j + degree >= controlPoints.size())
                        {
                            wrapEndPoint = true;
                        }

                        const vec3f& x1 = wrapEndPoint ? controlPoints[0] : controlPoints[j + 3];
                        const vec3f v1 = controlPoints[j + 2] - x1;

                        drawingInterface.DrawLines(&x0, 1, &v0, 1, &uniformColor, 1, &options.lineWidth, 1);
                        drawingInterface.DrawLines(&x1, 1, &v1, 1, &uniformColor, 1, &options.lineWidth, 1);
                    }
                }
            }
        }

        startIdx += curveVertexCounts[i];
        spanStartIdx += curve.getSegmentCount(controlPoints.size());
    }
}


} // namespace renderer
} // namespace omni
