-- Use folder name to build extension name and tag.
local ext = get_current_extension_info()

-- That will also link whole current "target" folder into as extension target folder:
project_ext (ext)
    repo_build.prebuild_link { "docs", ext.target_dir.."/docs" }
    repo_build.prebuild_link { "data", ext.target_dir.."/data" }
    repo_build.prebuild_link { "icons", ext.target_dir.."/icons" }
    repo_build.prebuild_link { "omni/kit", ext.target_dir.."/omni/kit" }

    repo_build.prebuild_link {
        { "%{target_deps}/omniverse.deepsearch.helper/omni/deepsearch/helper", ext.target_dir.."/omni/deepsearch/helper" },
        { "%{target_deps}/omni.search_grammar/omni/search_grammar", ext.target_dir.."/omni/search_grammar" },
    }
