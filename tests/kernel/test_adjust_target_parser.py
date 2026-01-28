from magnet.kernel.stdlib.parser import parse


def test_parse_adjust_statement():
    prog = parse(
        'ADJUST section_metric:deadrise_deg_at_chine AT station_range=(0.8, 1.0) body_id="main" BY +5deg\n'
    )
    st = prog.statements[0]
    assert st.observable_id == "section_metric:deadrise_deg_at_chine"
    assert st.scope["station_range"] == (0.8, 1.0)
    assert st.scope["body_id"] == "main"
    assert st.delta == 5.0
    assert st.unit == "deg"


def test_parse_target_statement():
    prog = parse('TARGET section_metric:max_half_beam_m AT station=0.25 = 0.20m\n')
    st = prog.statements[0]
    assert st.observable_id == "section_metric:max_half_beam_m"
    assert st.scope["station"] == 0.25
    assert st.value == 0.20
    assert st.unit == "m"

