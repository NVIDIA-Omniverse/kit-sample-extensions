# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import asyncio
import weakref
from typing import List, Set, Tuple

import omni.kit.app
import omni.usd
from pxr import Sdf, Usd, UsdGeom

from .cv_selection import CvSelection


class CvPayloadManager:
    __create_cv_payload_fn = None
    __is_cv_payload_fn = None

    __REQURED_EXTENSIONS = ["omni.kit.property.usd"]

    PROPERTY_PANEL_NAME = "basis_curves_cv"

    def __init__(self, selection: CvSelection, usd_context_name: str = ""):
        self.__context = omni.usd.get_context(usd_context_name)
        self.__default_paths = []
        self.__extension_hooks = []
        self.__selection = weakref.ref(selection)
        self.__selection_changed_id = None
        self.__registered_extensions = {}
        manager = omni.kit.app.get_app().get_extension_manager()
        for extension_name in CvPayloadManager.__REQURED_EXTENSIONS:
            self.__extension_hooks.append(
                manager.subscribe_to_extension_enable(
                    lambda _: self.__register_extension(extension_name),
                    lambda _: self.__unregister_extension(extension_name),
                    ext_name=extension_name,
                    hook_name=f"CvPayloadManager listener ({extension_name})",
                )
            )

    def set_default_prim_paths(self, paths: List[str]):
        async def update_properties_async():
            await omni.kit.app.get_app().next_update_async()
            self.__on_selection_changed(set())

        self.__default_paths = [Sdf.Path(path) for path in paths]
        asyncio.ensure_future(update_properties_async())

    def __extensions_updated(self):
        CvPayloadManager.__create_cv_payload_fn = None
        CvPayloadManager.__is_cv_payload_fn = None

        if self.__selection_changed_id:
            selection = self.__selection()
            if selection:
                selection.remove_selection_changed_fn(self.__selection_changed_id)
            self.__selection_changed_id = None

        for extension_name in CvPayloadManager.__REQURED_EXTENSIONS:
            if extension_name not in self.__registered_extensions:
                return

        import omni.kit.property.usd

        class CvPayload(omni.kit.property.usd.PrimSelectionPayload):
            def __init__(self, stage: weakref.ReferenceType(Usd.Stage), paths: List[Sdf.Path], indices: List[int]):
                min_length = min(len(paths), len(indices))
                super().__init__(stage, paths[:min_length])
                self._indices = indices[:min_length]

            def get_indices(self) -> List[int]:
                return self._indices

            def get_paths_and_indices(self) -> List[Tuple[Sdf.Path, int]]:
                tuple_list = []
                for i, prim_path in enumerate(self.get_paths()):
                    tuple_list.append((prim_path, self._indices[i]))
                return tuple_list

        def create_cv_payload(
            stage: weakref.ReferenceType(Usd.Stage),
            paths: List[Sdf.Path],
            indices: List[int],
            default_paths: List[Sdf.Path],
        ) -> Tuple[str, any]:
            if len(paths) > 0 and len(indices) > 0:
                return CvPayloadManager.PROPERTY_PANEL_NAME, CvPayload(stage, paths, indices)
            return "prim", omni.kit.property.usd.PrimSelectionPayload(stage, default_paths)

        def is_cv_payload(payload):
            if isinstance(payload, CvPayload):
                return True
            return False

        CvPayloadManager.__create_cv_payload_fn = create_cv_payload
        CvPayloadManager.__is_cv_payload_fn = is_cv_payload

        selection = self.__selection()
        if selection:
            self.__selection_changed_id = selection.add_selection_changed_fn(self.__on_selection_changed)

    def __on_selection_changed(self, selected_cvs: Set[Tuple[UsdGeom.BasisCurves, int]]):
        stage = self.__context.get_stage()
        if stage:
            if CvPayloadManager.__create_cv_payload_fn:
                indices = []
                prim_paths = []
                for curve, index in selected_cvs:
                    prim = curve.GetPrim()
                    if prim.IsA(UsdGeom.BasisCurves):
                        indices.append(index)
                        prim_paths.append(prim.GetPath())
                name, payload = CvPayloadManager.__create_cv_payload_fn(
                    weakref.ref(stage), prim_paths, indices, self.__default_paths
                )
                omni.kit.window.property.get_window().notify(name, payload)

    def __register_extension(self, extension_name: str):
        if extension_name not in self.__registered_extensions:
            self.__registered_extensions[extension_name] = True
            self.__extensions_updated()

    def __unregister_extension(self, extension_name: str):
        if extension_name in self.__registered_extensions:
            del self.__registered_extensions[extension_name]
            self.__extensions_updated()

    @staticmethod
    def is_cv_payload(payload):
        if CvPayloadManager.__is_cv_payload_fn:
            return CvPayloadManager.__is_cv_payload_fn(payload)
        return False
