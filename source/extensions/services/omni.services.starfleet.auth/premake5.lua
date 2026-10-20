-- Use folder name to build extension name and tag. Version is specified explicitly.
local ext = get_current_extension_info()

project_ext (ext)

-- Set up the location names for the plugin
local deps_omniverse_auth_client = "%{target_deps}/pip_nv_prebundle/omniverse_auth_client/omni/auth"
local deps_idl = "%{target_deps}/pip_nv_prebundle/omniverse_idl/idl"

repo_build.prebuild_link {
    { "omni", ext.target_dir.."/omni" },
    { "data", ext.target_dir.."/data" },
    { "docs", ext.target_dir.."/docs" },
    { deps_omniverse_auth_client, ext.target_dir.."/omniverse_auth" },
    { deps_idl, ext.target_dir.."/idl" },
}
