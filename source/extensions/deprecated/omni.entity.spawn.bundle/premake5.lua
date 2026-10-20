local ext = get_current_extension_info()

repo_build.prebuild_link {
    {"data/", ext.target_dir.."/data"},
}
repo_build.prebuild_link { "docs", ext.target_dir.."/docs" }

project_ext( ext, { generate_ext_project=true })
