-- Use folder name to build extension name and tag. 
local ext = get_current_extension_info()

-- Generic dummy project for extension, adds all python/toml/lua/rst files to VS. Automatically links "config" and "scripts" folders.
project_ext (ext)
    -- Link more folder to target folder. 
    repo_build.prebuild_link { "docs", ext.target_dir.."/docs" }
    repo_build.prebuild_link { "data", ext.target_dir.."/data" }
    repo_build.prebuild_link { "omni", ext.target_dir.."/omni" }
