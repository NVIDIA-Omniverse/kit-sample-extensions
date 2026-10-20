local ext = get_current_extension_info()

project_ext (ext)

repo_build.prebuild_link {
    { "data", ext.target_dir.."/data" },
    { "docs", ext.target_dir.."/docs" },
}

function common_geojson_build_settings()
    extra_usd_libs = {
        "usdGeom",
        "usdShade",
        "usdUtils",
        "kind",
        "trace",
        "usdImaging",
        "js",
        "pcp",
    }
    add_usd(extra_usd_libs)

    includedirs {
        "include",
        "include/geojson_converter",
        "%{target_deps}/usd/%{cfg.buildcfg}/include",
        -- windows python include directory
        "%{target_deps}/python/include",
        -- linux python include directory
        "%{target_deps}/python/include/python3.12",
    }
    libdirs {
        "%{target_deps}/usd/%{cfg.buildcfg}/lib",
    }

    pchheader "UsdPCH.h"
    pchsource "include/geojson_converter/UsdPCH.cpp"
    files { "include/geojson_converter/UsdPCH.cpp" }

    filter { "system:windows" }
        disablewarnings { "4251", "4005", "4244", "4267", "4305" }
    filter { "system:linux" }
        removeflags { "FatalCompileWarnings", "UndefinedIdentifiers" }
        disablewarnings { "error=unused-variable" }
        buildoptions { "-fvisibility=hidden -D_FILE_OFFSET_BITS=64 -fexceptions -lstdc++fs -Wno-unused-function -pthread"} -- , "/std:c++17" }
        links { "pthread", "stdc++fs", "z" }
    filter {}
end

-- C++ Carbonite plugin
project_ext_plugin(ext, "omni.kit.converter.geojson.plugin")
    local plugin_name = "omni.kit.converter.geojson"

    kind "SharedLib"
    staticruntime "Off"
    exceptionhandling "On"
    rtti "On"
    language "C++"


    includedirs {
        "plugins/"..plugin_name,
        "%{target_deps}/nlohmann_json/source",
    }

    add_files("impl", "plugins/"..plugin_name)
    add_files("iface", "%{root}/include/omni/ext", "IExt.h")
    add_files("iface", "include/omni/kit/converter/geojson/**")

    common_geojson_build_settings()


-- Python Bindings for Carobnite Plugin
project_ext_bindings {
    ext = ext,
    project_name = "omni.kit.converter.geojson.python",
    module = "_geojson_converter",
    src = "bindings/python/omni.kit.converter.geojson",
    target_subdir = "omni/kit/converter/geojson"
}
    repo_build.prebuild_link {
        { "python/impl", ext.target_dir.."/omni/kit/converter/geojson/impl" },
        { "python/tests", ext.target_dir.."/omni/kit/converter/geojson/tests" },
    }

    common_geojson_build_settings()
