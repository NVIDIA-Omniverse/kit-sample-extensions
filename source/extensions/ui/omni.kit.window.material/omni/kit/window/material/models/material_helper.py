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
import time
from typing import Callable, Dict, List, Optional, Union

import carb
import carb.settings
import omni.usd
from carb.eventdispatcher import get_eventdispatcher
from omni.usd import PrimCaching
from pxr import Sdf, Usd, UsdShade

SETTING_SELECTED_INCLUDE_CHILDREN = "/exts/omni.kit.window.material/selected/include_children"
SETTING_STAGE_MATERIALS_WITH_USDRT = "/exts/omni.kit.window.material/stage_materials_with_usdrt"
SETTING_STAGE_HAS_MATERIAL_BINDING_API = "/exts/omni.kit.window.material/stage_has_material_binding_api"
PERSISTENT_SETTING_SELECTED_INCLUDE_CHILDREN = "/persistent" + SETTING_SELECTED_INCLUDE_CHILDREN
PREFIX_FABIC_STAGE_PRIM = "/__Fabric_StageInfo"


class MaterialStatus:
    """
    Represent material status.
    Args:
        assigned (bool): Material assigned or not.
        selected (bool): Material selected or not.
    """

    def __init__(self, assigned: bool = False, selected: bool = False):
        self.assigned = assigned
        self.selected = selected

    def __repr__(self):  # pragma: no cover
        return f'"[Material Status] assigned: {self.assigned}, selected: {self.selected}"'

    def __eq__(self, other):
        return self.assigned == other.assigned and self.selected == other.selected


class MaterialHelper:
    """
    A helper to enum materials in a stage.
    Args:
        on_materials_changed_fn (callable): Function called when materials in stage changed (Add/Remove/Rename). Function signature:
            void on_materials_changed_fn()
        context (str): Name of usd context. Default is "".
    """

    def __init__(
        self,
        on_materials_changed_fn: callable,
        context: str = "",
        on_material_status_changed_fn: Callable[[Usd.Prim, MaterialStatus], None] = None,
    ):
        self._on_materials_changed_fn = on_materials_changed_fn
        self._on_selection_changed_fns: List[callable] = []
        self._on_material_status_changed_fn = on_material_status_changed_fn
        self._selection_future = None

        self._context = omni.usd.get_context(context)
        self._stage: Optional[Usd.Stage] = None
        self._usd_material_cache: Dict[Usd.Prim, MaterialStatus] = {}
        self._prim_caching: Optional[PrimCaching] = None
        self._pick_mode = False
        self._on_picked_fn = None
        self._saved_selected_paths = None
        self._skip_next_selection_change = False

        self._settings = carb.settings.get_settings()
        self._selection_include_children = self._settings.get(PERSISTENT_SETTING_SELECTED_INCLUDE_CHILDREN)
        if self._selection_include_children is None:
            self._selection_include_children = self._settings.get(SETTING_SELECTED_INCLUDE_CHILDREN)
        self._stage_materials_with_usdrt = self._settings.get(SETTING_STAGE_MATERIALS_WITH_USDRT)
        self._stage_has_material_binding_api = self._settings.get(SETTING_STAGE_HAS_MATERIAL_BINDING_API)

        self._refresh()

        self._stage_event_sub = get_eventdispatcher().observe_event(
            observer_name="material stage update",
            event_name=self._context.stage_event_name(omni.usd.StageEventType.OPENED),
            on_event=self._on_stage_opened,
        )

        self._sub_commands()

        self.__dirty = True
        self._notif_material_changed_future = None
        self._material_status_future = None

    def destroy(self) -> None:
        self._stage_event_sub = None
        self._unsub_commands()
        self._unsub_selection()
        self._stage = None
        self._usd_material_cache = {}
        if self._prim_caching:
            self._prim_caching.destroy()
            self._prim_caching = None
        if self._notif_material_changed_future and not self._notif_material_changed_future.done():
            self._notif_material_changed_future.cancel()  # pragma: no cover
        if self._material_status_future and not self._material_status_future.done():
            self._material_status_future.cancel()  # pragma: no cover

    @property
    def selection_include_children(self) -> bool:
        return self._selection_include_children

    @selection_include_children.setter
    def selection_include_children(self, enable: bool) -> None:
        self._selection_include_children = enable
        self._settings.set(PERSISTENT_SETTING_SELECTED_INCLUDE_CHILDREN, enable)
        self._refresh_selection()

    def get_materials_from_stage(self) -> Optional[Dict[str, MaterialStatus]]:
        """
        Get all material prims and assign status in current stage.
        Refer to get_materials_from_stage and get_binding_from_prims in omni.kit.property.material.scripts.material_utils.
        """
        if not self._stage or not self.__dirty:
            return self._usd_material_cache

        start = time.time()
        usd_material_cache = None
        if self._stage_materials_with_usdrt:
            try:
                usd_material_cache = self.__get_stage_materials_with_usdrt()
            except ImportError:
                pass
        if usd_material_cache is None:
            usd_material_cache = self._get_materials_from_prims(
                self._stage.Traverse(
                    Usd.TraverseInstanceProxies(Usd.PrimIsActive and Usd.PrimIsDefined and Usd.PrimIsLoaded)
                )
            )
            usd_material_cache = {k.GetPath().pathString: v for k, v in usd_material_cache.items()}

        carb.log_info(f"{len(usd_material_cache)} stage materials: {time.time() - start}")

        self.__dirty = False
        self._usd_material_cache = usd_material_cache

        return self._usd_material_cache

    def start_pick(self, on_materials_picked: callable):
        """
        Start picking materials from stage.
        Args:
            on_materials_picked: Function called when materials picked. Function signure:
                void on_materials_picked(materials: Dict[Usd.Prim, MaterialStatus])
        """
        self._pick_mode = True
        # Save current selection
        self._saved_selected_paths = self._context.get_selection().get_selected_prim_paths()
        self._on_picked_fn = on_materials_picked

        # Subscribe selection change
        if self._selection_future is None:
            self._sub_selection()

    def stop_pick(self):
        """
        Stop picking materials from stage.
        """
        # Unsubscribe selection change
        if len(self._on_selection_changed_fns) == 0:
            self._unsub_selection()
        else:
            self._skip_next_selection_change = True
        # Restore selection
        if self._saved_selected_paths is not None:
            self._context.get_selection().set_selected_prim_paths(self._saved_selected_paths, True)

        self._pick_mode = False

    def add_on_selection_changed_fn(
        self, on_selection_changed_fn: callable, trigger_on_next_selection: bool = False
    ) -> None:
        """
        Add function called when material selection changed.
        Args:
            on_selection_changed_fn (callable): Function called when material selection changed. Function signure:
                void on_selection_changed_fn(materials: Dict[Usd.Prim, MaterialStatus])
            trigger_on_next_selection (bool): False to call callback immediately with current selection. Otherswise call when next selection changed.
        """
        if on_selection_changed_fn not in self._on_selection_changed_fns:
            self._on_selection_changed_fns.append(on_selection_changed_fn)
            if not trigger_on_next_selection:
                selected_paths = self._context.get_selection().get_selected_prim_paths()
                materials = self._get_materials_from_prims(selected_paths, force_selected=True)
                on_selection_changed_fn(materials)

            if self._selection_future is None:
                self._sub_selection()

    def remove_on_selection_changed_fn(self, on_selection_changed_fn: callable) -> bool:
        """
        Remove function called when material selection chnaged:
        Args:
            on_selection_changed_fn (callable): Function to be removed.
        """
        if on_selection_changed_fn in self._on_selection_changed_fns:
            self._on_selection_changed_fns.remove(on_selection_changed_fn)
            if len(self._on_selection_changed_fns) == 0:
                self._unsub_selection()
            return True
        else:
            return False

    def _refresh_selection(self):
        selected_paths = self._context.get_selection().get_selected_prim_paths()
        materials = self._get_materials_from_prims(selected_paths, force_selected=True)
        for fn in self._on_selection_changed_fns:
            fn(materials)

    def _refresh(self) -> None:
        # Refresh current stage and prim cache
        stage = self._context.get_stage()
        if not stage:
            self._stage = None
            return

        if self._stage == stage:
            return

        self._stage = stage
        self._stage_id = self._context.get_stage_id()
        if self._prim_caching is not None:
            old_stage = self._prim_caching.get_stage()
            if self._stage != old_stage:
                self._prim_caching.destroy()
                self._prim_caching = None

        if self._prim_caching is None:
            # Prim cache to track materials add/remove/rename
            self._prim_caching = PrimCaching(UsdShade.Material, self._stage, self._on_prim_cache_changed)

    def __get_stage_materials_with_usdrt(self) -> Dict[Usd.Prim, MaterialStatus]:
        from usdrt import Usd as Usdrt

        usdrt_stage = Usdrt.Stage.Attach(self._stage_id)
        # Kit 111's OVStage-backed USDRT (what production apps load) has none of the Fabric-only queries used here
        # (GetPrimsWithTypeName, GetPrimsWithAppliedAPIName): use the caller's USD traversal instead.
        if not usdrt_stage or not all(
            hasattr(usdrt_stage, query) for query in ("GetPrimsWithTypeName", "GetPrimsWithAppliedAPIName")
        ):
            return None

        materials: Dict[str, MaterialStatus] = {}
        # Get all materials, ignore come from fabric stage when /app/useFabricSceneDelegate=true
        material_paths = [
            path
            for path in usdrt_stage.GetPrimsWithTypeName("Material")
            if not str(path).startswith(PREFIX_FABIC_STAGE_PRIM)
        ]
        selected_prim_paths = self._context.get_selection().get_selected_prim_paths()
        for path in material_paths:
            materials[str(path)] = MaterialStatus(assigned=False, selected=str(path) in selected_prim_paths)

        # Get material assignment and selection is very slow for huge stage with huge prims do it async
        if self._material_status_future and not self._material_status_future.done():
            self._material_status_future.cancel()
        self._material_status_future = asyncio.ensure_future(
            self._refresh_material_status(usdrt_stage, materials, selected_prim_paths)
        )

        return materials

    async def _refresh_material_status(
        self, usdrt_stage: "Usdrt.Stage", materials: List[MaterialStatus], selected_prim_paths: List[str]
    ):
        # Get material assignment and selection
        start = time.time()

        if self._stage_has_material_binding_api:
            material_binding_paths = usdrt_stage.GetPrimsWithAppliedAPIName("MaterialBindingAPI")
            carb.log_info(f"{len(material_binding_paths)} material bindings: {time.time() - start}")
            count = 0
            last_time = time.time()
            for path in material_binding_paths:
                if str(path).startswith(PREFIX_FABIC_STAGE_PRIM):
                    continue
                relationship = usdrt_stage.GetRelationshipAtPath(f"{path}.material:binding")
                for target in relationship.GetTargets():
                    try:
                        # Here do not check if target in material_paths because it is slow if material_paths is huge
                        path_string = str(target)
                        materials[path_string].assigned = True
                        if not materials[path_string].selected:
                            materials[path_string].selected = path_string in selected_prim_paths
                        if self._on_material_status_changed_fn:
                            self._on_material_status_changed_fn(path_string, materials[path_string])
                        count += 1
                    except Exception as e:
                        # target not in material_paths, ignore now
                        pass

                if time.time() - last_time >= 0.1:
                    await asyncio.sleep(0.1)
                    last_time = time.time()

            carb.log_info(f"{count} material bindings found: {time.time() - start}")
        else:
            imageable_paths = usdrt_stage.GetPrimsWithTypeName("Imageable")
            carb.log_info(f"{len(imageable_paths)} imageable prims found: {time.time() - start}")
            count = 0
            last_time = time.time()
            for path in imageable_paths:
                prim = self._stage.GetPrimAtPath(Sdf.Path(str(path)))
                relationship = prim.GetRelationship("material:binding")
                if relationship:
                    for target in relationship.GetTargets():
                        # Here do not check if target in material_paths because it is slow if material_paths is huge
                        try:
                            path_string = str(target)
                            materials[path_string].assigned = True
                            if not materials[path_string].selected:
                                materials[path_string].selected = path_string in selected_prim_paths
                            if self._on_material_status_changed_fn:
                                self._on_material_status_changed_fn(path_string, materials[path_string])
                            count += 1
                        except Exception as e:
                            # target not in material_paths, ignore now
                            pass

                if time.time() - last_time >= 0.1:
                    await asyncio.sleep(0.1)
                    last_time = time.time()
            carb.log_info(f"{count} material bindings found: {time.time() - start}")

        self._material_status_future = None

    def _get_materials_from_prims(
        self, prims: Union[List[str], List[Usd.Prim]], force_selected: bool = False
    ) -> Dict[Usd.Prim, MaterialStatus]:
        materials: Dict[Usd.Prim, MaterialStatus] = {}

        def __add_material(prim: Usd.Prim, assigned: bool = False, selected: bool = False):
            if prim in materials:
                # Only update status when value is True
                if assigned:
                    materials[prim].assigned = True
                if selected:
                    materials[prim].selected = True
            elif (
                not omni.usd.is_hidden_type(prim)
                and not prim.GetMetadata("ignore_material_updates")
                and not prim.IsInstanceProxy()
            ):
                materials[prim] = MaterialStatus(assigned=assigned, selected=selected)

        def __check_prim(prim: Usd.Prim):
            if prim.IsA(UsdShade.Material):
                __add_material(prim, selected=prim_selected)
            else:
                material, relationship = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
                if material:
                    __add_material(material.GetPrim(), assigned=True, selected=prim_selected)

            # Only check children in selection mode
            if force_selected and self._selection_include_children:
                for child in prim.GetAllChildren():
                    __check_prim(child)

        if not force_selected:
            selected_prim_paths = self._context.get_selection().get_selected_prim_paths()

        for prim in prims:
            prim_selected = force_selected if force_selected else str(prim.GetPath()) in selected_prim_paths

            if isinstance(prim, str):
                prim = self._stage.GetPrimAtPath(prim)

            __check_prim(prim)

        return materials

    def _on_prim_cache_changed(self) -> None:
        self.__dirty = True

        if self._notif_material_changed_future and not self._notif_material_changed_future.done():
            self._notify_material_changed_future.cancel()  # pragma: no cover
        self._notify_material_changed_future = asyncio.ensure_future(self.__notify_material_changed())

    async def __notify_material_changed(self):
        # Wait for a while to avoid prim cache change event one by one
        for _ in range(2):
            await omni.kit.app.get_app().next_update_async()
        self._refresh()
        if self._on_materials_changed_fn:
            self._on_materials_changed_fn()
        self._notify_material_changed_future = None

    def _sub_selection(self):
        if self._selection_future is None:
            self._selection_future = asyncio.ensure_future(self._get_selected_materials_async())

    def _unsub_selection(self):
        if self._selection_future is not None:
            self._selection_future.cancel()
            self._selection_future = None

    async def _get_selected_materials_async(self):
        while True:
            selected_prim_paths = await self._context.selection_changed_async()
            if selected_prim_paths:
                selected_material_prims = self._get_materials_from_prims(selected_prim_paths, force_selected=True)
            else:
                selected_material_prims = {}

            if self._skip_next_selection_change:
                self._skip_next_selection_change = False
                continue

            if self._pick_mode:
                self._on_picked_fn(selected_material_prims)
            else:
                for fn in self._on_selection_changed_fns:
                    fn(selected_material_prims)

    def _on_material_commands(self, cmds: List[str]) -> None:
        if any(
            item
            in [
                "BindMaterial",
                "BindMaterialCommand",
                "CreateReferenceCommand",
                "CreateReference",
                "CreatePayloadCommand",
                "CreatePayload",
            ]
            for item in cmds
        ):
            # Donot know happened on which prim, just notify materials changed
            self.__dirty = True
            if self._on_materials_changed_fn:
                self._on_materials_changed_fn()

    def _sub_commands(self) -> None:
        # Subscribe commands to track material bind changing
        omni.kit.undo.subscribe_on_change(self._on_material_commands)

    def _unsub_commands(self) -> None:
        omni.kit.undo.unsubscribe_on_change(self._on_material_commands)

    def _on_stage_opened(self, event):
        # Trigger only once to make sure stage initialized.
        # In general, stage is initialized when starup but usd stage may not opened yet.
        if self._stage is None:
            self._refresh()
            self.__dirty = True
            if self._on_materials_changed_fn:
                self._on_materials_changed_fn()
            self._stage_event_sub = None
