from typing import Dict, List


def check_clusters(hierarchy_nodes: List[Dict]) -> None:
    # recursively check that all clusters have all the proper fields in
    # place
    for cluster in hierarchy_nodes:
        assert "origin" in cluster.keys()
        assert "score" in cluster.keys()
        assert cluster["score"] >= 0
        assert isinstance(cluster["score"], float)
        assert "level" in cluster.keys()
        assert cluster["level"] >= 0
        assert isinstance(cluster["level"], int)
        assert isinstance(cluster["children"], list)
        assert isinstance(cluster["poster_idx"], int)
        assert isinstance(cluster["id"], int)

        for child_id in cluster["children"]:
            assert isinstance(child_id, int)
