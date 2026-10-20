-- Use folder name to build extension name and tag. 
local ext = get_current_extension_info()

-- Generic utility project for extension. It automatically links "config" and "scripts" folders, copies licenses. Look in "premake5-public.lua" for details.
project_ext (ext)

repo_build.prebuild_link { "data", ext.target_dir.."/data" }
repo_build.prebuild_link { "docs", ext.target_dir.."/docs" }
repo_build.prebuild_link { "icons", ext.target_dir.."/icons" }
repo_build.prebuild_link { "source", ext.target_dir.."/omni/kit/window/quicksearch" }