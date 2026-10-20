-- Build file for the Ramp extension.
local ext = get_current_extension_info()

-- Put this project into the simulation IDE group
ext.group = "extensions"

project_ext( ext )

-- Set up the location names for the plugin
local namespace = "omni/ramp"
local python_source_path = "python"
local plugin_source_path = "plugins"
local docs_source_path = "docs"

-- This function binds the runtime and settings to be compatiable with kit. This means
-- that even though our debug builds
function setRuntimeToBeKitCompatible()
    if kit_sdk_config == "debug" then
        runtime "Debug"
        defines{ "_DEBUG"}
    elseif kit_sdk_config == "release" then
        runtime "Release"
        defines{ "NDEBUG"}
    else
        filter { "configurations:debug" }
            runtime "Debug"
            defines{ "_DEBUG"}
        filter  { "configurations:release" }
            runtime "Release"
            defines{ "NDEBUG"}
        filter {}
    end
end

-- ----------------------------------------------------------------------
-- The main plugin is what implements the compute graph functionality
project_ext_plugin( ext, "omni.ramp.plugin" )
    -- Kit 111: omni/usd/UsdContext.h includes omni/fabric headers, which live under kit/dev/fabric/include.
    includedirs { "%{kit_dev_dir}/fabric/include" }

    -- Sort out the files into rough correspondence with the file tree
    add_files("impl", plugin_source_path)
    add_files("config", "config")
    add_files("iface", "%{root}/include/"..namespace)
    add_files("docs", docs_source_path)

    -- Standard way of building in Omniverse
    exceptionhandling "On"
    rtti "On"
    language "C++"

    setRuntimeToBeKitCompatible()

    -- To speed up USD include compiling
    removeflags { "NoPCH" } -- to speed up USD includes compiling

    -- Begin USD support
    extra_usd_libs = {
        "pcp",
        "trace",
        "usdUtils",
        "usdSkel"
    }

    add_usd(extra_usd_libs)

    filter { "system:windows" }
        disablewarnings {
            "4005", -- (warning C4005: NOMINMAX macro redefinition)
        }
    filter {}
    -- End USD support

    -- Common include dependencies
    includedirs {
        target_deps.."/rtx_plugins/include",
        plugin_source_path,
        "%{root}/_build/%{platform_target}/%{config}/kit/dev/include",
        "%{root}/source/pch"
    }

    externalincludedirs { target_deps.."/gsl/include" }

    -- Common library locations
    libdirs {
        extsbuild_dir.."/omni.usd.core/bin",
        "%{root}/_build/%{platform_target}/%{config}/kit/plugins",
    }

    -- Linux-specific compile information
    filter { "system:linux" }
        exceptionhandling "On"
        removeflags { "FatalCompileWarnings", "UndefinedIdentifiers" }
        includedirs { target_deps.."/python/include/python3.10" }
    filter {}

    -- Specifies the external libraries required by the nodes
    links {"omni.usd"}

    repo_build.prebuild_link {
        { "data", ext.target_dir.."/data" },
        { "docs", ext.target_dir.."/docs" },
    }

-- ----------------------------------------------------------------------
-- Python support and scripts
project_ext_bindings {
    ext = ext,
    project_name = "omni.ramp.python",
    module = "_omni_ramp",
    src = "bindings",
    target_subdir = namespace.."/bindings"
}

    -- All Python script and documentation files are part of this project
    add_files("bindings", "bindings/*.*")
    add_files("python", "*.py")
    add_files("python/scripts", "python/scripts/**.py")

    -- Structure the Python script directories to make it convenient for tests.
    -- The scripts have to be copied so that the ".." path goes to the correct place when looking for data files.
    -- It also allows the OGN generated test files to be automatically picked up from the test directory.
    repo_build.prebuild_link {
        { "python/scripts", ext.target_dir.."/"..namespace.."/scripts" },
        { "python/tests", ext.target_dir.."/"..namespace.."/tests" },
    }

    repo_build.prebuild_copy {
        { "python/*.py", ext.target_dir.."/"..namespace},
    }

    -- Common include dependencies
    includedirs { plugin_source_path }
