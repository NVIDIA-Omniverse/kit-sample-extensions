local ext = get_current_extension_info()

-- Use the SDK extension-test harness; project applications are not shipped.
project_ext(ext)

repo_build.prebuild_link
{
    { "config", ext.target_dir.."/config" },
    { "docs", ext.target_dir.."/docs" },
    { "data", ext.target_dir.."/data" },
    { "generated", ext.target_dir.."/generated" },
    { "python", ext.target_dir.."/usd/schema/scene/visualization" },
}
