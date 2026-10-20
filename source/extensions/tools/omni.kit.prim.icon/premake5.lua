-- Use folder name to build extension name and tag. Version is specified explicitly.
local EXT_VERSION = "0.1.0"
local ext = get_current_extension_info(EXT_VERSION)

project_ext (ext)
    repo_build.prebuild_link { "docs", ext.target_dir.."/docs" }
    repo_build.prebuild_link { "data", ext.target_dir.."/data" }
    repo_build.prebuild_link { "icons", ext.target_dir.."/icons" }
    repo_build.prebuild_link { "prim_icon", ext.target_dir.."/omni/kit/prim/icon" }
