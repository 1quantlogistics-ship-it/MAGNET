from magnet.hull_gen.generator import HullGenerator, GeneratorConfig
from magnet.hull_gen.parameters import (
    DeadriseProfile,
    FormCoefficients,
    HullDefinition,
    HullFeatures,
    MainDimensions,
)
from magnet.hull_gen.geometry import HullGeometry
from magnet.kernel.anchor_tracker import AnchorTracker
from magnet.kernel.topology_classifier import TopologyChangeType


def _make_geom(*, hull_id: str, beam_max: float) -> HullGeometry:
    gen = HullGenerator(config=GeneratorConfig(num_sections=9, points_per_section=21))
    definition = HullDefinition(
        hull_id=hull_id,
        hull_name=hull_id,
        dimensions=MainDimensions(
            loa=18.0,
            lwl=17.0,
            beam_max=beam_max,
            beam_wl=min(beam_max, 4.2),
            depth=2.2,
            draft=0.9,
        ),
        coefficients=FormCoefficients(cb=0.52, cp=0.65, cm=0.80, cwp=0.72, lcb=0.52),
        deadrise=DeadriseProfile.warped(14.0, 16.0, 25.0),
        features=HullFeatures(chine_count=1),
    )
    return gen.generate(definition)


def test_anchor_tracker_preserves_ids_for_small_edits_and_reports_updates():
    geom1 = _make_geom(hull_id="trk", beam_max=4.4)
    geom2 = _make_geom(hull_id="trk", beam_max=4.5)  # small edit

    tracker = AnchorTracker(match_distance_m=1.0, degraded_distance_m=2.0)
    prev = tracker.initialize(geom1)
    cur, report = tracker.update(prev, geom2)

    assert cur
    assert report.updated  # at least one matched anchor

    prev_ids = {a.uuid for a in prev}
    cur_ids = {a.uuid for a in cur}

    # Some previous IDs should remain after a small edit.
    assert prev_ids.intersection(cur_ids)
    assert report.topology_change in (
        TopologyChangeType.INCREMENTAL,
        TopologyChangeType.ADDITIVE,
        TopologyChangeType.SUBTRACTIVE,
        TopologyChangeType.RESTRUCTURE,
    )


def test_anchor_tracker_retires_all_when_geometry_has_no_sections():
    geom1 = _make_geom(hull_id="trk2", beam_max=4.4)
    tracker = AnchorTracker()
    prev = tracker.initialize(geom1)

    empty = HullGeometry(hull_id="trk2", sections=[])
    cur, report = tracker.update(prev, empty)

    assert cur == []
    assert set(report.retired) == {a.uuid for a in prev}
    assert report.topology_change == TopologyChangeType.SUBTRACTIVE

