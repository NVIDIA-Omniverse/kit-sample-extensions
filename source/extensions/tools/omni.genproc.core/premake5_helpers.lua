function commaficate(options)
    local result = "";
    local sep = "";
    for option in string.gmatch(options, "-%w+") do
        result = result..sep..tostring(option);
        sep = ","
    end
    return result;
end

function get_include_string(includes)
    cmdString =" ";
    for k, v in ipairs(includes) do
        cmdString = cmdString.." -I "..tostring(v);
    end
    return cmdString
end

carbSDKPath = "%{root}/_build/target-deps/carb_sdk_plugins"
carbSDKInclude = carbSDKPath.."/include"
nvccHostCompilerVS =  "%{root}/_build/host-deps/msvc/VC"
nvccPath = "%{root}/_build/target-deps/cuda/bin/nvcc"

function make_nvcc_command(nvccPath, nvccHostCompilerVS, nvccHostCompilerFlags, nvccFlags)
    if os.target() == "windows" then
        ext = ".obj"
        local compilerBindir = " --compiler-bindir "..nvccHostCompilerVS
        local buildString =  "\""..nvccPath.."\"".." "..nvccFlags..compilerBindir.." -Xcompiler="..nvccHostCompilerFlags.." -c -I "..carbSDKInclude.." %{get_include_string(cfg.includedirs)} %{file.abspath} -o %{cfg.objdir}/%{file.basename}"..ext
        buildmessage (buildString)
        buildcommands { buildString }
        buildoutputs { "%{cfg.objdir}/%{file.basename}"..ext }
    end
    if os.target() == "linux" then
        ext = ".o"
        local buildString =  "\""..nvccPath.."\" -std=c++14 "..nvccFlags.." -Xcompiler="..commaficate(nvccHostCompilerFlags).." -c -I "..carbSDKInclude.." %{get_include_string(cfg.includedirs)} %{file.abspath} -o %{cfg.objdir}/%{file.basename}"..ext
        buildcommands { "{MKDIR} %{cfg.objdir} ", buildString }
        buildoutputs { "%{cfg.objdir}/%{file.basename}"..ext }
    end
end
