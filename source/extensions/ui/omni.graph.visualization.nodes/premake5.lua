-- Build file for the Omnigraph nodes visualization extension.
local ext = get_current_extension_info()

-- Helper variable containing standard configuration information for the OGN files in this project
local ogn = get_ogn_project_information(ext, "omni/graph/visualization/nodes")

-- Put this project into the omnigraph IDE group
ext.group = "omnigraph"

project_ext( ext )

-- ----------------------------------------------------------------------
-- Break this out as a separate project ensures the .ogn files are processed before their results are needed
project_ext_ogn( ext, ogn )

-- ----------------------------------------------------------------------
-- Python support and scripts for the plugin
project_ext( ext, { generate_ext_project=true})

    -- All Python script and documentation files are part of this project
    add_files("bindings", "bindings")
    add_files("python", "python/*.py")
    add_files("python/_impl", "python/_impl/**.py")
    add_files("python/tests", "python/tests/**.py")

    -- Add the standard dependencies all OGN projects have
    set_up_ogn_dependencies(ogn)
    link_ogn_python_directories(ogn, {"nodes"})

    -- Copy the init script directly into the build tree to avoid reload conflicts.
    repo_build.prebuild_copy {
        { "python/__init__.py", ogn.python_target_path },
    }

	-- docs and data files are linked to get information into the extension window
    repo_build.prebuild_link {
        { "data", ext.target_dir.."/data" },
        { "docs", ext.target_dir.."/docs" },
        { "config", ext.target_dir.."/config" },
        { "python/tests", ogn.python_tests_target_path },
        { "python/_impl", ogn.python_target_path.."/_impl" },
    }

    -- Common include dependencies
    includedirs {
        target_deps.."/rtx_plugins/include",
    }
