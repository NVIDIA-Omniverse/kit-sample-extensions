local ext = get_current_extension_info()

project_ext (ext)
    -- Set up the location names for the plugin
    local namespace = "omni/kit/ngsearch"

    local deps_omniverse_discovery_py = "%{target_deps}/omniverse.discovery.client.py/omni/discovery"
    local deps_idl_py = "%{target_deps}/idl.py/idl"
    local deps_ngsearch_service = "%{target_deps}/omniverse.ngsearch.client.py/omni/ngsearch"
    repo_build.prebuild_copy {
        { "omni/", ext.target_dir.."/omni" },
    }
    repo_build.prebuild_link {
        { "data/", ext.target_dir.."/data" },
        { "docs/", ext.target_dir.."/docs" },
        { deps_omniverse_discovery_py, ext.target_dir.."/omni/discovery" },
        { deps_ngsearch_service, ext.target_dir.."/omni/ngsearch" },
        { deps_idl_py, ext.target_dir.."/idl" },
        -- { deps_ngsearch_pip, ext.target_dir.."/pip_prebundle" }
    }
