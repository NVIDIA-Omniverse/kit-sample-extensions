#pragma once

#ifdef _WIN32
#ifdef GeoJSON_LIB_BUILD
#define EXPORT_DECORATOR __declspec(dllexport)
#else
#define EXPORT_DECORATOR
#endif
#else
#define EXPORT_DECORATOR
#endif
#define GeoJSON_Converter_ABI EXPORT_DECORATOR

namespace geojson_converter_abi
{
int GeoJSON_Converter_ABI Convert_GeoJSON_ABI(const char* stage_url, const char* folder_name, bool recursive);

}
