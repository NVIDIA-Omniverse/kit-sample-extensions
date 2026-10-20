local ext = get_current_extension_info()

local omni_client_library = "%{target_deps}/omni_client_library"

project_ext (ext)
    -- Link more folder to target folder.
    repo_build.prebuild_link { "docs", ext.target_dir.."/docs" }
    repo_build.prebuild_link { "data", ext.target_dir.."/data" }

-- Set up the location names for the plugin
local namespace = "omni/curve/manipulator"
local python_source_path = "python"
local plugin_source_path = "plugins"
local docs_source_path = "docs"

project_ext_plugin(ext, "omni.curve.manipulator.plugin")
    -- Preserve particle-system root warning policy; cleanup is tracked separately.
    removeflags { "FatalCompileWarnings" }
    local plugin_name = "omni.curve.manipulator"

    add_files("impl", "plugins/"..plugin_name)
    add_files("iface", "%{root}/include/omni/ext", "IExt.h")
    add_files("iface", "%{root}/include/omni/curvemanipulator", "ICurveManipulator.h")
    includedirs { "plugins/"..plugin_name }
    includedirs { omni_client_library.."/include" }

    defines { "SUPPORT_VP1=1" }

    -- Begin USD support
    extra_usd_libs = {
        "kind",
        "pcp",
        "usdGeom",
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

    staticruntime "Off"
    exceptionhandling "On"
    rtti "On"
    filter { "configurations:debug" }
        runtime "Debug"
    filter  { "configurations:release" }
        runtime "Release"
    filter {}
    includedirs {
        "include",
        target_deps.."/rtx_plugins/include"
    }

    externalincludedirs { target_deps.."/gsl/include" }

    libdirs {
        extsbuild_dir.."/omni.usd.core/bin",
        "%{root}/_build/%{platform_target}/%{config}/kit/plugins",
        target_deps.."/cuda/lib/x64",
    }
    links {
        "carb", "omni.usd"
    }

    filter { "system:linux" }
        exceptionhandling "On"
        removeflags { "UndefinedIdentifiers" }
        buildoptions { "-pthread" }
        links { "dl", "pthread" }
    filter {}

-- ----------------------------------------------------------------------
-- Python support and scripts
project_ext_bindings {
    ext = ext,
    project_name = "omni.curve.manipulator.python",
    module = "_omni_curve_manipulator",
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
    }

    repo_build.prebuild_link {
        { "python/tests", ext.target_dir.."/"..namespace.."/tests" },
    }

    repo_build.prebuild_copy {
        { "python/*.py", ext.target_dir.."/"..namespace},
    }

    -- Begin USD support
    add_usd(extra_usd_libs)
    -- End USD support

    -- Common include dependencies
    includedirs {
       plugin_source_path,
       "%{root}/_build/%{platform_target}/%{config}/kit/dev/include",
    }
