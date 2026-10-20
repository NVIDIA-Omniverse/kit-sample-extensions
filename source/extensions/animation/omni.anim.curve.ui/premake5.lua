-- Set up standard extension information
local ext = get_current_extension_info()

repo_build.prebuild_link {
    { "python", ext.target_dir.."/omni/anim/curve/ui" },
    { "data", ext.target_dir.."/data" },
    { "docs", ext.target_dir.."/docs" },
    { "icons", ext.target_dir.."/icons" },
}

-- Generic utility project for extension. It automatically links "config" and "scripts" folders, copies licenses. Look in "premake5-public.lua" for details.
project_ext (ext)
