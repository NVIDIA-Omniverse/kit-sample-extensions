import json
import os

import carb
import carb.dictionary
import carb.events
import omni.kit.app
import omni.kit.test
import omni.usd
from carb import log_info
from omni.kit.converter.geojson import _geojson_converter
from pxr import Sdf, Usd, UsdGeom

# import geojson

EXTENSION_NAME = "GeoJSON Converter"
_geojson_instance = None  # Singleton approach


class TestGeoJSON(omni.kit.test.AsyncTestCase):

    # # Create good data
    # goodLineString = geojson.LineString([(5.01,3.4543,63.4),(5.101,3.4554,68.45),(5.121,3.4558,67.5)])
    # goodPolygon = geojson.Polygon([[(5.01,3.4543,63.4),(5.101,3.4554,68.45),(5.121,3.4558,67.5)]])
    # goodMultiPolygon = geojson.MultiPolygon([
    #     ([(5.01,3.4543,63.4),(5.101,3.4554,68.45),(5.121,3.4558,67.5)]),
    #     ([(2.01,4.4543,2.4),(2.101,4.4554,2.45),(2.121,4.4558,2.5)])
    #     ])

    # goodFeatures = []
    # goodFeatures.append(Feature(geometry=goodLineString, properties={"object_id": "123uio-890zxd","type": "aString","material": "metal"}))
    # goodFeatures.append(Feature(geometry=goodPolygon, properties={"object_id": "123321-dfs3","type": "aPolygon","material": "metal"}))
    # goodFeatures.append(Feature(geometry=goodMultiPolygon, properties={"object_id": "3553m7r6-2w4y67","type": "PolygonGroup","material": "metal"}))

    # goodFeatureCollection = FeatureCollection(goodFeatures)

    # # Create bad data
    # badLineString = geojson.LineString([(5.01,3.4543,63.4)])
    # badPolygon = geojson.Polygon([[(5.01,3.4543,63.4),(5.101,3.4554,68.45)]])
    # badMultiPolygon = geojson.MultiPolygon([
    #     ([(5.01,3.4543,63.4),(5.121,3.4558,67.5)]),
    #     ([(2.101,4.4554,2.45),(2.121,4.4558,2.5)])
    #     ])

    # badFeatures = []
    # badFeatures.append(Feature(geometry=badLineString, properties={"object_id": "123uio-890zxd","type": "aString","material": "metal"}))
    # badFeatures.append(Feature(geometry=badPolygon, properties={"object_id": "123321-dfs3","type": "aPolygon","material": "metal"}))
    # badFeatures.append(Feature(geometry=badMultiPolygon, properties={"object_id": "3553m7r6-2w4y67","type": "PolygonGroup","material": "metal"}))

    # badFeatureCollection = FeatureCollection(badFeatures)

    goodData = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[5.01, 3.4543, 63.4], [5.101, 3.4554, 68.45], [5.121, 3.4558, 67.5]],
                },
                "properties": {"object_id": "123uio-890zxd", "type": "Rail_Left", "material": "metal"},
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        # Ring 1
                        [[5.01, 3.4543, 63.4], [5.101, 3.4554, 68.45], [5.121, 3.4654, 68.2]]
                    ],
                },
                "properties": {"object_id": "123321-dfs3", "type": "polygon", "material": "metal"},
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [
                        # Polygon 1
                        [
                            # Polygon 1, Ring 1
                            [[5.01, 3.4543, 63.4], [5.101, 3.4554, 68.45], [5.121, 3.4654, 68.2]]
                        ],
                        # Polygon 2
                        [
                            # Polygon 2, Ring 1
                            [[5.01, 3.4543, 63.4], [5.101, 3.4554, 68.45], [5.121, 3.4654, 68.2]]
                        ],
                    ],
                },
                "properties": {"object_id": "123321-dfs3", "type": "polygon", "material": "metal"},
            },
        ],
        "crs": {"properties": {"name": "EPSG:4326"}, "type": "name"},
    }

    badDataWrongCoordinateCount = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [5.01, 3.4543, 63.4],
                    ],
                },
                "properties": {"object_id": "123uio-890zxd", "type": "Rail_Left", "material": "metal"},
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        # Ring 1
                        [[5.01, 3.4543, 63.4], [5.101, 3.4554, 68.45]]
                    ],
                },
                "properties": {"object_id": "123321-dfs3", "type": "polygon", "material": "metal"},
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [
                        # Polygon 1
                        [
                            # Polygon 1, Ring 1
                            [[5.01, 3.4543, 63.4], [5.101, 3.4554, 68.45]]
                        ],
                        # Polygon 2
                        [
                            # Polygon 2, Ring 1
                            [[5.01, 3.4543, 63.4], [5.101, 3.4554, 68.45]]
                        ],
                    ],
                },
                "properties": {"object_id": "123321-dfs3", "type": "polygon", "material": "metal"},
            },
        ],
        "crs": {"properties": {"name": "EPSG:4326"}, "type": "name"},
    }

    async def setUp(self):
        # global _geojson_instance # needed for proper startup and shutdown
        # _geojson_instance = self
        self._geojson_interface = _geojson_converter.acquire_interface()
        self.assertIsNotNone(self._geojson_interface)

    def testFolderDoesNotExist(self):
        self._geojson_interface = _geojson_converter.acquire_interface()

        # provide current path
        path = os.path.abspath("./")
        print(path)
        # Create stage
        url = path + "/testFolderDoesNotExist.usda"
        stage = Usd.Stage.CreateNew(url)
        print("url: " + url)
        print("Path to file exists: " + str(os.path.exists(url)))
        print("IsSupportedFile: " + str(Usd.Stage.IsSupportedFile(path + url)))
        # add a default prim
        print("add a default prim")
        prim = stage.DefinePrim("/World", "XForm")
        stage.SetDefaultPrim(prim)
        # root_frame = UsdGeom.Xform.Define(stage, '/World')
        # print("Setting /World as default prim")
        # for x in stage.Traverse():
        #     stage.SetDefaultPrim(x.GetName())
        # print("Saving root layer")
        # stage.GetRootLayer().Save()

        countBefore = 0
        for x in stage.Traverse():
            countBefore += 1
        print(countBefore)
        # run program
        self._geojson_interface.convert_geojson_python(url, path, False)
        # check that prim size is still same
        countAfter = 0
        for x in stage.Traverse():
            countAfter += 1
        print(countAfter)
        os.remove("testFolderDoesNotExist.usda")
        self.assertEqual(countBefore, countAfter)

    def testEmptyFolder(self):
        self._geojson_interface = _geojson_converter.acquire_interface()

        #### DO NOT DELETE - USING AS REFERENCE ####
        # # Create stage in memory
        # stage = Usd.Stage.CreateInMemory()
        # url = stage.GetRootLayer().identifier
        # print(url)
        # # provide current path
        # path = os.path.abspath("./")
        # print(path)
        # # add a default prim
        # prim = stage.DefinePrim("/World", "XForm")
        ############################################

        # provide current path
        path = os.path.abspath("./")
        print(path)
        # Create stage
        url = path + "/testEmptyFolder.usda"
        stage = Usd.Stage.CreateNew(url)
        print("url: " + url)
        print("Path to file exists: " + str(os.path.exists(url)))
        print("IsSupportedFile: " + str(Usd.Stage.IsSupportedFile(path + url)))
        # add a default prim
        print("add a default prim")
        prim = stage.DefinePrim("/World", "XForm")
        stage.SetDefaultPrim(prim)
        # root_frame = UsdGeom.Xform.Define(stage, '/World')
        # print("Setting /World as default prim")
        # for x in stage.Traverse():
        #     stage.SetDefaultPrim(x.GetName())
        # print("Saving root layer")
        # stage.GetRootLayer().Save()

        countBefore = 0
        for x in stage.Traverse():
            countBefore += 1
        print(countBefore)
        # run program
        self._geojson_interface.convert_geojson_python(url, path, False)
        # check that prim size is still same
        countAfter = 0
        for x in stage.Traverse():
            countAfter += 1
        print(countAfter)
        os.remove("testEmptyFolder.usda")
        self.assertEqual(countBefore, countAfter)

    def testGoodGeoJSONFile(self):
        self._geojson_interface = _geojson_converter.acquire_interface()

        # provide current path
        path = os.path.abspath("./")
        print(path)
        # Create stage
        url = path + "/testGoodGeoJSONFile.usda"
        stage = Usd.Stage.CreateNew(url)
        print("url: " + url)
        print("Path to file exists: " + str(os.path.exists(url)))
        print("IsSupportedFile: " + str(Usd.Stage.IsSupportedFile(path + url)))
        # add a default prim
        print("add a default prim")
        prim = stage.DefinePrim("/World", "XForm")
        stage.SetDefaultPrim(prim)
        # root_frame = UsdGeom.Xform.Define(stage, '/World')
        # print("Setting /World as default prim")
        # for x in stage.Traverse():
        #     stage.SetDefaultPrim(x.GetName())
        # print("Saving root layer")
        # stage.GetRootLayer().Save()

        # store data for json
        json_string = json.dumps(self.goodData)
        # check string
        # print(json_string)

        # Create GeoJSON file
        # Directly from dictionary
        with open("good.geojson", "w") as outfile:
            json.dump(self.goodData, outfile)
        # with open('good.geojson', 'w') as f:
        #     dump(goodFeatureCollection, f)
        # check load
        with open("good.geojson") as json_file:
            data = json.load(json_file)
            print(data)

        countBefore = 0
        for x in stage.Traverse():
            countBefore += 1
        print(countBefore)
        # run program
        self.assertEqual(self._geojson_interface.convert_geojson_python(url, path, False), 0)
        # check that prim size is still same
        countAfter = 0
        for x in stage.Traverse():
            countAfter += 1
        print(countAfter)
        os.remove("good.geojson")
        os.remove("testGoodGeoJSONFile.usda")
        self.assertNotEqual(countBefore, countAfter)

    def testBadGeoJSONFile(self):
        self._geojson_interface = _geojson_converter.acquire_interface()

        # provide current path
        path = os.path.abspath("./")
        print(path)
        # Create stage
        url = path + "/testBadGeoJSONFile.usda"
        stage = Usd.Stage.CreateNew(url)
        print("url: " + url)
        print("Path to file exists: " + str(os.path.exists(url)))
        print("IsSupportedFile: " + str(Usd.Stage.IsSupportedFile(path + url)))
        # add a default prim
        print("add a default prim")
        prim = stage.DefinePrim("/World", "XForm")
        stage.SetDefaultPrim(prim)
        # root_frame = UsdGeom.Xform.Define(stage, '/World')
        # print("Setting /World as default prim")
        # for x in stage.Traverse():
        #     stage.SetDefaultPrim(x.GetName())
        # print("Saving root layer")
        # stage.GetRootLayer().Save()

        # store data for json
        json_string = json.dumps(self.badDataWrongCoordinateCount)
        # check string
        # print(json_string)

        # Create GeoJSON file
        # Directly from dictionary
        with open("bad.geojson", "w") as outfile:
            json.dump(self.badDataWrongCoordinateCount, outfile)
        # with open('bad.geojson', 'w') as f:
        #     dump(badFeatureCollection, f)
        # check load
        with open("bad.geojson") as json_file:
            data = json.load(json_file)
            print(data)

        countBefore = 0
        for x in stage.Traverse():
            countBefore += 1
        print(countBefore)
        # run program
        self._geojson_interface.convert_geojson_python(url, path, False)
        # check that prim size is still same
        countAfter = 0
        for x in stage.Traverse():
            countAfter += 1
        print(countAfter)
        os.remove("bad.geojson")
        os.remove("testBadGeoJSONFile.usda")
        self.assertEqual(countBefore, countAfter)
