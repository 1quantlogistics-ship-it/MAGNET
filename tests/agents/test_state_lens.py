"""
TASK-015: Token Efficiency via State Lens
"""

import json

from magnet.agents.state_lens import extract_lens


def test_extract_lens_filters_non_geometry_resources():
    state = {
        "resources": {
            "g1": {"_type": "geometry.body", "_id": "g1", "offset_y_m": 0.0},
            "g2": {"_type": "geometry.section", "_id": "g2", "station": 0.5, "points": [[0.0, 0.0], [1.0, 1.0]]},
            "x1": {"_type": "interior.room", "_id": "x1", "name": "cabin"},
            "d1": {"_type": "geometry.section", "_id": "d1", "_deleted": True},
        },
        "hull": {"loa": 25.0, "beam": 5.0, "draft": 1.2, "depth": 2.0},
        "mission": {"max_speed_kts": 30.0},
        "physics": {"hydrostatics": {"gm_m": 0.6}, "resistance": {"rt_n": 1234}},
        "huge": {"blob": "x" * 10000},
    }

    lens = extract_lens(state)
    assert "resources" in lens
    assert "g1" in lens["resources"]
    assert "g2" in lens["resources"]
    assert "x1" not in lens["resources"]
    assert "d1" not in lens["resources"]


def test_extract_lens_keeps_key_scalar_paths():
    state = {
        "resources": {},
        "hull": {"loa": 25.0, "beam": 5.0, "draft": 1.2, "depth": 2.0},
        "mission": {"max_speed_kts": 30.0},
        "physics": {"hydrostatics": {"gm_m": 0.6}},
    }
    lens = extract_lens(state)
    assert lens["hull"]["loa"] == 25.0
    assert lens["mission"]["max_speed_kts"] == 30.0
    assert lens["physics"]["hydrostatics"]["gm_m"] == 0.6


def test_extract_lens_reduces_size_substantially():
    state = {
        "resources": {"g1": {"_type": "geometry.body", "_id": "g1"}},
        "hull": {"loa": 25.0, "beam": 5.0, "draft": 1.2, "depth": 2.0},
        "mission": {"max_speed_kts": 30.0},
        "physics": {"hydrostatics": {"gm_m": 0.6}},
        "huge": {"blob": "x" * 20000},
    }
    full = json.dumps(state)
    lens = json.dumps(extract_lens(state))
    assert len(lens) < len(full) * 0.6

