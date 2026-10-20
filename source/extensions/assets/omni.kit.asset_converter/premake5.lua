local ext = get_current_extension_info()


project_ext (ext)
    repo_build.prebuild_link { "data", ext.target_dir.."/data" }
    repo_build.prebuild_link { "docs", ext.target_dir.."/docs" }
    repo_build.prebuild_link { "omni", ext.target_dir.."/omni" }
    -- link include folder for dependent C++ extension
    repo_build.prebuild_link {
        {"%{root}/_build/target-deps/usd-convert-asset_%{config}/include", ext.target_dir.."/include"},

    }
    -- copy everything inside asset_converter_native_bindings
    repo_build.prebuild_copy (
        {
            { "%{root}/_build/target-deps/usd-convert-asset_%{config}/asset_converter_native_bindings/**", ext.target_dir.."/asset_converter_native_bindings" },
        }
    )

    -- copy import library for dependent C++ extensions. Required only for windows
    repo_build.prebuild_copy (
        {
            {"%{root}/_build/target-deps/usd-convert-asset_%{config}/lib/${lib_prefix}usd_convert_asset.lib", ext.target_dir.."/asset_converter_native_bindings/libs"},
        },
        "windows-x86_64"
    )

-- Kit 111 (Linux) workaround: FBX SDK allocator handlers with a 16-byte minimum alignment, until the pinned
-- usd-convert-asset installs them itself (usd-convert-asset-internal#6). Kit 111's Linux kit exports mimalloc,
-- whose 8-byte-aligned small blocks make FBX SDK 2020.3.7 silently drop animation keys. On Windows the converter
-- already sets its own handlers.
-- TODO: remove at the usd_convert_asset pin bump to the first 9.2.x with usd-convert-asset-internal#6.
if os.target() == "linux" then
    project_ext_plugin(ext, "omni.kit.asset_converter.fbx_allocator")
        -- The aarch64 converter package ships no FBX SDK.
        removeplatforms { "aarch64" }
        kind "SharedLib"
        language "C++"
        local src = "plugins/fbx_allocator_workaround"
        files { src.."/*.h", src.."/*.cpp" }
        -- Only the four FBX allocator setter declarations; the Autodesk SDK is not staged.
        includedirs { src, src.."/stub" }
        -- Link the converter package's own FBX SDK, and load that same copy at run time.
        libdirs { "%{root}/_build/target-deps/usd-convert-asset_%{config}/asset_converter_native_bindings/libs" }
        links { "fbxsdk" }
        linkoptions { "-Wl,-rpath,'$$ORIGIN/../asset_converter_native_bindings/libs'" }
end
