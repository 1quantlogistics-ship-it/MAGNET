from magnet.bootstrap.hull_library import HullLibrary, LibraryHull
from magnet.bootstrap.manifold_blending import ManifoldBlender


def test_manifold_blender_blends_and_projects_to_validity():
    # Validity predicate: loa must be <= 30
    def is_valid(p):
        return float(p.get("loa", 0.0) or 0.0) <= 30.0

    lib = HullLibrary(
        [
            LibraryHull(hull_id="a", parameters={"loa": 20.0, "beam": 5.0}),
            LibraryHull(hull_id="b", parameters={"loa": 40.0, "beam": 6.0}),  # invalid by predicate
            LibraryHull(hull_id="c", parameters={"loa": 28.0, "beam": 5.5}),
        ]
    )

    blender = ManifoldBlender(hull_library=lib, validator=is_valid, variance_to_keep=0.95)

    # Blend toward b strongly would exceed validity, projection should pull back.
    out = blender.blend(hull_ids=["a", "b"], weights=[0.1, 0.9], anchor_hull_id="a")
    assert is_valid(out)
    assert float(out["loa"]) <= 30.0

