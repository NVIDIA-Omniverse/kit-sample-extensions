import os
import re
from typing import Dict, List, Tuple, Union

import omni.client
import omni.usd
from pxr import Sdf

from .builtin_importer import BuiltinImporter
from .builtin_options_builder import BuiltinImporterOptionsBuilder
from .utils import Utils

__all__ = ["AbstractImporterDelegate", "BuiltInImporterDelegate"]


class AbstractImporterDelegate:
    """
    AbstractImporterDelegate is abstract class for extending
    external importers into asset_importer framework.
    """

    @property
    def name(self) -> str:
        raise NotImplemented("name must be implemented.")

    @property
    def filter_regexes(self) -> List[str]:
        """List of regex filters of this importer supported.
        It's provided as a list because it's possible that the importer
        will support multiple formats and share the same options list.

        Args:
            None

        Return:
            List of regex strings.
        """
        raise NotImplemented("filter_regex must be implemented.")

    @property
    def filter_descriptions(self) -> List[str]:
        """List of descriptions for each regex filter. It will be
        used for filter description in the file picker.

        Args:
            None

        Return:
            List of regex descriptions.
        """
        raise NotImplemented("filter_description must be implemented.")

    @property
    def priority(self) -> int:
        """Priority of this importer when multiple importers support the same format.
        Higher values = higher priority (selected by default).
        Default is 0.

        Returns:
            int: Priority value (higher = more preferred)
        """
        return 0

    def build_options(self, paths: List[str]) -> None:
        """Options pane builder for file picker after paths are selected.
        It will only include those paths that are supported by this importer
        filtered with regex filters.

        Args:
            paths (List[str]): The list of selected paths from file picker.
        """
        raise NotImplemented("build_options must be implemented.")

    async def convert_assets(self, paths: List[str], **kargs) -> Dict[str, Union[str, None]]:
        """The real worker to convert assets.
        It will only include those paths that are supported by this importer
        filtered with regex filters.

        Args:
            paths (List[str]): The list of selected paths from file picker.
            **kwargs: Optional arguments. Following args are supported currently:
                add_reference: If it will be added into stage after convert.

        Returns:
            Dict[str, Union[str, None]]: The key is the asset path to be converted, and
            the value is the target path or stage ID within UsdStageCache that this asset converted to.
            If value is None, it means it's failed to be converted.
        """
        raise NotImplemented("convert_assets must be implemented.")

    async def added_reference(self, assets: Dict[str, Tuple[str, Sdf.Path]]):
        """The post process to assets that are imported to current stage.
        It will only be called if it's imported from menu `File -> Import`.

        Args:
            asset_pair: The dict of all assets that successfully imported and added as references. The key is the original asset path to be converted, and value is a tuple, of which the first element is the target path this asset is converted to, and the second one is prim path that the converted USD is added as reference.
        """
        pass

    def is_supported_format(self, path: str) -> bool:
        """If the asset is supported by this importer."""
        # remove checkpoint if any
        url = omni.client.break_url(path)
        if not url:
            return False

        matched = False
        for filter_regex in self.filter_regexes:
            regex = re.compile(filter_regex, re.IGNORECASE)
            if regex.match(url.path):
                matched = True
                break

        if not matched:
            return False

        # Utils.is_folder issues a blocking omni.client.stat call, so it's only checked once
        # a cheap regex match is found (e.g. drag/drop accept callbacks run on every hover).
        if Utils.is_folder(path):
            return False

        return True

    def supports_usd_stage_cache(self):
        """Whether the importer can write to UsdStageCache for us to retrieve data from"""
        # defaults to false and individual importer can overwrite this function if it's supported
        return False

    def show_destination_frame(self):
        """Whether the option panel show destination frame"""
        # defaults to true and individual importer can overwrite this function if it's supported
        return True

    def show_scene_optimizer_config_frame(self):
        """Whether the option panel show scene optimizer config frame"""
        # defaults to false and individual importer can overwrite this function if it's supported
        return False


class BuiltInImporterDelegate(AbstractImporterDelegate):
    def __init__(self, usd_context, builtin_importer: BuiltinImporter) -> None:
        super().__init__()
        self._options_builder = BuiltinImporterOptionsBuilder(usd_context)
        self._builtin_importer = builtin_importer
        self._filter_regexes = [
            ".*\\.fbx$",
            ".*\\.obj$",
            "(.*\\.gltf$)|(.*\\.glb$)",
            ".*\\.lxo$",
            ".*\\.md5$",
            ".*\\.stl$",
            ".*\\.bvh$",
            ".*\\.ply$",
        ]
        self._filter_descriptions = [
            "FBX Files (*.fbx)",
            "OBJ Files (*.obj)",
            "glTF Files (*.gltf, *.glb)",
            "LXO Files (*.lxo)",
            "MD5 Files (*.md5)",
            "STL Files (*.stl)",
            "BVH Files (*.bvh)",
            "PLY Files (*.ply)",
        ]

    def destroy(self):
        self._builtin_importer = None
        self._options_builder.destroy()
        self._options_builder = None

    def set_default_target_folder(self, folder: str):
        self._options_builder.set_default_target_folder(folder)

    @property
    def name(self) -> str:
        return "Asset Importer"

    @property
    def filter_regexes(self) -> List[str]:
        return self._filter_regexes

    @property
    def filter_descriptions(self) -> List[str]:
        return self._filter_descriptions

    def build_options(self, paths: List[str]) -> None:
        self._options_builder.build_pane(paths)

    async def convert_assets(self, paths: List[str], **kargs) -> Dict[str, Union[str, None]]:
        export_folder = kargs["export_folder"] if "export_folder" in kargs else ""
        export_file_name = kargs["export_file_name"] if "export_file_name" in kargs else ""
        export_file_format = kargs["export_file_format"] if "export_file_format" in kargs else ""
        context = self._options_builder.get_import_options()

        absolute_paths = []
        relative_paths = []
        for file_path in paths:
            if self.is_supported_format(file_path):
                absolute_paths.append(file_path)
                filename = os.path.basename(file_path)
                relative_paths.append(filename)

        converted_assets = await self._builtin_importer.create_import_task(
            True,
            absolute_paths,
            relative_paths,
            export_folder,
            export_file_name,
            export_file_format,
            context.asset_import_context,
        )

        return converted_assets

    async def added_reference(self, assets: Dict[str, Tuple[str, Sdf.Path]]):
        pass
