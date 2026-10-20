function add_ogn_dependencies_override(ogn, extra_usd_libs, python_node_directories)

    -- NOTE: THIS IS ESSENTIALLY A COPY OF WHAT IS IN set_up_ogn_dependencies
    -- so we can add usdGeom as an additional lib

    -- moved from add_usd method to individual plugins
    -- use dynamically linked runtime
    staticruntime("Off")
    filter { "configurations:debug" }
        runtime "Debug"
    filter  { "configurations:release" }
        runtime "Release"
    filter {}

    add_usd(extra_usd_libs)
    -- end OpenUSD

    -- Enact the dependencies extracted from the OGN configuration
    includedirs { ogn.includedirs }
    -- Kit 111 separates SDK external headers (including Fabric) from includedirs.
    externalincludedirs { ogn.externalincludedirs or {} }
    libdirs { ogn.libdirs }
    dependson { ogn.dependson }

    -- The API has some concurrent containers in use so tbb is needed
    filter { "system:linux" }
        disablewarnings { "undef", "deprecated-declarations" } -- must have for tbb :(
    filter { "configurations:debug" }
        links { "tbb_debug" }
    filter { "configurations:release" }
        links { "tbb" }
    filter {}

    if debuggingOGN() then
        print("OGN: Add Dependencies")
        print("     includedirs")
        printTable(ogn.includedirs, 2)
        print("     libdirs")
        printTable(ogn.libdirs, 2)
        print("     dependson")
        printTable(ogn.dependson, 2)
    end

    -- END COPY OF SET_UP_OGN_DEPENDENCIES

    set_ogn_cpp_flags(ogn)
    link_ogn_python_directories(ogn, python_node_directories)
end

