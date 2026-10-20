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
#ifndef PXR_USD_METRICS_ASSEMBLER_FILE_FORMAT_H
#define PXR_USD_METRICS_ASSEMBLER_FILE_FORMAT_H

/// \file sdf/textFileFormat.h

#include "api.h"
#include "pxr/base/tf/staticTokens.h"
#include "pxr/usd/sdf/declareHandles.h"
#include "pxr/usd/sdf/fileFormat.h"

PXR_NAMESPACE_OPEN_SCOPE

TF_DECLARE_WEAK_AND_REF_PTRS(MetricsAssemblerFileFormat);

#define METRICS_ASSEMBLER_FORMAT_TOKENS                                                                                \
    ((Id, "metricsAssembler"))((Version, "1.0.0"))((Extension, "metricsAssembler"))((Target, "usd"))

TF_DECLARE_PUBLIC_TOKENS(MetricsAssemblerFormatTokens, METRICS_ASSEMBLER_FORMAT_TOKENS);


/// \class MetricsAssemblerFileFormat
///
/// Test
///
class MetricsAssemblerFileFormat : public SdfFileFormat
{
public:
    // MetricsAssemblerFileFormat overrides.
    METRICSASSEMBLER_API
    virtual bool CanRead(const std::string& file) const override
    {
        return false;
    }

    METRICSASSEMBLER_API
    virtual bool Read(SdfLayer* layer, const std::string& resolvedPath, bool metadataOnly) const override;

    METRICSASSEMBLER_API
    virtual bool WriteToFile(const SdfLayer& layer,
                             const std::string& filePath,
                             const std::string& comment = std::string(),
                             const FileFormatArguments& args = FileFormatArguments()) const override
    {
        printf("MetricsAssemblerFileFormat:writetofile\n");
        printf("File: %s\n", filePath.c_str());
        return false;
    }

    METRICSASSEMBLER_API
    virtual bool ReadFromString(SdfLayer* layer, const std::string& str) const override
    {
        printf("MetricsAssemblerFileFormat:readfromstring\n");
        return true;
    }

    METRICSASSEMBLER_API
    virtual bool WriteToString(const SdfLayer& layer,
                               std::string* str,
                               const std::string& comment = std::string()) const override
    {
        printf("MetricsAssemblerFileFormat:writetostring\n");
        return true;
    }

    METRICSASSEMBLER_API
    virtual bool WriteToStream(const SdfSpecHandle& spec, std::ostream& out, size_t indent) const override
    {
        printf("MetricsAssemblerFileFormat:writetostream\n");
        return true;
    }

protected:
    SDF_FILE_FORMAT_FACTORY_ACCESS;

    /// Destructor.
    METRICSASSEMBLER_API
    virtual ~MetricsAssemblerFileFormat();

    /// Constructor.
    METRICSASSEMBLER_API
    MetricsAssemblerFileFormat();

    /// Constructor. This form of the constructor may be used by formats that
    /// use the .sdf text format as their internal representation.
    /// If a non-empty versionString and target are provided, they will be
    /// used as the file format version and target; otherwise the .sdf format
    /// version and target will be implicitly used.
    METRICSASSEMBLER_API
    explicit MetricsAssemblerFileFormat(const TfToken& formatId,
                                        const TfToken& versionString = TfToken(),
                                        const TfToken& target = TfToken());

private:
    // Override to return false.  Reloading anonymous text layers clears their
    // content.
    METRICSASSEMBLER_API virtual bool _ShouldSkipAnonymousReload() const override
    {
        return false;
    }

    METRICSASSEMBLER_API virtual bool _ShouldReadAnonymousLayers() const override
    {
        return true;
    }
};

PXR_NAMESPACE_CLOSE_SCOPE

#endif // PXR_USD_METRICS_ASSEMBLER_FILE_FORMAT_H
