import os.path

import carb
import omni.kit.commands
import omni.usd
import pxr.Gf
import pxr.Sdf
import pxr.Tf
import pxr.Usd


def get_parent_prim(stage, create=True):
    default_prim = stage.GetDefaultPrim()
    parent_prim = None
    if default_prim:
        parent_prim = default_prim
    else:
        parent_prim = stage.GetPseudoRoot()

    path = parent_prim.GetPath().AppendChild("SpawnedEntities")

    if create:
        return stage.DefinePrim(path, "Scope")
    else:
        return stage.GetPrimAtPath(path)


class SpawnEntityCommand(omni.kit.commands.Command):
    """
    Command spawns entities from source paths. Source paths are prim paths or layer paths. Entities are created as prims under SpawnedEntities prim. These entities have USD references with source paths.
    @param
        source_paths: A list of prim paths or layer paths.
        transform: World transform of spawned entities.
    @return
        Returns spawned entities' names, which are names of created prims under SpawnedEntities.
    """

    def __init__(self, source_paths: list[str], transform: pxr.Gf.Matrix4d):
        super().__init__()

        self._source_paths = source_paths
        self._transform = transform
        self._spawned_names = []

    def do(self):
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            carb.log_error("Can't get current stage.")
            return []

        with pxr.Usd.EditContext(stage, stage.GetEditTargetForLocalLayer(stage.GetSessionLayer())):
            entity_parent = get_parent_prim(stage)

            for source_path in self._source_paths:
                source_path = source_path.strip()
                if not source_path:
                    continue

                if pxr.Sdf.Path.IsValidPathString(source_path):
                    asset_path = ""
                    prim_path = pxr.Sdf.Path(source_path)
                    if not stage.GetPrimAtPath(prim_path):
                        carb.log_error(f"{prim_path} is not a valid prim.")
                        continue
                else:
                    asset_path = source_path
                    prim_path = pxr.Sdf.Path()
                    if not pxr.Sdf.Layer.FindOrOpen(asset_path):
                        carb.log_error(f"Can't open layer {asset_path}")
                        continue

                base_name, ext = os.path.splitext(os.path.basename(source_path))

                base_name = pxr.Tf.MakeValidIdentifier(base_name)

                new_path = omni.usd.get_stage_next_free_path(
                    stage, entity_parent.GetPath().AppendChild(base_name).pathString, False
                )
                name = pxr.Sdf.Path(new_path).name
                self._spawned_names.append(name)
                entity_prim = stage.DefinePrim(new_path)

                entity_prim.SetPayload(asset_path, prim_path)

                xformable = pxr.UsdGeom.Xformable(entity_prim)
                if xformable:
                    xform_cache = pxr.UsdGeom.XformCache(pxr.Usd.TimeCode.Default())
                    parent_transform = xform_cache.GetParentToWorldTransform(entity_prim)

                    transform = parent_transform.GetInverse() * self._transform
                    xformable.MakeMatrixXform().Set(transform)

            return self._spawned_names

    def undo(self):
        DestroyEntityCommand(self._spawned_names).do()


class DestroyEntityCommand(omni.kit.commands.Command):
    """
    Command destroys spawned entities. It removes prims under SpawnedEntities prim if they match the given names.
    @param
        entity_names: A list of entities' names, which are names of prims under SpawnedEntities prim.
    """

    # Removes spawned entity prims.
    def __init__(self, entity_names: list[str]):
        super().__init__()

        self._entity_names = entity_names
        self._del_prim_cmd = None

    def do(self):
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            carb.log_error("Can't get current stage.")
            return

        with pxr.Usd.EditContext(stage, stage.GetEditTargetForLocalLayer(stage.GetSessionLayer())):
            entity_parent = get_parent_prim(stage, False)
            if not entity_parent:
                return

            paths = [entity_parent.GetPath().AppendChild(name) for name in self._entity_names]

            filtered_paths = [path for path in paths if stage.GetPrimAtPath(path)]

            self._del_prim_cmd = omni.usd.commands.DeletePrimsCommand(paths=filtered_paths, stage=stage)
            self._del_prim_cmd.do()

    def undo(self):
        if self._del_prim_cmd is not None:
            self._del_prim_cmd.undo()


class FindEntityCommand(omni.kit.commands.Command):
    """
    Command finds spawned entities from source path. It returns prims' names under SpawnedEntities prim, if they are created from given source path.
    @param
        source_path: A prim path or a layer path that is used to spawn entities.
    @return
        Returns a list of entitis'names, which are names of prims under SpawnedEntities prim.
    """

    def __init__(self, source_path: str):
        super().__init__()
        self._source_path = source_path

    def do(self):
        if not self._source_path:
            return []

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            carb.log_error("Can't get current stage.")
            return []

        entity_parent = get_parent_prim(stage, False)
        if not entity_parent:
            return []

        entity_parent = stage.GetSessionLayer().GetPrimAtPath(entity_parent.GetPath())
        if not entity_parent:
            return []

        if pxr.Sdf.Path.IsValidPathString(self._source_path):
            asset_path = ""
            prim_path = pxr.Sdf.Path(self._source_path)
        else:
            asset_path = pxr.Sdf.ComputeAssetPathRelativeToLayer(stage.GetRootLayer(), self._source_path)
            prim_path = pxr.Sdf.Path()

        entity_names = []

        for prim in entity_parent.nameChildren:
            for payload in prim.payloadList.explicitItems:
                if payload.assetPath == asset_path and payload.primPath == prim_path:
                    entity_names.append(prim.name)
                    break

        return entity_names
