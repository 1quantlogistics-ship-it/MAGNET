from dataclasses import dataclass

from magnet.physics.multi_body_hydrostatics import compute_multi_body_hydrostatics


@dataclass
class _P:
    y: float


@dataclass
class _Pos:
    y: float


@dataclass
class _SP:
    position: _Pos


@dataclass
class _Section:
    body_id: str
    x_position: float
    area: float
    half_beam: float
    points: list


@dataclass
class _Geom:
    sections: list


def _make_body_sections(body_id: str, *, offset_y: float) -> list[_Section]:
    # 3 stations, constant area and half_beam.
    # points only used to infer avg_y if body_id doesn't match; we set body_id, but
    # include points for completeness.
    pts = [_SP(_Pos(offset_y)), _SP(_Pos(offset_y))]
    return [
        _Section(body_id=body_id, x_position=0.0, area=10.0, half_beam=2.0, points=pts),
        _Section(body_id=body_id, x_position=5.0, area=10.0, half_beam=2.0, points=pts),
        _Section(body_id=body_id, x_position=10.0, area=10.0, half_beam=2.0, points=pts),
    ]


def test_multibody_hydrostatics_symmetric_catamaran_has_zero_tcb_and_increased_bm():
    # Two identical bodies at +/- 4m. Combined TCB should be ~0.
    bodies = {
        "port": {"_type": "geometry.body", "offset_y_m": 4.0},
        "stbd": {"_type": "geometry.body", "offset_y_m": -4.0},
    }

    geom = _Geom(sections=_make_body_sections("port", offset_y=4.0) + _make_body_sections("stbd", offset_y=-4.0))

    hydro = compute_multi_body_hydrostatics(bodies, geom, draft_m=1.5)
    assert hydro.total_volume_m3 > 0
    assert abs(hydro.combined_tcb_m) < 1e-6
    assert len(hydro.body_results) == 2

    # Now reduce spacing and ensure BM drops (parallel axis term shrinks).
    bodies_narrow = {
        "port": {"_type": "geometry.body", "offset_y_m": 2.0},
        "stbd": {"_type": "geometry.body", "offset_y_m": -2.0},
    }
    geom_narrow = _Geom(sections=_make_body_sections("port", offset_y=2.0) + _make_body_sections("stbd", offset_y=-2.0))
    hydro_narrow = compute_multi_body_hydrostatics(bodies_narrow, geom_narrow, draft_m=1.5)

    assert hydro.bm_transverse_m > hydro_narrow.bm_transverse_m

