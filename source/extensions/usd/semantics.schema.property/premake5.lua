-- Use folder name to build extension name and tag. Version is specified explicitly.
local ext = get_current_extension_info()

project_ext (ext)

repo_build.prebuild_link {
    { "python", ext.target_dir.."/semantics/schema/property" },
    { "data", ext.target_dir.."/data" },
    { "docs", ext.target_dir.."/docs" }
}
