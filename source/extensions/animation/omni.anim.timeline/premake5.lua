local ext = get_current_extension_info()

-- Helper variable containing standard configuration information for projects containing OGN files
local ogn = get_ogn_project_information(ext, "omni/anim/timeline")

-- Grouping also tells the name of the premake file that calls this one - $TOP/premake5-{ext.group}.lua
ext.group = "animation"

-- Set up common project variables
project_ext( ext )

repo_build.prebuild_link {
    { "data", ext.target_dir.."/data" },
    { "docs", ext.target_dir.."/docs" },
}

-- ----------------------------------------------------------------------
-- Define the project containing the C++ code
project_ext_plugin(ext, ogn.plugin_project)

    add_files("impl", ogn.plugin_path)
    add_files("ogn", ogn.nodes_path)

    -- Add the standard dependencies all OGN projects have
    add_ogn_dependencies(ogn)

    includedirs {
        "%{target_deps}/usd/%{config}/include",
        "%{kit_dev_dir}/fabric/include",
        "%{target_deps}/cuda/include",
        "%{target_deps}/usd_ext_animation/%{config}/include",
        "%{root}/source/extensions/animation/omni.anim.curve.core/plugins",
		"%{target_deps}/AnimX/%{config}/include",
        "%{target_deps}/gsl/include"
    }

    libdirs { "%{target_deps}/usd_ext_animation/%{config}/lib"}

    filter { "system:linux" }
        removeflags { "FatalCompileWarnings", "UndefinedIdentifiers" }
        includedirs { "%{kit_sdk_bin_dir}/python/include/python3.12" }
    filter { "system:windows" }
        libdirs { "%{target_deps}/tbb/lib/intel64/vc14" }
        disablewarnings {"4307"}
    filter {}

    links {"usd_ar", "usd_vt", "usd_gf", "usd_pcp", "usd_sdf", "usd_arch", "usd_usd", "usd_tf", "usd_usdUtils", "usd_usdGeom", "usd_usdSkel", extsbuild_dir.."/omni.usd.core/bin/omni.usd", "animationSchemaTools", "animationSchema"}

    -- TODO dll where?
    if os.target() == "windows" then
        -- Windows also builds with AnimX so copy that dll to a findable location
        repo_build.prebuild_copy {
            { "%{root}/_build/%{platform}/%{config}/plugins" },
        }
    end

-- ----------------------------------------------------------------------
-- Breaking this out as a separate project ensures the .ogn files are processed before their results are needed
project_ext_ogn( ext, ogn )


-- ----------------------------------------------------------------------
-- Python support and scripts for the timeline
project_ext_bindings {
    ext = ext,
    project_name = ogn.python_project,
    module = ogn.bindings_module,
    src = ogn.bindings_path,
    target_subdir = ogn.bindings_target_path
}
    filter { "system:windows" }
    disablewarnings {"4307"}
    filter {}

    -- All Python script and documentation files are part of this project
    add_files("bindings", "bindings/*.*")
    add_files("python", "python/*.py")
    add_files("python/tests", "python/tests/**.py")

    -- Add the standard dependencies all OGN projects have
    add_ogn_dependencies(ogn)

    -- Copy the init script directly into the build tree to avoid reload conflicts.
    repo_build.prebuild_copy {
        { "python/__init__.py", ogn.python_target_path },
    }
    -- Linking directories allows them to hot reload when files are modified in the source tree
    repo_build.prebuild_link {
        { "python/scripts", ogn.python_target_path.."/scripts" },
        { "python/tests", ogn.python_tests_target_path },
    }
