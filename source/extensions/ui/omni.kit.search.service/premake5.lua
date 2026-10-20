local ext = get_current_extension_info()

project_ext (ext)

-- Set up the location names for the plugin
local namespace = "omni/kit/search/service"

local deps_omniverse_discovery_py = "%{target_deps}/omniverse.discovery.client.py/omni/discovery"
local deps_idl_py = "%{target_deps}/idl.py/idl"
local deps_search_service = "%{target_deps}/omniverse.search.client.py/omni/search"

repo_build.prebuild_copy {
    { "python/*.py", ext.target_dir.."/"..namespace },
}
repo_build.prebuild_link {
    { "docs/", ext.target_dir.."/docs" },
    { "data/", ext.target_dir.."/data" },
    { "python/scripts", ext.target_dir.."/"..namespace.."/scripts" },
    { "python/tests", ext.target_dir.."/"..namespace.."/tests" },
    { deps_omniverse_discovery_py, ext.target_dir.."/omni/discovery" },
    { deps_search_service, ext.target_dir.."/omni/search" },
    { deps_idl_py, ext.target_dir.."/idl" },
}
