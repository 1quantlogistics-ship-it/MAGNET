"""
TASK-018: Geometry-Pure Cost Scaling
"""

from magnet.cost.estimator import CostEstimator


class _SM:
    def __init__(self, d):
        self._d = d

    def get(self, path, default=None):
        parts = path.split(".")
        cur = self._d
        for p in parts:
            if not isinstance(cur, dict) or p not in cur:
                return default
            cur = cur[p]
        return cur


def test_engineering_does_not_branch_on_patrol_vessel_type():
    est = CostEstimator()
    sm_patrol = _SM({"hull": {"lwl": 20.0}, "mission": {"vessel_type": "patrol"}})
    sm_commercial = _SM({"hull": {"lwl": 20.0}, "mission": {"vessel_type": "commercial"}})

    patrol = est._estimate_engineering(sm_patrol)
    commercial = est._estimate_engineering(sm_commercial)

    assert patrol.engineering_hours == commercial.engineering_hours


def test_engineering_branches_only_on_military_organization():
    est = CostEstimator()
    sm_mil = _SM({"hull": {"lwl": 20.0}, "mission": {"organization": "military"}})
    sm_civ = _SM({"hull": {"lwl": 20.0}, "mission": {"organization": "commercial"}})

    mil = est._estimate_engineering(sm_mil)
    civ = est._estimate_engineering(sm_civ)

    assert mil.engineering_hours > civ.engineering_hours


def test_complexity_scales_with_body_and_compartments():
    est = CostEstimator()
    sm1 = _SM({"hull": {"lwl": 20.0, "body_count": 1}, "interior": {"compartment_count": 0}})
    sm2 = _SM({"hull": {"lwl": 20.0, "body_count": 2}, "interior": {"compartment_count": 10}})

    b1 = est._estimate_engineering(sm1)
    b2 = est._estimate_engineering(sm2)

    assert b2.engineering_hours > b1.engineering_hours

