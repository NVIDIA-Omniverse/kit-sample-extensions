local ext = get_current_extension_info()

local targetDepsDir = root.."/_build/target-deps"

project_ext (ext)

repo_build.prebuild_link {
    { "data", ext.target_dir.."/data" },
    { "docs", ext.target_dir.."/docs" },
}

repo_build.prebuild_copy {
    { "python/__init__.py", ext.target_dir.."/omni/metrics/assembler/core/__init__.py" },
}

repo_build.prebuild_link {
    { "config", ext.target_dir.."/config" },
    { "python/scripts", ext.target_dir.."/omni/metrics/assembler/core/scripts" },
    { "python/tests", ext.target_dir.."/omni/metrics/assembler/core/tests" },
}

-- C++ Carbonite plugin
project_ext_plugin(ext, "omni.usd.metrics.assembler.plugin")
    local plugin_name = "omni.usd.metrics.assembler"

    cppdialect "C++17"

    add_files("impl", "plugins")
    add_files("iface", "include/omni/usd", "IMetricsAssembler.h")
    includedirs {
        "include",
        targetDepsDir.."/carb_sdk_plugins/include",
        targetDepsDir.."/usd_ext_physics/%{cfg.buildcfg}/include",
    }
    libdirs {
        targetDepsDir.."/usd_ext_physics/%{cfg.buildcfg}/lib",
    }
    -- add USD dependency
    additional_libs = {
        "js",
        "pcp",
        "usdGeom",
        "usdPhysics",
        "usdUtils"
    }
    add_usd(additional_libs)

    filter { "system:linux" }
        removeflags { "UndefinedIdentifiers" }
        buildoptions { "-pthread" }
        links { "dl", "pthread" }
    filter {}

-- Python Bindings for Carobnite Plugin
project_ext_bindings {
        ext = ext,
        project_name = "omni.usd.metrics.assembler.python",
        module = "_metricsAssembler",
        src = "bindings",
        target_subdir = "usd"
    }

    cppdialect "C++17"

    includedirs {
        "include",
        targetDepsDir.."/carb_sdk_plugins/include",
    }
    -- add USD dependency
    add_usd()

    filter { "system:linux" }
        removeflags { "UndefinedIdentifiers" }
        buildoptions { "-pthread" }
        links { "dl", "pthread" }
    filter {}


    targetdir (ext.target_dir.."/omni/metrics/assembler/core/bindings")
