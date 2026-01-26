from magnet.bootstrap.blending import blend_hulls
from magnet.bootstrap.hull_library import HullLibrary, LibraryHull


def test_blended_coefficients_are_consistent():
    lib = HullLibrary(
        [
            LibraryHull(hull_id="a", parameters={"cp": 0.60, "cm": 0.80, "cb": 0.48}),
            LibraryHull(hull_id="b", parameters={"cp": 0.80, "cm": 0.90, "cb": 0.72}),
            LibraryHull(hull_id="c", parameters={"cp": 0.70, "cm": 0.85, "cb": 0.595}),
        ]
    )
    res = blend_hulls(library=lib, hull_ids=["a", "b", "c"], weights=[0.3, 0.5, 0.2])
    p = res.parameters
    assert abs(float(p["cb"]) - float(p["cp"]) * float(p["cm"])) < 1e-6

