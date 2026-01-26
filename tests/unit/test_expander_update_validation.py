from magnet.kernel.stdlib.parser import parse
from magnet.kernel.stdlib.expander import expand


def test_update_validates_geometry_section_points_shape():
    """
    Regression: UPDATE must validate resource grammar, not just CREATE.
    Without this, LLM can corrupt geometry.section.points via UPDATE and it will commit.
    """
    state = {
        "resources": {
            "s1": {
                "_type": "geometry.section",
                "_id": "s1",
                "station": 0.5,
                "body_id": "main",
                "definition_type": "polygon",
                "points": [[0.0, 0.0], [1.0, -1.0], [1.0, 1.0]],
            }
        }
    }

    program_text = """
UPDATE s1 { points: [[0.0, 0.0, -2.0], [1.0, 0.0, -1.0]] }
"""
    ast = parse(program_text)
    result = expand(ast, state)
    # Contract: UPDATE validates AND normalizes common LLM output shapes.
    # [x,y,z] triples are accepted and normalized to canonical [y,z] pairs (drop x).
    assert not result.errors, result.errors
    action = next(a for a in result.actions if a.op == "SET" and a.path == "resources.s1")
    assert action.value["points"] == [[0.0, -2.0], [0.0, -1.0]]


