from magnet.core.incremental_state import IncrementalStateManager


def test_incremental_state_invalidates_only_dependents():
    sm = IncrementalStateManager()
    sm.register_computation("c1", depends_on=["a"])
    sm.register_computation("c2", depends_on=["b"])
    sm.register_computation("c3", depends_on=["a", "b"])

    # Prime cache
    sm.update_parameter("a", 1)
    sm.update_parameter("b", 2)
    v1 = sm.get_computation("c1", lambda st: st["a"] + 10)
    v2 = sm.get_computation("c2", lambda st: st["b"] + 20)
    v3 = sm.get_computation("c3", lambda st: st["a"] + st["b"])
    assert (v1, v2, v3) == (11, 22, 3)

    # Change only "a" should invalidate c1 and c3, but not c2
    invalidated = sm.update_parameter("a", 5)
    assert set(invalidated) == {"c1", "c3"}

    # c2 should remain cached
    v2_again = sm.get_computation("c2", lambda st: (_ for _ in ()).throw(AssertionError("should be cached")))
    assert v2_again == 22

    # c1/c3 should recompute
    assert sm.get_computation("c1", lambda st: st["a"] + 10) == 15
    assert sm.get_computation("c3", lambda st: st["a"] + st["b"]) == 7

