local ext = get_current_extension_info()

project_ext (ext)
    repo_build.prebuild_link {
        { "data", ext.target_dir.."/data" },
        { "docs", ext.target_dir.."/docs" },
        { "icons", ext.target_dir.."/icons" },
        { "graphs", ext.target_dir.."/graphs" },
        { "omni", ext.target_dir.."/omni" },
    }