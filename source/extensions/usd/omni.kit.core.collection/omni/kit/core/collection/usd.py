# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import re
from typing import List, Set, Union

import omni
from pxr import Sdf, Usd


def increment_pathname(path):
    match = re.search(r"_(\d+)$", path)
    if match:
        new_num = int(match.group(1)) + 1
        ret = re.sub(r"_(\d+)$", str.format("_{:02d}", new_num), path)
    else:
        ret = path + "_01"
    return ret


class StageHelper:
    @staticmethod
    def get_stage(usd_context_name: str = "") -> Union[Usd.Stage, None]:
        if not usd_context_name:
            return omni.usd.get_context().get_stage()
        usd_context = omni.usd.get_context(usd_context_name)
        return usd_context.get_stage() if usd_context else None


class CollectionHelper:
    """
    helps convert to/from various representations and provide some
    utilities
    """

    prop_prefix = "collection:"
    prop_dotted_prefix = ".collection:"
    API_prefix = "CollectionAPI:"
    collection_properties = ["expansionRule", "includes", "includeRoot", "excludes"]

    def __init__(self, collection_path: str, stage=None):
        """
        Format of a collection_path is:
        {prim_path}.collection:{collection_name}
        e.g "CollectionTest.collection:allGeomProperties"

        You can pass a non-existent collection path and it will construct an instance of the object...
        It's up to you to validate that the path is valid by calling path_is_valid_collection() if you're unsure
        self.collection_prim will be an invalid prim if the prim path is non-existent
        """
        # This will fail if you don't pass a stage and there is no valid omni stage
        self.stage = stage if stage else omni.usd.get_context().get_stage()
        self.collection_prim = None
        self.collection_name = ""

        self.valid_collection_path = self.is_valid_collection_path(Sdf.Path(collection_path))
        if self.valid_collection_path:

            elements = self._get_collection_path_elements(Sdf.Path(collection_path))
            self.coll_path = Sdf.Path(elements[0] + self.prop_dotted_prefix + elements[1])

            prim_path = self.coll_path.GetPrimPath()  # Get the owning prim

            self.collection_prim = self.stage.GetPrimAtPath(prim_path)

            self.collection_name = elements[1]

    @classmethod
    def from_collection_api(cls, collection: Usd.CollectionAPI):
        return cls(collection.GetCollectionPath().pathString)

    def get_all_members(self, prims_only=False) -> Set[Usd.Object]:
        collection = self.get_collection_api()
        mqueries = collection.ComputeMembershipQuery()

        included_objs = Usd.CollectionAPI.ComputeIncludedObjects(mqueries, self.stage)
        if prims_only:
            included_prims = set()
            for i in included_objs:
                if not i.GetPath().IsPropertyPath():
                    included_prims.add(i)
            return included_prims
        return included_objs

    def get_members(self, filter="") -> List[Sdf.Path]:
        """
        Without a filter (path), this will pass the immediate/explicit members.
        With a filter, it will pass any immediate children of the filter (path)
        filter can be any path like /foo/bar (there may be a better SDF way to do this)
        """
        collection = self.get_collection_api()
        mqueries = collection.ComputeMembershipQuery()
        erm = mqueries.GetAsPathExpansionRuleMap()
        grouping = []

        if not filter:
            for path, expansion_rule in erm.items():
                # Just add the paths themselves where they are
                # Filter out invalid prims
                if (path.IsPrimPath() and self.stage.GetPrimAtPath(path)) or path.IsPropertyPath():
                    grouping.append(path)
        else:
            included_paths = Usd.CollectionAPI.ComputeIncludedPaths(mqueries, self.stage)
            filter_path_sdf = Sdf.Path(filter)
            source_cnt = filter_path_sdf.pathElementCount
            # NOTE: might want to validate against expansion_rule in ['expandPrims', 'expandPrimsAndProperties']:
            for curr_obj_path in included_paths:
                if curr_obj_path.HasPrefix(filter_path_sdf) and curr_obj_path != filter_path_sdf:
                    # Prims
                    if curr_obj_path.IsPrimPath() and curr_obj_path.GetPrimPath().pathElementCount == source_cnt + 1:
                        grouping.append(curr_obj_path)
                    elif curr_obj_path.IsPropertyPath() and curr_obj_path.pathElementCount == source_cnt + 1:
                        grouping.append(curr_obj_path)
        return grouping

    @classmethod
    def is_valid_collection_path(cls, path: Sdf.Path):
        """
        This checks if the syntax of the path is collection-like
        (also returns true for collection paths with properties)
        """
        return Usd.CollectionAPI.IsCollectionAPIPath(path)

    @classmethod
    def is_collection_property_path(cls, path: Sdf.Path):
        """
        If it refers to a property, it's:
        {prim_path}.collection:{collection_name}.{propertyname}..
        """
        elements = cls._get_collection_path_elements(path)
        if len(elements) < 3:
            return False
        return elements[2] in cls.collection_properties

    @classmethod
    def strip_property_from_path(cls, path: Sdf.Path) -> Sdf.Path:
        """
        return the collection path
        """
        elements = cls._get_collection_path_elements(path)
        return Sdf.Path(elements[0] + cls.prop_dotted_prefix + elements[1])

    @classmethod
    def _get_collection_path_elements(cls, path: Sdf.Path) -> List[str]:
        """
        are we something like {prim_path}.collection:{collection_name}:{propertyname}?
        return a List containing up to 3 elements
        1. PrimPath
        2. CollectionName
        3. propertyname (if exists)
        """
        elements = []

        prim_path = path.GetParentPath()
        if not prim_path:
            return elements
        elements.append(prim_path.pathString)

        if path.pathString.find(cls.prop_dotted_prefix) == -1:
            return elements

        coll_name_with_prop = path.pathString[len(prim_path.pathString) + 12 :]
        coll_prop_list = coll_name_with_prop.split(":")

        if len(coll_prop_list) == 0:
            return elements

        elements.append(coll_prop_list[0])  # Prop name

        # TODO need to rewrite if we can have multiple namespaces in coll name. simple for now
        if len(coll_prop_list) < 2:
            return elements

        # Do we have a property name?
        elements.append(coll_prop_list[1])
        return elements

    def is_valid(self) -> bool:
        """
        is the collection valid?
        """
        if not self.valid_collection_path:
            return False
        if not self.collection_prim:
            return False
        if not self.collection_prim.HasAPI(Usd.CollectionAPI):
            return False
        return self.collection_prim.HasAPI(Usd.CollectionAPI, instanceName=self.collection_name)

    def get_collection_api(self) -> Usd.CollectionAPI:
        # I made a mistake here and initially used Apply rather than GetCollection...
        # gives similar results, but hardcodes the expansion Attribute
        return Usd.CollectionAPI.GetCollection(self.collection_prim, self.collection_name)

    def get_prim(self) -> Usd.Prim:
        return self.collection_prim

    def get_collection_name(self, namespace=False):
        """
        so {collection_name} above
        """
        if namespace:
            return self.prop_prefix + self.collection_name
        return self.collection_name

    def get_full_path(self):
        return self.coll_path

    @classmethod
    def get_collection_properties(cls):
        return cls.collection_properties

    def duplicate_with_name(self, new_collection_name: str, generate_valid_name: bool = False) -> str:
        """
        duplicate the collection under the same prim.

        Args:
            generate_valid_name: If False and If the named collection already exists, do nothing, if true
                try to generate a valid name
        """
        collection = self.get_collection_api()

        prim = self.collection_prim

        if generate_valid_name == False:
            if prim.GetPropertiesInNamespace(self.prop_prefix + new_collection_name) and generate_valid_name == False:
                return ""
        else:
            while prim.GetPropertiesInNamespace(self.prop_prefix + new_collection_name):
                new_collection_name = increment_pathname(new_collection_name)

        # USD >=21.02 uses Apply, earlier uses ApplyCollection
        if hasattr(Usd.CollectionAPI, "Apply"):
            new_collection = Usd.CollectionAPI.Apply(prim, new_collection_name)
        else:
            new_collection = Usd.CollectionAPI.ApplyCollection(prim, new_collection_name)

        attr1 = collection.GetExpansionRuleAttr()
        if attr1.HasValue():
            attr2 = new_collection.CreateExpansionRuleAttr()
            attr2.Set(attr1.Get())

        attr1 = collection.GetIncludeRootAttr()
        if attr1.HasValue():
            attr2 = new_collection.CreateIncludeRootAttr()
            attr2.Set(attr1.Get())

        # These 2 seem to print a load of errors of type
        # "usdImaging/instanceAdapter.cpp -- Failed verification: ' r "
        # TODO: investigate
        rel1 = collection.GetIncludesRel()
        targets = rel1.GetTargets()
        if targets:
            rel2 = new_collection.CreateIncludesRel()
            rel2.SetTargets(targets)

        rel1 = collection.GetExcludesRel()
        targets = rel1.GetTargets()
        if targets:
            rel2 = new_collection.CreateExcludesRel()
            rel2.SetTargets(targets)
        # Return the full path
        return self.collection_prim.GetPath().pathString + self.prop_dotted_prefix + new_collection_name

    def delete_collection(self):
        """
        We delete the properties in the collecton
        """
        props = self.collection_prim.GetAuthoredPropertiesInNamespace(self.prop_prefix + self.get_collection_name())
        for p in props:
            self.collection_prim.RemoveProperty(p.GetName())

        self.collection_prim.RemoveAppliedSchema(self.API_prefix + self.get_collection_name())
