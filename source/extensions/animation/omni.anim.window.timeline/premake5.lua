-- Use folder name to build extension name and tag. 
local ext = get_current_extension_info()

local ext_id = "omni.anim.window.timeline"
local ext_folder = "%{root}/_build/$platform/$config/exts/"..ext_id
local ext_namespace = "omni/anim/window/timeline"
local ext_folder_namespace = ext_folder.."/"..ext_namespace

repo_build.prebuild_link {
    { "python/scripts", ext_folder_namespace.."/scripts" },
}
repo_build.prebuild_link {
    { "python/tests", ext_folder_namespace.."/tests" },
}
repo_build.prebuild_link { "data", ext.target_dir.."/data" }

repo_build.prebuild_copy {
    { "python/*.py", ext_folder_namespace },
}

repo_build.prebuild_link { "docs", ext.target_dir.."/docs" }

-- Generic utility project for extension. It automatically links "config" and "scripts" folders, copies licenses. Look in "premake5-public.lua" for details.
project_ext (ext)
