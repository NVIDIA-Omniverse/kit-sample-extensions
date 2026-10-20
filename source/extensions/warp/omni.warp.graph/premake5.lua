local ext = get_current_extension_info()

local py_bin = root .. "/_build/target-deps/python/python "
local warp_dir = root .. "/source/extensions/warp"

project_ext(ext)

    repo_build.prebuild_link {
        { "data", ext.target_dir .. "/data" },
        { "docs", ext.target_dir .. "/docs" },
        { "omni", ext.target_dir .. "/omni" },
    }

    postbuildcommands {
        py_bin .. " " .. warp_dir .. "/generate_node_metadata.py --extension-path " .. ext.target_dir
    }
