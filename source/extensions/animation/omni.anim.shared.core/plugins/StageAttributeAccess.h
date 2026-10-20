// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#pragma once
#include <usdrt/scenegraph/ovstage/Stage.h>
#include <ovstage/ovstage_api/ovstage_api.h>
#include <pxr/base/gf/matrix4d.h>
#include <algorithm>
#include <array>
#include <cstring>
#include <limits>
#include <map>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <type_traits>
#include <vector>

namespace omni::anim::shared::stage
{
// Extension-local consumer state. Kit owns the provider, population and write floor.
struct StageAccess
{
    usdrt::ovstage::StageRefPtr stage;
    uint64_t generation = 0;
    ovstage_ordinal_t ordinal = 0;
    std::vector<omni::runtime::core::StageEdit> edits;
    // Same-update producer inputs used only by this extension's evaluation.
    std::map<std::pair<std::string, std::string>, omni::runtime::core::StageEdit> inputs;
};

class AttributeAccess
{
public:
    using Value = omni::runtime::core::StageEdit;
    using ValueType = omni::runtime::core::StageValueType;
    using Semantic = omni::runtime::core::StageValueSemantic;
    explicit AttributeAccess(StageAccess* instance) : m_instance(instance) { checkFrame(); }
    StageAccess* instance() const noexcept { return m_instance; }
    struct Query { StageAccess* owner; std::vector<std::string> paths; };
    Query paths(const std::vector<std::string_view>& names) const
    {
        Query result{m_instance,{}};
        for (auto path : names)
        {
            if (path.empty() || path.front() != '/') throw std::invalid_argument("Stage path must be absolute");
            result.paths.emplace_back(path);
        }
        return result;
    }
    uint64_t token(std::string_view name) const
    {
        checkFrame();
        if (name.empty()) return 0;
        std::vector<uint64_t> ids;
        if (!m_instance->stage->InternTokenStrings({std::string(name)}, ids) || ids.size() != 1)
            fail("intern token");
        return ids.front();
    }
    std::string tokenString(uint64_t id) const
    {
        checkFrame();
        std::vector<std::string> values;
        if (!m_instance->stage->ResolveTokenStrings({id}, values) || values.size() != 1) fail("resolve token");
        return values.front();
    }
    std::vector<std::string> relationships(std::string_view path, std::string_view attribute) const
    {
        checkFrame();
        std::vector<std::string> result;
        if (!m_instance->stage->ReadRelationshipTargets(path, attribute, result))
        {
            if (m_instance->stage->GetLastDiagnostic().status == usdrt::ovstage::Status::eNotFound) return {};
            fail("read relationship");
        }
        checkFrame();
        return result;
    }
    std::optional<Value> readRaw(std::string_view path, std::string_view attribute, ovstage_ordinal_t ordinal) const
    {
        checkOrdinal(ordinal);
        for (auto it = m_instance->edits.rbegin(); it != m_instance->edits.rend(); ++it)
            if (it->primPath == path && it->attribute == attribute)
                return it->kind == omni::runtime::core::StageEditKind::eErase ? std::nullopt : std::optional<Value>(*it);
        auto input = m_instance->inputs.find({std::string(path),std::string(attribute)});
        if (input != m_instance->inputs.end())
            return input->second.kind == omni::runtime::core::StageEditKind::eErase ? std::nullopt : std::optional<Value>(input->second);
        // A producer's root edit can precede Kit's hierarchy commit. For this
        // extension's same-update evaluation, compose only affected ancestors
        // from ovstage local values; otherwise use Kit's authoritative world value.
        if (attribute == "omni:fabric:worldMatrix" && hasPendingAncestor(path))
        {
            PXR_NS::GfMatrix4d world(1.0);
            for (std::string current(path); current != "/" && !current.empty();)
            {
                auto local = readValue<std::array<double,16>>(current,"omni:xform",{kDLFloat,64,16},ordinal);
                if (local) { PXR_NS::GfMatrix4d matrix; std::copy(local->begin(),local->end(),matrix.data()); world *= matrix; }
                auto reset = readValue<bool>(current,"omni:resetXformStack",{kDLBool,8,1},ordinal);
                if (reset.value_or(false)) break;
                const auto slash = current.find_last_of('/');
                current = slash == 0 ? "/" : current.substr(0,slash);
            }
            Value derived; derived.primPath=path; derived.attribute=attribute;
            derived.type={kDLFloat,64,16,false,Semantic::eMatrix};
            derived.bytes.resize(sizeof(double)*16);
            std::memcpy(derived.bytes.data(),world.data(),derived.bytes.size());
            return derived;
        }
        Value result;
        result.primPath = path; result.attribute = attribute;
        usdrt::ovstage::Diagnostic diagnostic;
        if (!m_instance->stage->ReadAttributeRaw(path, attribute, &result.type, &result.bytes, &diagnostic))
        {
            if (diagnostic.status == usdrt::ovstage::Status::eNotFound) { checkFrame(); return std::nullopt; }
            throw std::runtime_error("Kit ovstage read failed: " + std::to_string(int(diagnostic.status)));
        }
        checkFrame();
        return result;
    }
    std::optional<std::string> readString(std::string_view path, std::string_view name,
                                          ovstage_ordinal_t ordinal) const
    {
        auto value=readRaw(path,name,ordinal);
        if (!value) return std::nullopt;
        // Kit population stores authored strings as interned IDs. Facade-created
        // strings can also use the public byte-array string representation.
        if (value->type.code==kDLUInt && value->type.bits==64 && value->type.lanes==1 &&
            !value->type.isArray && value->bytes.size()==sizeof(uint64_t))
        {
            uint64_t id; std::memcpy(&id,value->bytes.data(),sizeof(id));
            return tokenString(id);
        }
        if (value->type.code==kDLUInt && value->type.bits==8 && value->type.lanes==1 && value->type.isArray)
            return std::string(value->bytes.begin(),value->bytes.end());
        throw std::runtime_error("Kit ovstage attribute is not a string");
    }
    template<class T>
    std::optional<T> readValue(std::string_view path, std::string_view name, DLDataType type,
                               ovstage_ordinal_t ordinal) const
    {
        validateType<T>(type);
        auto value = readRaw(path,name,ordinal);
        if (!value) return std::nullopt;
        validateValue(*value,type,false);
        if (value->bytes.size() != sizeof(T)) throw std::runtime_error("Invalid scalar attribute size");
        T result; std::memcpy(&result,value->bytes.data(),sizeof(T)); return result;
    }
    template<class T>
    std::optional<std::vector<T>> readArray(std::string_view path, std::string_view name, DLDataType type,
                                           ovstage_ordinal_t ordinal) const
    {
        validateType<T>(type);
        auto value = readRaw(path,name,ordinal);
        if (!value) return std::nullopt;
        validateValue(*value,type,true);
        if (value->bytes.size() % sizeof(T)) throw std::runtime_error("Invalid array attribute size");
        std::vector<T> result(value->bytes.size()/sizeof(T));
        if (!result.empty()) std::memcpy(result.data(),value->bytes.data(),value->bytes.size());
        return result;
    }
    std::vector<std::string> findPrims(const std::vector<std::string_view>& types,
                                     const std::vector<std::string_view>& apis, ovstage_ordinal_t ordinal) const
    {
        checkOrdinal(ordinal);
        std::vector<std::string> paths, result;
        if (!m_instance->stage->QueryPrimPathsByAttributeNames({"usd-prim-type"},paths)) fail("enumerate prims");
        for (const auto& path : paths)
        {
            if (!types.empty())
            {
                auto exact = readValue<uint64_t>(path,"usd-prim-type",{kDLUInt,64,1},ordinal);
                auto ancestors = readArray<uint64_t>(path,"usd-ancestor-types",{kDLUInt,64,1},ordinal);
                bool match = false;
                for (auto type : types)
                {
                    const auto id = token(type);
                    match |= (exact && *exact == id) || (ancestors && std::find(ancestors->begin(),ancestors->end(),id) != ancestors->end());
                }
                if (!match) continue;
            }
            if (!apis.empty())
            {
                auto schemas = readArray<uint64_t>(path,"usd-schemas",{kDLUInt,64,1},ordinal);
                std::vector<std::string> names;
                if (schemas && !m_instance->stage->ResolveTokenStrings(*schemas,names)) fail("resolve schemas");
                bool match = true;
                for (auto api : apis)
                    match &= std::any_of(names.begin(),names.end(),[&](const std::string& name) {
                        return name == api || (name.size() > api.size() && name.compare(0,api.size(),api) == 0 && name[api.size()] == ':');
                    });
                if (!match) continue;
            }
            result.push_back(path);
        }
        checkFrame();
        return result;
    }
    // Convert existing animation CPU columns into one owned Kit edit batch.
    // No provider pointer, asynchronous tensor storage or local write ordinal escapes.
    void write(const Query& query, const ovstage_attribute_write_t* attributes, size_t count,
               ovstage_ordinal_t ordinal) const
    {
        validate(query,ordinal);
        if (!count || query.paths.empty()) return;
        if (!attributes) throw std::invalid_argument("Missing attribute descriptors");
        std::vector<Value> edits;
        for (size_t a=0; a<count; ++a)
        {
            const auto& d = attributes[a].data;
            if (!d.tensors || d.managed_tensors || !d.tensor_count || d.cuda_sync.stream || d.cuda_sync.wait_event)
                throw std::invalid_argument("Animation writes require borrowed CPU tensors");
            const auto name = tokenString(attributes[a].attribute.token);
            const size_t rows = d.count ? d.count : query.paths.size();
            if (rows > query.paths.size() || (d.mask && d.index_map)) throw std::invalid_argument("Invalid attribute row selection");
            for (size_t i=0; i<rows; ++i)
            {
                if (d.mask && !(d.mask[i/64] & (uint64_t(1) << (i%64)))) continue;
                const size_t row = d.index_map ? d.index_map[i] : i;
                const size_t ti = d.is_array && d.tensor_count > 1 ? row : 0;
                if (ti >= d.tensor_count || (!d.is_array && d.tensor_count != 1)) throw std::invalid_argument("Invalid tensor row");
                const auto& t = d.tensors[ti];
                if (t.device.device_type != kDLCPU || t.ndim != 1 || !t.shape || t.shape[0] < 0 ||
                    !t.dtype.bits || t.dtype.bits%8 || !t.dtype.lanes || (t.strides && t.strides[0] < 0))
                    throw std::invalid_argument("Unsupported animation tensor layout");
                size_t n = 1, start = row;
                if (d.is_array)
                {
                    start = 0; n = size_t(t.shape[0]);
                    if (d.tensor_count == 1)
                    {
                        size_t sourceRows = rows;
                        if (d.index_map) sourceRows = size_t(*std::max_element(d.index_map,d.index_map+rows))+1;
                        if (!sourceRows || n%sourceRows) throw std::invalid_argument("Invalid packed array rows");
                        n /= sourceRows; start = row*n;
                    }
                }
                if (start > size_t(t.shape[0]) || n > size_t(t.shape[0])-start || (n && !t.data))
                    throw std::invalid_argument("Invalid tensor size");
                const size_t size = size_t(t.dtype.bits/8)*t.dtype.lanes;
                const size_t stride = t.strides ? size_t(t.strides[0]) : 1;
                const auto limit = std::numeric_limits<size_t>::max();
                if (n > limit/size || stride > limit/size || t.byte_offset > limit ||
                    (n && stride && start+n-1 > (limit-size_t(t.byte_offset))/(stride*size)))
                    throw std::overflow_error("Tensor byte offset overflow");
                Value edit; edit.primPath=query.paths[i]; edit.attribute=name;
                edit.type={t.dtype.code,t.dtype.bits,t.dtype.lanes,d.is_array,semantic(d.semantic)};
                edit.bytes.resize(n*size);
                for (size_t j=0;j<n;++j)
                    std::memcpy(edit.bytes.data()+j*size,static_cast<const uint8_t*>(t.data)+t.byte_offset+(start+j)*stride*size,size);
                edits.push_back(std::move(edit));
            }
        }
        m_instance->edits.insert(m_instance->edits.end(),std::make_move_iterator(edits.begin()),std::make_move_iterator(edits.end()));
    }
    void erase(const Query& query, const std::vector<ovx_string_or_token_t>& names, ovstage_ordinal_t ordinal) const
    {
        validate(query,ordinal);
        std::vector<Value> edits;
        for (const auto& path : query.paths) for (auto name : names)
        {
            Value edit; edit.kind=omni::runtime::core::StageEditKind::eErase;
            edit.primPath=path; edit.attribute=tokenString(name.token); edits.push_back(std::move(edit));
        }
        m_instance->edits.insert(m_instance->edits.end(),std::make_move_iterator(edits.begin()),std::make_move_iterator(edits.end()));
    }
    template<class T>
    void writeValue(std::string_view path, std::string_view name, const T& value, DLDataType type,
                    ovstage_ordinal_t ordinal, ovstage_attribute_semantic_t meaning=OVSTAGE_SEMANTIC_NONE) const
    {
        validateType<T>(type); int64_t one=1;
        DLTensor tensor{const_cast<T*>(&value),{kDLCPU,0},1,type,&one,nullptr,0};
        ovstage_attribute_write_t descriptor{}; descriptor.attribute.token=token(name);
        descriptor.data.tensors=&tensor; descriptor.data.tensor_count=1; descriptor.data.semantic=meaning;
        write(paths({path}),&descriptor,1,ordinal);
    }
    void checkFrame() const
    {
        if (!m_instance || !m_instance->stage || !m_instance->stage->IsReadReady() ||
            m_instance->stage->GetGeneration()!=m_instance->generation ||
            m_instance->stage->GetSealedOrdinal()!=m_instance->ordinal)
            throw std::runtime_error("Kit ovstage generation/frame is unavailable; retry on the next update");
    }
private:
    bool hasPendingAncestor(std::string_view path) const
    {
        auto affects = [&](const Value& edit) {
            return edit.attribute == "omni:xform" &&
                (edit.primPath == path || (path.size() > edit.primPath.size() &&
                 path.substr(0,edit.primPath.size()) == edit.primPath && path[edit.primPath.size()] == '/'));
        };
        for (const auto& edit : m_instance->edits) if (affects(edit)) return true;
        for (const auto& input : m_instance->inputs) if (affects(input.second)) return true;
        return false;
    }
    void checkOrdinal(ovstage_ordinal_t ordinal) const
    { checkFrame(); if (ordinal!=m_instance->ordinal) throw std::invalid_argument("Stage frame changed"); }
    void validate(const Query& query, ovstage_ordinal_t ordinal) const
    { checkOrdinal(ordinal); if (query.owner!=m_instance) throw std::invalid_argument("Query belongs to another core binding"); }
    [[noreturn]] void fail(const char* operation) const
    { throw std::runtime_error(std::string("Kit ovstage ")+operation+" failed: "+std::to_string(int(m_instance->stage->GetLastDiagnostic().status))); }
    template<class T> static void validateType(DLDataType type)
    {
        static_assert(std::is_trivially_copyable_v<T>);
        if (!type.bits || type.bits%8 || !type.lanes || size_t(type.bits/8)*type.lanes!=sizeof(T))
            throw std::invalid_argument("Attribute type does not match the C++ value");
    }
    static void validateValue(const Value& value, DLDataType type, bool array)
    {
        if (value.type.code!=type.code || value.type.bits!=type.bits || value.type.lanes!=type.lanes || value.type.isArray!=array)
            throw std::runtime_error("Kit ovstage attribute has an incompatible type");
    }
    static Semantic semantic(ovstage_attribute_semantic_t value)
    {
        switch (value)
        {
#define MAP(a,b) case OVSTAGE_SEMANTIC_##a: return Semantic::b
            MAP(NONE,eNone); MAP(ASSET_PATH_ID,eAssetString); MAP(TOKEN_ID,eTokenId);
            MAP(PATH_EXPRESSION_STRING,ePathExpressionString); MAP(RELATIONSHIP_PATH_ID,eRelationshipPathId);
            MAP(POINT,ePoint); MAP(VECTOR,eVector); MAP(NORMAL,eNormal); MAP(COLOR,eColor);
            MAP(QUATERNION,eQuaternion); MAP(MATRIX,eMatrix); MAP(TEXTURE_COORDINATE,eTextureCoordinate);
            MAP(CONNECTION_PATH_ID,eConnectionPathId); MAP(STRING,eString); MAP(TIME_CODE,eTimeCode); MAP(FRAME,eFrame);
#undef MAP
            default: throw std::invalid_argument("Unknown attribute semantic");
        }
    }
    StageAccess* m_instance;
};
} // namespace omni::anim::shared::stage
