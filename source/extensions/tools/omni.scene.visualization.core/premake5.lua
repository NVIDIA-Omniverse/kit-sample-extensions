-- Build file for the scene visualization extension.
local ext = get_current_extension_info()

-- Helper variable containing standard configuration information for the OGN files in this project
local ogn = get_ogn_project_information(ext, "omni/scene/visualization/core", "TypeConfigurationLinAlg.json")

-- Put this project into the simulation IDE group
ext.group = "extensions"

project_ext( ext )

-- Set up the location names for the plugin
local namespace = "omni/scene/visualization/core"

-- ----------------------------------------------------------------------
-- The main plugin is what implements the compute graph functionality
project_ext_plugin( ext, ogn.plugin_project )
    -- Preserve particle-system root warning policy; cleanup is tracked separately.
    removeflags { "FatalCompileWarnings" }
-- project_ext_plugin( ext, "scene.visualization.plugin" )

    -- Sort out the files into rough correspondence with the file tree
    add_files("impl", ogn.plugin_path)
    add_files("config", "config")
    add_files("iface", "%{root}/include/omni/scenevisualization")
    add_files("docs", ogn.docs_path)
    add_files("ogn", ogn.nodes_path)

    -- Add the standard dependencies all OGN projects have
    extra_usd_libs = {
        "trace",
        "usdGeom",
        "usdUtils"
    }
    add_ogn_dependencies_override(ogn, extra_usd_libs)

    filter { "system:windows" }
        disablewarnings {
            "4005", -- (warning C4005: NOMINMAX macro redefinition)
        }
    filter {}

    -- Standard way of building in Omniverse
    exceptionhandling "On"
    rtti "On"
    language "C++"

    -- Define the runtime to match the build configuration
    filter { "configurations:debug" }
        runtime "Debug"
    filter  { "configurations:release" }
        runtime "Release"
    filter {}

    -- To speed up USD include compiling
    removeflags { "NoPCH" } -- to speed up USD includes compiling

    -- Common include dependencies
    includedirs {
        target_deps.."/rtx_plugins/include",
        target_deps.."/usdrt/include",
        target_deps.."/omni_client_library/include",
        target_deps.."/pybind11/include",
        ogn.plugin_path,
        "%{root}/_build/%{platform_target}/%{config}/kit/dev/include",
        "%{root}/source/pch"
    }

    -- Common library locations
    libdirs {
        target_deps.."/usdrt/_build/%{platform_target}/%{config}",
        extsbuild_dir.."/omni.usd.core/bin",
        "%{root}/_build/%{platform_target}/%{config}/kit/plugins",
    }

    -- Linux-specific compile information
    filter { "system:linux" }
        exceptionhandling "On"
        removeflags { "FatalCompileWarnings", "UndefinedIdentifiers" }
    filter {}

    -- Specifies the external libraries required by the nodes
    links {"omni.usd"}

    -- Use the ovstage facade and runtime shipped by the selected Kit (Kit 111: the Fabric-backed usdrt
    -- provider is retired; usdrt.scenegraph is OVStage-backed).
    -- Kit PR 2404 moved the facade's include/ and bin/ into usdrt.scenegraph; Kits before it (the pinned kernel) have
    -- the facade library only in usdrt.scenegraph.ovstage/bin/. extsbuild_dir holds %{platform}/%{config} tokens, so
    -- neither folder can be tested when premake runs: both are listed, new first, and the compiler and linker take the
    -- first that has the file. A stale usdrt.scenegraph.ovstage in a reused tree is reached only where the new one lacks it.
    local kit_ovstage_dirs = { extsbuild_dir.."/usdrt.scenegraph", extsbuild_dir.."/usdrt.scenegraph.ovstage" }
    includedirs { kit_ovstage_dirs[1].."/include", kit_ovstage_dirs[2].."/include" }
    libdirs { kit_ovstage_dirs[1].."/bin", kit_ovstage_dirs[2].."/bin" }
    links { "usdrt.scenegraph.ovstage" }

    repo_build.prebuild_link {
        { "data", ext.target_dir.."/data" },
        { "docs", ext.target_dir.."/docs" },
    }

-- ----------------------------------------------------------------------
-- Break this out as a separate project to ensure the .ogn files are processed before their results are needed
project_ext_ogn( ext, ogn )

-- ----------------------------------------------------------------------
-- Python support and scripts
project_ext_bindings {
    ext = ext,
    project_name = ogn.python_project,
    module = ogn.bindings_module,
    src = ogn.bindings_path,
    target_subdir = ogn.bindings_target_path
}

    -- All Python script and documentation files are part of this project
    add_files("bindings", "bindings/*.*")
    add_files("python", "*.py")
    add_files("python/scripts", "python/scripts/**.py")

    -- Add the standard dependencies all OGN projects have
    add_ogn_dependencies_override(ogn)

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
    includedirs {
       ogn.plugin_path,
       "%{kit_sdk_bin_dir}/dev/fabric/include",
       "%{root}/_build/%{platform_target}/%{config}/kit/dev/include",
    }

    -- Common library locations
    libdirs {
        extsbuild_dir.."/omni.usd.core/bin",
        "%{root}/_build/%{platform_target}/%{config}/kit/plugins",
    }

    -- Specifies the external libraries required by the nodes
    links {"omni.usd"}

    -- TBB is needed for the binding target; point to the correct variant per config
    filter { "system:linux", "configurations:debug" }
        libdirs { target_deps.."/tbb-debug/lib" }
        links { "tbb_debug" }
    filter { "system:linux", "configurations:release" }
        libdirs { target_deps.."/tbb/lib" }
        links { "tbb" }
    filter {}
