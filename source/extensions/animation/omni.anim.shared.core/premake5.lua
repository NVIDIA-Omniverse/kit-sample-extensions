-- ----------------------------------------------------------------------
-- Set up standard extension information
local ext = get_current_extension_info()

-- change name of plugins here
local namespace = "omni/anim/shared/core"

-- ----------------------------------------------------------------------
-- Set up standard OGN information
local ogn = get_ogn_project_information(ext, namespace)

-- Grouping also tells the name of the premake file that calls this one - $TOP/premake5-{ext.group}.lua
ext.group = "animation"

repo_build.prebuild_link {
    { "data", ext.target_dir.."/data" },
    { "docs", ext.target_dir.."/docs" },

}

-- Set up common project variables
project_ext( ext )

----------------------------------------------------------------------
-- Create a project for processing the .ogn files to create the generated code.
project_ext_ogn( ext, ogn )

-- ----------------------------------------------------------------------
-- Python support and scripts for the Omnigraph example files.
-- There are no C++ bindings so a plain old project_ext() is good enough here.
project_ext( ext, { generate_ext_project=true } )

    -- All Python script and documentation files are part of this project
    add_files("python", "*.py")
    add_files("python/scripts", "python/scripts/**.py")
    add_files("python/nodes", "python/nodes/**.py")

    -- Add the standard dependencies all OGN projects have
    add_ogn_dependencies(ogn, {"python/nodes"})

    -- Copy the init script directly into the build tree to avoid reload conflicts.
    repo_build.prebuild_copy {
        { "python/__init__.py", ogn.python_target_path },
    }
    -- Linking directories allows them to hot reload when files are modified in the source tree
    -- Docs are linked to get the README into the extension window
    repo_build.prebuild_link {
        { "docs", ext.target_dir.."/docs" },
        { "data", ext.target_dir.."/data" },
        { "python/scripts", ext.target_dir.."/"..namespace.."/scripts" },
        { "python/nodes", ext.target_dir.."/"..namespace.."/nodes" },
        { "python/tests", ext.target_dir.."/"..namespace.."/tests" },
    }

    -- Common include dependencies
    includedirs {
        target_deps.."/rtx_plugins/include",
    }

-- ----------------------------------------------------------------------
-- Define the plugin project, which contains all of the C++ code
project_ext_plugin( ext, ogn.plugin_project )
    cppdialect "c++17"
    includedirs {
        "include",
        target_deps.."/rtx_plugins/include",
        target_deps.."/omni_client_library/include",
        target_deps.."/pybind11/include",
        target_deps.."/python/include",
    }
    libdirs { extsbuild_dir.."/omni.usd.core/bin" }

    filter { "system:linux" }
        removeflags { "FatalCompileWarnings", "UndefinedIdentifiers" }
        includedirs { "%{kit_sdk_bin_dir}/python/include" }

    filter { "system:windows" }
        libdirs { "%{target_deps}/tbb/lib/intel64/vc14" }
    filter {}

    -- ----------------------------------------------------------------------
    -- Add the files to the project, reorganizing to make them easier to find in the Visual Studio project
    add_files("ogn", ogn.nodes_path)
    add_files("impl", ogn.plugin_path)
    add_files("config", "config")
    add_files("docs", ogn.docs_path)

    -- ----------------------------------------------------------------------
    -- Set up all build dependencies required by the OGN generated code
    add_ogn_dependencies(ogn)
    extra_usd_libs = {"ar","vt", "gf", "pcp", "sdf", "arch", "usd", "tf", "trace", "usdUtils", "usdGeom", "usdSkel"}

--    -- Extension dependencies
--    dependson { "prebuild", "reflection.gen", "carb", "omni.gpucompute-*.plugin" }
--
   ----------------------------------------------------------------------
    -- Add dependent libraries to the extension link phase
--    links {"carb", "vt", "gf", "sdf", "arch", "usd", "tf", "usdUtils", "usdGeom", "usdSkel"}
    links { "omni.usd"}
    add_usd(extra_usd_libs)

    -- Use the ovstage facade and runtime shipped by the selected Kit.
    -- Kit PR 2404 moved the facade's include/ and bin/ into usdrt.scenegraph; Kits before it (the pinned kernel) have
    -- the facade library only in usdrt.scenegraph.ovstage/bin/. extsbuild_dir holds %{platform}/%{config} tokens, so
    -- neither folder can be tested when premake runs: both are listed, new first, and the compiler and linker take the
    -- first that has the file. A stale usdrt.scenegraph.ovstage in a reused tree is reached only where the new one lacks it.
    local kit_ovstage_dirs = { extsbuild_dir.."/usdrt.scenegraph", extsbuild_dir.."/usdrt.scenegraph.ovstage" }
    includedirs { kit_ovstage_dirs[1].."/include", kit_ovstage_dirs[2].."/include" }
    libdirs { kit_ovstage_dirs[1].."/bin", kit_ovstage_dirs[2].."/bin" }
    links { "usdrt.scenegraph.ovstage" }
    add_usd { "usdUtils" }


----------------------------------------------------------------------
-- Create a project for providing the Python interface to the extension
project_ext_bindings {
    ext = ext,
    project_name = ogn.python_project,
    module = ogn.bindings_module,
    src = ogn.bindings_path,
    target_subdir = ogn.bindings_target_path
}

    -- ----------------------------------------------------------------------
    -- Add the files to the project, reorganizing to make them easier to find in the Visual Studio project
    add_files("bindings", "bindings")
    add_files("python", "python/*.py")

    -- ----------------------------------------------------------------------
    -- Python bindings have OGN depdencies so set them up here.
    add_ogn_dependencies(ogn, {"python/nodes"})

    -- ----------------------------------------------------------------------
    -- Copy the init script directly into the build tree to avoid reload conflicts.
    repo_build.prebuild_copy {
        { "python/__init__.py", ogn.python_target_path },
    }
