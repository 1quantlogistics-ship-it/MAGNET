from magnet.kernel.program_executor import execute_program


def _seed_state():
    # Minimal compiled hull: one body, two sections, one surface (smooth).
    return {
        "resources": {
            "main": {
                "_type": "geometry.body",
                "_id": "main",
                "body_type": "seed",
                "physics_category": "surface_piercing",
                "offset_x_m": 0.0,
                "offset_y_m": 0.0,
                "offset_z_m": 0.0,
            },
            "s0": {
                "_type": "geometry.section",
                "_id": "s0",
                "body_id": "main",
                "station": 0.0,
                # z strictly increasing
                "points": [[0.0, -1.0], [2.0, -0.10], [1.0, 1.0]],
            },
            "s1": {
                "_type": "geometry.section",
                "_id": "s1",
                "body_id": "main",
                "station": 1.0,
                "points": [[0.0, -1.0], [2.0, -0.10], [1.0, 1.0]],
            },
            "surf": {
                "_type": "geometry.surface",
                "_id": "surf",
                "body_id": "main",
                "definition": "lofted",
                "surface_definition": "smooth",
                "surface_type": "hull_shell",
                "section_ids": ["s0", "s1"],
            },
        },
        "metadata": {},
    }


def test_execute_program_adjust_deadrise_sets_receipt_and_cache():
    state = _seed_state()
    program = "\n".join(
        [
            'ADJUST section_metric:deadrise_deg_at_chine AT station=0.0 body_id="main" BY +5deg',
        ]
    )
    res = execute_program(program, initial_state=state, dry_run=True, validate=False)
    assert res.success is True, res.errors

    # Must write receipt + witness cache atomically as actions.
    paths = [a.path for a in res.actions if a.op == "SET"]
    assert "metadata.last_edit_receipt" in paths
    assert "metadata.anchor_witness_cache" in paths

    receipt = next(a.value for a in res.actions if a.op == "SET" and a.path == "metadata.last_edit_receipt")
    assert receipt["op"] == "ADJUST"
    assert receipt["observable_id"] == "section_metric:deadrise_deg_at_chine"
    assert receipt["unit"] == "deg"
    assert "achieved" in receipt and receipt["achieved"]
    assert receipt["achieved"][0]["section_id"] == "s0"
    wi = receipt["achieved"][0]["witness_index"]
    assert isinstance(wi, int)

    # The section update must preserve identity and point count.
    sec_action = next(a for a in res.actions if a.op == "SET" and a.path == "resources.s0")
    pts = sec_action.value["points"]
    assert len(pts) == 3
    assert pts[1][0] == 2.0  # chine-like point y unchanged; z moved


def test_execute_program_two_adjusts_reuse_witness_cache():
    state = _seed_state()
    program = "\n".join(
        [
            'ADJUST section_metric:deadrise_deg_at_chine AT station=0.0 body_id="main" BY +2deg',
            'ADJUST section_metric:deadrise_deg_at_chine AT station=0.0 body_id="main" BY +2deg',
        ]
    )
    res = execute_program(program, initial_state=state, dry_run=True, validate=False)
    assert res.success is True, res.errors

    # Anchor cache should contain a stable witness entry for s0.
    cache = next(a.value for a in res.actions if a.op == "SET" and a.path == "metadata.anchor_witness_cache")
    assert "main:s0:section_metric:deadrise_deg_at_chine" in cache
    assert cache["main:s0:section_metric:deadrise_deg_at_chine"]["witness_index"] == 1

