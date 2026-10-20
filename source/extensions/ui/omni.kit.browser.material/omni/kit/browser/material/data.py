# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
import os
import re
from typing import Callable, List, Optional

import carb
import omni.client
import omni.kit.material.library
from omni.kit.browser.folder.core import FileSystemFile, FileSystemFolder
from pxr import Usd, UsdShade

from .usd_reader import read_usd_materials_async

THUMBNAIL_PATH = ".thumbs"
THUMBNAIL_SIZE = 256
THUMBNAIL_FULL_PATH = f"/{THUMBNAIL_PATH}/{THUMBNAIL_SIZE}x{THUMBNAIL_SIZE}"

MAX_RETRY_COUNT = 3

# Compiled once, and run once over the whole file rather than per line. Both matter: this runs on
# the event loop, and the per-line version cost 29.7 ms on a 1 MB mdl declaring 8,000 materials
# against 5.1 ms for a single pass - 75 ms against 15 ms at 20,000. A block that long is one the
# user sees, because neither progress nor Cancel can update while it runs.
_RE_MATERIAL_IN_MDL = re.compile(r"export\s+material\s+([^\s]+)\s*\(")


# TODO: Replace this function with omni.usd.get_subidentifier_from_mdl once it in kit release
async def get_subidentifier_from_mdl(mdl_file: str, on_complete_fn: Callable = None):
    if not mdl_file:
        carb.log_error(f"get_subidentifier_from_mdl: Failed to read file {mdl_file}")
        if on_complete_fn:
            on_complete_fn(None)
        return []

    result, _, content = await omni.client.read_file_async(mdl_file)
    if result != omni.client.Result.OK:
        carb.log_error(f"get_subidentifier_from_material: Failed to read file {mdl_file}")
        if on_complete_fn:
            on_complete_fn(None)
        return None

    mtl_list = []
    try:
        # get material names from MDL file
        mtl_list = _RE_MATERIAL_IN_MDL.findall(memoryview(content).tobytes().decode("utf-8"))
    except UnicodeDecodeError:
        carb.log_warn(f"Failed to parse {mdl_file}, try omni.kit.material.library.get_subidentifier_from_mdl")
        entries = await omni.kit.material.library.get_subidentifier_from_mdl(mdl_file=mdl_file)
        mtl_list = [entry.name for entry in entries]

    if on_complete_fn:
        on_complete_fn(mtl_list)
    return mtl_list


def _same_file(one: FileSystemFile, other: FileSystemFile) -> bool:
    """
    Do these two name one file? The base class's answer, whichever base class it is.

    _same_url is how a current omni.kit.browser.folder.core decides it - one local file has several
    spellings on Windows, and a cached copy spelled differently from the listing is the same file.
    An older one has no such method, and its own equals() compares urls as plain strings, so that is
    the fallback. Either way this follows the base class, which is the only thing that matters: the
    cache match indexes on one side and calls equals() on the other, and the two have to agree.
    """
    same_url = getattr(one, "_same_url", None)
    return same_url(other) if same_url is not None else one.url == other.url


class MaterialType:
    USD = "usd"
    MDL = "mdl"


class SubMaterial:
    """
    Represent a sub material.
    Args:
        name (str): Name of sub material
        thumbnail (Optional[str]): Thumbnail url of sub material
        url (str): Url of sub material. Default None to use name string.
    """

    def __init__(self, name: str, thumbnail: Optional[str] = None, url: str = None):
        self.name = name
        self.thumbnail = thumbnail
        self.url = url if url else name

    def equals(self, other: "SubMaterial"):
        """
        Compared exactly, because none of this is a filesystem path.

        A sub material's url is its identifier - a material name, or a prim path - and those are
        case-sensitive. Running them through the filesystem's rules folded two materials whose
        names differed only in case into one.

        The thumbnail is a file, but its spelling is not this comparison's business: it is derived
        from the file url and the material name, and the file was already matched on its own
        identity by MaterialFile.equals before any of this runs. What is left to notice is whether
        a thumbnail has appeared or gone.
        """
        return self.name == other.name and self.url == other.url and bool(self.thumbnail) == bool(other.thumbnail)

    def get_default_thumbnail_url(self, file_url: str) -> str:
        """
        Get default thumbnail url of this sub material.
        Args:
            file_url: Url tof material file this sub material belongs to.
        """
        file_name = file_url.split("/")[-1]
        return os.path.dirname(file_url) + THUMBNAIL_FULL_PATH + f"/{file_name}@{self.name}.png"

    def __repr__(self) -> str:
        return f"{self.url}:{self.thumbnail}"


class UsdSubMaterial(SubMaterial):
    """
    Represent a material prim in a usd.
    Args:
        url (str): Material prim path.
    Keyword args:
        default (bool): True if prim is the default prim in usd file. Otherwise False.
    """

    def __init__(self, url: str, default: bool = False, thumbnail: Optional[str] = None):
        self.default = default
        super().__init__(url.split("/")[-1], thumbnail=thumbnail, url=url)

    # Nothing to add: a prim path is an identifier, which is what SubMaterial.equals already
    # compares exactly.


class MaterialFile(FileSystemFile):
    """
    Represent a material file object.
    Args:
        url (str): Url of material file.
        sub_materials (Optional[List[UsdSubMaterial]]): Material prims in the file. None means this material file is a single material, otherwise muilti materials in the file.
    """

    def __init__(self, url: str, sub_materials: Optional[List[UsdSubMaterial]] = None):
        super().__init__(url)
        if url.lower().endswith(".mdl"):
            self.type = MaterialType.MDL
        else:
            self.type = MaterialType.USD

        self.sub_materials = sub_materials

    @property
    def _item_count(self) -> int:
        """
        Overridden. One item per material in the file.

        A .mdl or .usd can carry many materials, and the browser shows each one, so the file count
        alone understates what a scan is producing. Files with no sub materials are a single
        material named after the file, hence the one.
        """
        return len(self.sub_materials) if self.sub_materials else 1

    def equals(self, other: "MaterialFile") -> bool:
        """Determines if material file objects are equal by comparing file URL, sub materials, and thumbnail value.

        Args:
            other (MaterialFile): Material file object to compare against.

        Returns:
            bool: True if material files are equal; otherwise False.
        """
        if self.sub_materials or other.sub_materials:
            # The sub materials carry the thumbnails in this case, so the file's own is not
            # compared - which is why this cannot simply defer to the base class.
            if not _same_file(self, other):
                return False
            if not self.sub_materials or not other.sub_materials:
                return False
            if len(self.sub_materials) != len(other.sub_materials):
                return False
            self.sub_materials.sort(key=lambda item: item.name)
            other.sub_materials.sort(key=lambda item: item.name)
            return all(mine.equals(theirs) for mine, theirs in zip(self.sub_materials, other.sub_materials))
        # No sub materials on either side: url and thumbnail, which is exactly the base class.
        return super().equals(other)

    def set_thumbnail(self, thumbnail_url: str) -> bool:
        """Check and set thumbnail.

        If sub materials exist, determine the sub material based on a matching thumbnail name pattern and update its thumbnail value; otherwise, delegate to the parent implementation.

        Args:
            thumbnail_url (str): Url of thumbnail.

        Returns:
            bool: True if the thumbnail belongs to this file; otherwise False.
        """
        if self.sub_materials:
            thumbnail_name = thumbnail_url.split("/")[-1][:-4]
            # Check if thumbnail of sub materials
            # In format: {file_name}.{material.name}
            for material in self.sub_materials:
                file_name = self.url.split("/")[-1]
                expected_name = f"{file_name}@{material.name}"
                if thumbnail_name == expected_name:
                    material.thumbnail = thumbnail_url
                    return True
            else:
                return False
        else:
            return super().set_thumbnail(thumbnail_url)


class MaterialFolder(FileSystemFolder):
    """
    Represent a material folder.
    Keyword args:
        on_sub_materials_loaded_fn: Function called when multi sub materials load comppleted. Function signure:
            void on_sub_materials_loaded_fn(folder: MaterialFolder)

    Other args and keyword args, please refre to "FileSystemFolder"
    """

    def __init__(self, *args, **kwargs):
        self.sub_materials_count: int = 0
        self.sub_materials_loaded: bool = False
        super().__init__(*args, **kwargs)

    def destroy(self) -> None:
        super().destroy()

    @property
    def file_item_count(self) -> int:
        count = 0
        for file in self.files:
            if hasattr(file, "sub_materials") and file.sub_materials:
                count += len(file.sub_materials)
            else:
                count += 1
        return count

    def create_folder_object(self, *args, **kwargs) -> FileSystemFolder:
        """
        Overridden. Create folder object when a sub folder found
        """
        return MaterialFolder(*args, **kwargs)

    def create_file_object(self, url: str) -> Optional[MaterialFile]:
        """
        Overridden. Create file object.
        """
        file = MaterialFile(url)
        return file

    async def _on_file_found_async(self, url: str) -> Optional[MaterialFile]:
        file = await super()._on_file_found_async(url)
        if file:
            if await self._load_sub_material_async(file):
                return file
            else:
                return None
        return file

    async def _load_sub_material_async(self, material_file: MaterialFile) -> bool:
        retry_count = 0
        while retry_count <= MAX_RETRY_COUNT:
            if retry_count:
                carb.log_info(f"[{material_file.url}] Retry #{retry_count}")
            if material_file.type == MaterialType.MDL:
                if not await self._load_mdl_sub_materials_async(material_file, retry_count=retry_count):
                    retry_count += 1
                    await asyncio.sleep(0.5)
                else:
                    break
            else:
                return await self._load_usd_sub_materials_async(material_file)
        else:
            carb.log_error(
                f"Timeout {self._timeout} seconds when reading subidendifiers from {material_file.url}. Please check your network and connection to the url. Otherwise increase the timeout."
            )
            self.has_timeout = True
        return True

    def _create_usd_material_file_object(self, url: str) -> Optional[MaterialFile]:  # pragma: no cover - never called
        # usd files
        stage = Usd.Stage.Open(url)
        if stage:
            if stage.HasDefaultPrim():
                default_prim = stage.GetDefaultPrim()
            else:
                default_prim = None
            material_prims = []
            for prim in stage.TraverseAll():
                if prim.IsA(UsdShade.Material):
                    default = True if default_prim and prim == default_prim else False
                    material_prims.append(UsdSubMaterial(prim.GetPath().pathString, default=default))
            if not material_prims:
                # Invalid since No materials in usd file
                return None
            else:
                # Materials in usd
                return MaterialFile(url, sub_materials=material_prims)
        else:
            return None

    async def _load_mdl_sub_materials_async(self, material_file: MaterialFile, retry_count=0) -> bool:
        try:
            # OM-60914: Sometimes there maybe invalid utf-8 chars in mdl file
            # As a result, get_subidentifier_from_mdl cannot parse the file
            # Use omni.kit.material.library.get_subidentifier_from_mdl instead but it is slower first time
            subids = await asyncio.wait_for(
                get_subidentifier_from_mdl(material_file.url), timeout=self._timeout * (retry_count + 1)
            )
        except asyncio.TimeoutError:
            subids = None
            return False
        except asyncio.CancelledError:
            # Re-raise: returning False reports "could not read this file", which the caller
            # answers with a retry, so a cancelled scan would sleep and try again instead of
            # unwinding. Cancellation is caught only to release something.
            subids = None
            raise
        if subids is None:
            return False
        if subids:
            # remove duplicated sub ids, for example: omniverse://ov-content/NVIDIA/Materials/Base/Glass/Clear_Glass.mdl
            subids = set(subids)
            if len(subids) == 1:
                # If only one subid in material file, do nothing if subid is same as file name
                material_file.sub_materials = []
                dirs = material_file.url.split("/")
                file_name = dirs[-1].split(".")[0]
                sub_id = next(iter(subids))
                if sub_id != file_name:
                    sub_material = SubMaterial(sub_id)
                    # Find thumbnail
                    await self._load_sub_material_default_thumbnail(sub_material, material_file.url)
                    material_file.sub_materials = [sub_material]
            elif len(subids) > 1:
                # If more than 1 subid, get all subids and related thumbnails
                material_file.sub_materials = []
                self.sub_materials_count += len(subids)
                for name in subids:
                    sub_material = SubMaterial(name)
                    # Find thumbnail
                    await self._load_sub_material_default_thumbnail(sub_material, material_file.url)

                    material_file.sub_materials.append(sub_material)
        return True

    async def _load_usd_sub_materials_async(self, material_file: MaterialFile) -> bool:
        # usd files. The stage open and traversal run on a worker thread and hand back plain data -
        # prim path strings and a default flag - because doing them here blocks the event loop for
        # the whole of every file. Everything below stays on the loop: omni.client I/O and model
        # updates.
        found = await read_usd_materials_async(material_file.url)
        if found is not None:
            sub_materials = []
            for info in found:
                sub_material = UsdSubMaterial(info.path, default=info.is_default)
                # Find thumbnail
                await self._load_sub_material_default_thumbnail(sub_material, material_file.url)

                sub_materials.append(sub_material)
            if len(sub_materials) == 1:
                # If only one subid in material file, do nothing if subid is same as file name
                material_file.sub_materials = []
                dirs = material_file.url.split("/")
                file_name = dirs[-1].split(".")[0]
                sub_id = next(iter(sub_materials))
                if sub_id != file_name:
                    # The loop above already looked for this sub material's own thumbnail, with the
                    # same arguments - asking again is a second omni.client round trip per file, on
                    # the scan's hot path, for an answer already held.
                    if not sub_material.thumbnail:
                        try:
                            thumbnail = material_file.get_default_thumbnail_url()
                            result, list_entry = await omni.client.stat_async(thumbnail)
                            if result == omni.client.Result.OK:
                                sub_material.thumbnail = thumbnail
                        except asyncio.CancelledError:
                            # A missing thumbnail is survivable; a swallowed cancel is not - it
                            # leaves the traverse walking a collection the user has stopped.
                            raise
                    material_file.sub_materials = [sub_material]
            elif len(sub_materials) > 1:
                # Materials in usd
                self.sub_materials_count += len(sub_materials)
                material_file.sub_materials = sub_materials
            else:
                # No materials in usd file
                return False
            return True
        return False

    async def _load_sub_material_default_thumbnail(self, sub_material: SubMaterial, file_url: str) -> None:
        """
        Load default thumbnail if exists.
        Args:
            file_url: Url of material file.
        """
        thumbnail = sub_material.get_default_thumbnail_url(file_url)
        try:
            result, list_entry = await omni.client.stat_async(thumbnail)
            if result == omni.client.Result.OK:
                sub_material.thumbnail = thumbnail
        except asyncio.CancelledError:
            # As above: the thumbnail is optional, the unwind is not.
            raise
