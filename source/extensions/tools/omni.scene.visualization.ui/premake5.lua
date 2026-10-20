local ext = get_current_extension_info()

project_ext (ext)

repo_build.prebuild_link {
    {"python/", ext.target_dir.."/omni/scene/visualization/ui"},
    { "data", ext.target_dir.."/data" },
    { "docs", ext.target_dir.."/docs" },
}
