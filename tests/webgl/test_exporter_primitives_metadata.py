from magnet.webgl.exporter import GeometryExporter, ExportFormat
from magnet.webgl.schema import MeshData, SceneData, GeometryMode


def test_export_metadata_includes_primitives_custom_block():
    # Minimal scene
    scene = SceneData(
        design_id="d1",
        geometry_mode=GeometryMode.AUTHORITATIVE,
        hull=MeshData(
            mesh_id="hull",
            vertices=[0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0],
            normals=[0.0, 0.0, 1.0] * 3,
            indices=[0, 1, 2],
        ),
        metadata={
            "primitives": {
                "semantics": "diagnostic_only",
                "openings": [{"_id": "o1"}],
                "flow_paths": [{"_id": "f1"}],
                "attachments": [{"_id": "a1"}],
            }
        },
    )

    exporter = GeometryExporter(design_id="d1")
    result = exporter.export_scene(scene=scene, format=ExportFormat.GLB, include_structure=False)
    assert result.success is True
    md = result.metadata.to_dict()
    assert "custom" in md
    assert md["custom"].get("primitives", {}).get("semantics") == "diagnostic_only"
    assert len(md["custom"]["primitives"].get("openings") or []) == 1

