from magnet.bootstrap.hull_library import HullLibrary, LibraryHull


def test_hull_library_add_get_and_parameter_names():
    lib = HullLibrary()
    lib.add(LibraryHull(hull_id="h1", parameters={"loa": 20.0, "beam": 5.0}))
    lib.add(LibraryHull(hull_id="h2", parameters={"loa": 22.0, "draft": 1.8}))

    assert lib.get("h1").parameters["loa"] == 20.0
    assert set(lib.parameter_names()) == {"beam", "draft", "loa"}


def test_hull_library_search_by_parameters_returns_nearest():
    lib = HullLibrary(
        [
            LibraryHull(hull_id="a", parameters={"x": 0.0}),
            LibraryHull(hull_id="b", parameters={"x": 10.0}),
            LibraryHull(hull_id="c", parameters={"x": 20.0}),
        ]
    )
    res = lib.search_by_parameters({"x": 12.0}, k=2)
    assert [r.hull.hull_id for r in res] == ["b", "c"]

