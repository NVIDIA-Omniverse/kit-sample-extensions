//
// Copyright 2016 Pixar
//
// Licensed under the Apache License, Version 2.0 (the "Apache License")
// with the following modification; you may not use this file except in
// compliance with the Apache License and the following modification to it:
// Section 6. Trademarks. is deleted and replaced with:
//
// 6. Trademarks. This License does not grant permission to use the trade
//    names, trademarks, service marks, or product names of the Licensor
//    and its affiliates, except as required to comply with Section 4(c) of
//    the License and to reproduce the content of the NOTICE file.
//
// You may obtain a copy of the Apache License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the Apache License with the above modification is
// distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
// KIND, either express or implied. See the Apache License for the specific
// language governing permissions and limitations under the Apache License.
//
///
/// \file Sdf/textFileFormat.cpp


#include "metricsAssemblerFileFormat.h"

#include <pxr/usd/sdf/layer.h>

#include <iostream>

PXR_NAMESPACE_OPEN_SCOPE

TF_DEFINE_PUBLIC_TOKENS(MetricsAssemblerFormatTokens, METRICS_ASSEMBLER_FORMAT_TOKENS);

TF_REGISTRY_FUNCTION(TfType)
{
    SDF_DEFINE_FILE_FORMAT(MetricsAssemblerFileFormat, SdfFileFormat);
}

MetricsAssemblerFileFormat::MetricsAssemblerFileFormat()
    : SdfFileFormat(MetricsAssemblerFormatTokens->Id,
                    MetricsAssemblerFormatTokens->Version,
                    MetricsAssemblerFormatTokens->Target,
                    MetricsAssemblerFormatTokens->Extension)
{
    // Do Nothing.
}

MetricsAssemblerFileFormat::MetricsAssemblerFileFormat(const TfToken& formatId,
                                                       const TfToken& versionString,
                                                       const TfToken& target)
    : SdfFileFormat(formatId,
                    (versionString.IsEmpty() ? MetricsAssemblerFormatTokens->Version : versionString),
                    (target.IsEmpty() ? MetricsAssemblerFormatTokens->Target : target),
                    formatId)
{
    // Do Nothing.
}

MetricsAssemblerFileFormat::~MetricsAssemblerFileFormat()
{
    // Do Nothing.
}

bool MetricsAssemblerFileFormat::Read(SdfLayer* layer, const std::string& resolvedPath, bool metadataOnly) const
{
    SdfAbstractDataRefPtr data = InitData(layer->GetFileFormatArguments());
    _SetLayerData(layer, data);

    // I had to disable the following since it would cause Kit to hang as it was opening a scene
    // Not sure what this is needed the layer identifier should already be set before reading the data
    // layer->SetIdentifier(resolvedPath);
    return true;
}


PXR_NAMESPACE_CLOSE_SCOPE
