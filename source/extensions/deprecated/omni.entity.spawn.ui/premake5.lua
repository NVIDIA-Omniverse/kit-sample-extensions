local ext = get_current_extension_info()

repo_build.prebuild_link {
    {"data/", ext.target_dir.."/data"},
}
repo_build.prebuild_link { "docs", ext.target_dir.."/docs" }

repo_build.prebuild_copy {
    { "python/*.py", ext.target_dir.."/omni/entity/spawn/ui" },
}

repo_build.prebuild_link {
    { "python/scripts", ext.target_dir.."/omni/entity/spawn/ui/scripts" },
    { "python/tests", ext.target_dir.."/omni/entity/spawn/ui/tests" }
}

project_ext( ext, { generate_ext_project=true })
