local ext = get_current_extension_info()
local ogn = get_ogn_project_information(ext, "omni/entity/spawn/core")

repo_build.prebuild_link {
    {"data/", ext.target_dir.."/data"},
}
repo_build.prebuild_link { "docs", ext.target_dir.."/docs" }

repo_build.prebuild_copy {
    { "python/*.py", ext.target_dir.."/omni/entity/spawn/core" },
}

repo_build.prebuild_link {
    { "python/scripts", ext.target_dir.."/omni/entity/spawn/core/scripts" },
    { "python/tests", ext.target_dir.."/omni/entity/spawn/core/tests" },
}

project_ext_ogn( ext, ogn )
project_ext( ext, { generate_ext_project=true })
add_ogn_dependencies(ogn, {"python/nodes"})
