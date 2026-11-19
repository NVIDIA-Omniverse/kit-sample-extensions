
local ext = get_current_extension_info()

project_ext (ext)

-- The checker implementations live in the external usd_optimize package; this extension only ships
-- the Kit registration glue + docs + package icon/preview (data/).
repo_build.prebuild_link {
    {"python/", ext.target_dir.."/omni/scene/optimizer/validators"},
    { "docs", ext.target_dir.."/docs" },
    { "data", ext.target_dir.."/data" },
}
