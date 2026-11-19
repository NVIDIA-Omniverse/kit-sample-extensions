local ext = get_current_extension_info()

-- Define app which will run tests. Needed for the schema extension otherwise the test will fail
local args = {}
if os.target() == "windows" then
    args = {"--/exts/omni.kit.test/testExtApp=%~dp0apps/omni.app.particle.system.kit" }
else
    args = {"--/exts/omni.kit.test/testExtApp=$SCRIPT_DIR/apps/omni.app.particle.system.kit" }
end
local extra_args = { test_args = {extra_test_args = args } }

-- Run generic utility project for the extension (defined in premake5-public.lua in Kit SDK)
project_ext(ext, extra_args)

repo_build.prebuild_link
{
    { "config", ext.target_dir.."/config" },
    { "docs", ext.target_dir.."/docs" },
    { "data", ext.target_dir.."/data" },
    { "generated", ext.target_dir.."/generated" },
    { "python", ext.target_dir.."/usd/schema/scene/visualization" },
}
