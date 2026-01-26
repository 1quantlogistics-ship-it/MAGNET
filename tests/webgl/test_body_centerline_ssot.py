"""
Body centerline SSOT test

Tessellation must prefer HullGeometryData.metadata.body_centerline_y_by_body
over per-section "keel y" inference.
"""

from magnet.webgl.geometry_pipeline import HullGeometryPipeline
from magnet.webgl.interfaces import HullGeometryData, HullSection, SectionVertex, Point3D


def test_tessellation_uses_body_centerline_metadata_when_present():
    # Body centerline is y=10.0 in ship coordinates, but the first point is WRONG (y=9.0),
    # simulating a malformed keel point. Tessellation must still mirror about 10.0.
    y0 = 10.0
    bid = "bodyA"

    s0 = HullSection(
        station=0.0,
        body_id=bid,
        points=[
            SectionVertex(position=Point3D(x=0.0, y=9.0, z=0.0)),   # wrong keel y
            SectionVertex(position=Point3D(x=0.0, y=10.7, z=1.0)),
            SectionVertex(position=Point3D(x=0.0, y=10.0, z=2.0)),  # correct centerline at deck
        ],
    )
    s1 = HullSection(
        station=1.0,
        body_id=bid,
        points=[
            SectionVertex(position=Point3D(x=1.0, y=9.0, z=0.0)),   # wrong keel y
            SectionVertex(position=Point3D(x=1.0, y=10.7, z=1.0)),
            SectionVertex(position=Point3D(x=1.0, y=10.0, z=2.0)),
        ],
    )

    hg = HullGeometryData(
        design_id="d",
        version_id="v1",
        sections=[s0, s1],
        keel_profile=[],
        stem_profile=[],
        openings=[],
        flow_paths=[],
        attachments=[],
        metadata={"surface_definition": "panelized", "body_centerline_y_by_body": {bid: y0}},
    )

    pipeline = HullGeometryPipeline(hull_geom=hg)
    mesh = pipeline.tessellate_with_options(hg.sections, faceted=True, panel_edges_hard=True)

    # Expect a mirrored vertex at y = 2*y0 - 10.7 = 9.3
    ys = [mesh.vertices[i + 1] for i in range(0, len(mesh.vertices), 3)]
    assert any(abs(y - 9.3) < 1e-6 for y in ys), "Expected mirrored vertex about metadata centerline_y"

