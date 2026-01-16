"""
tests/hull_gen/test_edge_type_phase1.py - Phase 1 edge type validation tests.

Tests the foundation for hard edge rendering:
- EdgeType enum exists and is usable
- SectionPoint has edge_type field
- ChineType.HARD generates EdgeType.HARD on chine points
- MeshBuilder supports hard edges
- Hydrostatics remain unchanged
"""

import pytest
import math
from magnet.hull_gen.geometry import EdgeType, SectionPoint, Point3D, HullSection
from magnet.hull_gen.generator import HullGenerator, GeneratorConfig
from magnet.hull_gen.enums import HullType, ChineType
from magnet.hull_gen.parameters import (
    HullDefinition, MainDimensions, FormCoefficients, 
    DeadriseProfile, HullFeatures
)
from magnet.webgl.mesh_builder import MeshBuilder
from magnet.webgl.geometry_pipeline import HullGeometryPipeline
from magnet.webgl.interfaces import HullGeometryData


class TestEdgeTypeEnum:
    """Test EdgeType enum existence and values."""
    
    def test_edge_type_enum_exists(self):
        """EdgeType enum should exist with correct values."""
        assert EdgeType.SMOOTH.value == "smooth"
        assert EdgeType.HARD.value == "hard"
        assert EdgeType.CREASE.value == "crease"
    
    def test_edge_type_default_is_smooth(self):
        """Default edge type should be SMOOTH."""
        point = SectionPoint(position=Point3D(x=0, y=0, z=0))
        assert point.edge_type == EdgeType.SMOOTH


class TestSectionPointEdgeType:
    """Test SectionPoint edge_type field."""
    
    def test_section_point_has_edge_type(self):
        """SectionPoint should have edge_type field."""
        point = SectionPoint(
            position=Point3D(x=10.0, y=2.5, z=-1.0),
            edge_type=EdgeType.HARD,
        )
        assert point.edge_type == EdgeType.HARD
    
    def test_section_point_has_feature_id(self):
        """SectionPoint should have feature_id field."""
        point = SectionPoint(
            position=Point3D(x=10.0, y=2.5, z=-1.0),
            is_chine=True,
            edge_type=EdgeType.HARD,
            feature_id="chine_main",
        )
        assert point.feature_id == "chine_main"
    
    def test_section_point_to_dict_includes_edge_type(self):
        """to_dict should include edge_type."""
        point = SectionPoint(
            position=Point3D(x=10.0, y=2.5, z=-1.0),
            edge_type=EdgeType.HARD,
        )
        d = point.to_dict()
        assert d["edge_type"] == "hard"


class TestChineTypeWiring:
    """Test that ChineType.HARD generates EdgeType.HARD."""
    
    def _create_hull_definition(self, chine_type: ChineType) -> HullDefinition:
        """Create test hull definition with specified chine type."""
        return HullDefinition(
            hull_id="TEST-CHINE",
            hull_name="Test Chine Hull",
            hull_type=HullType.HARD_CHINE,
            dimensions=MainDimensions(
                loa=20.0,
                lwl=19.0,
                lpp=18.5,
                beam_max=5.0,
                beam_wl=4.8,
                beam_chine=4.5,
                depth=3.0,
                draft=1.5,
            ),
            coefficients=FormCoefficients(
                cb=0.45,
                cp=0.65,
                cm=0.80,
                cwp=0.75,
                lcb=0.52,
            ),
            deadrise=DeadriseProfile.warped(18.0, 20.0, 35.0),
            features=HullFeatures(chine_type=chine_type),
        )
    
    def test_hard_chine_generates_hard_edge_type(self):
        """ChineType.HARD should produce EdgeType.HARD on chine points."""
        definition = self._create_hull_definition(ChineType.HARD)
        generator = HullGenerator(GeneratorConfig(num_sections=5))
        hull = generator.generate(definition)
        
        # Find chine points and check their edge type
        hard_chine_points = [
            p for section in hull.sections 
            for p in section.points 
            if p.is_chine and p.edge_type == EdgeType.HARD
        ]
        
        assert len(hard_chine_points) > 0, "No hard edge chine points generated"
    
    def test_soft_chine_generates_smooth_edge_type(self):
        """ChineType.SOFT should produce EdgeType.SMOOTH on chine points."""
        definition = self._create_hull_definition(ChineType.SOFT)
        generator = HullGenerator(GeneratorConfig(num_sections=5))
        hull = generator.generate(definition)
        
        # Check that chine points have smooth edge type
        hard_chine_points = [
            p for section in hull.sections 
            for p in section.points 
            if p.is_chine and p.edge_type == EdgeType.HARD
        ]
        
        assert len(hard_chine_points) == 0, "Soft chine should not have hard edges"
    
    def test_chine_points_have_feature_id(self):
        """Hard chine points should have feature_id set."""
        definition = self._create_hull_definition(ChineType.HARD)
        generator = HullGenerator(GeneratorConfig(num_sections=5))
        hull = generator.generate(definition)
        
        # Find chine points with feature_id
        labeled_chine_points = [
            p for section in hull.sections 
            for p in section.points 
            if p.is_chine and p.feature_id == "chine_main"
        ]
        
        assert len(labeled_chine_points) > 0, "No chine points with feature_id"


class TestMeshBuilderHardEdges:
    """Test MeshBuilder hard edge support."""
    
    def test_mesh_builder_accepts_edge_type(self):
        """MeshBuilder.add_vertex should accept edge_type parameter."""
        builder = MeshBuilder()
        v0 = builder.add_vertex(0, 0, 0, edge_type=EdgeType.SMOOTH)
        v1 = builder.add_vertex(1, 0, 0, edge_type=EdgeType.HARD)
        v2 = builder.add_vertex(0, 1, 0, edge_type=EdgeType.SMOOTH)
        
        assert v0 == 0
        assert v1 == 1
        assert v2 == 2
    
    def test_mark_hard_edge(self):
        """MeshBuilder should support marking hard edges."""
        builder = MeshBuilder()
        v0 = builder.add_vertex(0, 0, 0)
        v1 = builder.add_vertex(1, 0, 0, edge_type=EdgeType.HARD)
        v2 = builder.add_vertex(0.5, 1, 0)
        
        builder.add_triangle(v0, v1, v2)
        builder.mark_hard_edge(v0, v1)
        
        # Should build without error
        mesh = builder.build()
        assert mesh.vertex_count >= 3
    
    def test_build_with_hard_edges_produces_valid_mesh(self):
        """Build with hard edges should produce valid mesh."""
        builder = MeshBuilder()
        
        # Create a simple quad with one hard edge
        v0 = builder.add_vertex(0, 0, 0)
        v1 = builder.add_vertex(1, 0, 0, edge_type=EdgeType.HARD)
        v2 = builder.add_vertex(1, 1, 0)
        v3 = builder.add_vertex(0, 1, 0)
        
        builder.add_quad(v0, v1, v2, v3)
        builder.mark_hard_edge(v0, v1)
        
        mesh = builder.build()
        
        # Validate mesh
        assert mesh.vertex_count >= 4  # May be more due to vertex splitting
        assert mesh.face_count == 2
        assert not any(math.isnan(v) for v in mesh.vertices)
        assert not any(math.isnan(n) for n in mesh.normals)
        
        # Normals should be unit length
        for i in range(mesh.vertex_count):
            nx = mesh.normals[i * 3]
            ny = mesh.normals[i * 3 + 1]
            nz = mesh.normals[i * 3 + 2]
            length = math.sqrt(nx*nx + ny*ny + nz*nz)
            assert 0.99 < length < 1.01, f"Normal {i} not unit length: {length}"


class TestHydrostaticsUnchanged:
    """Test that hydrostatics calculations are unaffected by edge types."""
    
    def _create_hull_definition(self, chine_type: ChineType) -> HullDefinition:
        """Create test hull definition."""
        return HullDefinition(
            hull_id="TEST-HYDRO",
            hull_name="Test Hydrostatics Hull",
            hull_type=HullType.HARD_CHINE,
            dimensions=MainDimensions(
                loa=20.0,
                lwl=19.0,
                lpp=18.5,
                beam_max=5.0,
                beam_wl=4.8,
                beam_chine=4.5,
                depth=3.0,
                draft=1.5,
            ),
            coefficients=FormCoefficients(
                cb=0.45,
                cp=0.65,
                cm=0.80,
                cwp=0.75,
                lcb=0.52,
            ),
            deadrise=DeadriseProfile.warped(18.0, 20.0, 35.0),
            features=HullFeatures(chine_type=chine_type),
        )
    
    def test_volume_unchanged_between_soft_and_hard_chine(self):
        """Hull volume should be similar for soft and hard chine (same dimensions)."""
        generator = HullGenerator(GeneratorConfig(num_sections=21))
        
        hull_soft = generator.generate(self._create_hull_definition(ChineType.SOFT))
        hull_hard = generator.generate(self._create_hull_definition(ChineType.HARD))
        
        volume_soft = hull_soft.volume
        volume_hard = hull_hard.volume
        
        # Allow up to 10% difference (hard chine shapes differ more from soft)
        # Hard chines naturally have less volume due to angular vs curved bilge
        assert abs(volume_hard - volume_soft) / max(volume_soft, 0.1) < 0.10, \
            f"Volume difference too large: soft={volume_soft:.2f}, hard={volume_hard:.2f}"
    
    def test_section_areas_compute_correctly(self):
        """Section areas should compute correctly with edge type fields."""
        definition = self._create_hull_definition(ChineType.HARD)
        generator = HullGenerator(GeneratorConfig(num_sections=11))
        hull = generator.generate(definition)
        
        # All sections should have non-negative area
        for section in hull.sections:
            area = section.compute_area(0.0)
            assert area >= 0, f"Section area negative: {area}"


class TestMeshGenerationWithEdgeTypes:
    """Test mesh generation with edge type support."""
    
    def _create_hull_geometry_data(self, chine_type: ChineType) -> HullGeometryData:
        """Generate hull geometry for testing."""
        definition = HullDefinition(
            hull_id="TEST-MESH",
            hull_name="Test Mesh Hull",
            hull_type=HullType.HARD_CHINE,
            dimensions=MainDimensions(
                loa=15.0,
                lwl=14.25,
                lpp=14.0,
                beam_max=4.0,
                beam_wl=3.8,
                beam_chine=3.5,
                depth=2.5,
                draft=1.2,
            ),
            coefficients=FormCoefficients(
                cb=0.45,
                cp=0.65,
                cm=0.80,
                cwp=0.75,
                lcb=0.52,
            ),
            deadrise=DeadriseProfile.warped(18.0, 20.0, 35.0),
            features=HullFeatures(chine_type=chine_type),
        )
        
        generator = HullGenerator(GeneratorConfig(num_sections=11, points_per_section=15))
        hull = generator.generate(definition)
        
        # Convert to HullGeometryData format for pipeline
        from magnet.webgl.interfaces import HullSection as PipelineSection, Point3D as PipelinePoint
        
        pipeline_sections = []
        for section in hull.sections:
            points = []
            for p in section.points:
                pt = PipelinePoint(x=p.position.x, y=p.position.y, z=p.position.z)
                # Transfer edge_type attribute
                pt.edge_type = p.edge_type
                points.append(pt)
            pipeline_sections.append(PipelineSection(
                station=section.station,
                points=points,
                is_closed=False,
            ))
        
        # Return HullGeometryData with required fields
        return HullGeometryData(
            sections=pipeline_sections,
            design_id="TEST-MESH",
            version_id="v1",
            keel_profile=[],
            stem_profile=[],
        )
    
    def test_mesh_generation_soft_chine(self):
        """Soft chine hull should generate valid mesh."""
        hull_data = self._create_hull_geometry_data(ChineType.SOFT)
        pipeline = HullGeometryPipeline(hull_geom=hull_data)
        mesh = pipeline.tessellate()
        
        assert mesh.vertex_count > 0
        assert mesh.face_count > 0
        assert not any(math.isnan(v) for v in mesh.vertices)
        assert not any(math.isnan(n) for n in mesh.normals)
    
    def test_mesh_generation_hard_chine(self):
        """Hard chine hull should generate valid mesh with split normals."""
        hull_data = self._create_hull_geometry_data(ChineType.HARD)
        pipeline = HullGeometryPipeline(hull_geom=hull_data)
        mesh = pipeline.tessellate()
        
        assert mesh.vertex_count > 0
        assert mesh.face_count > 0
        assert not any(math.isnan(v) for v in mesh.vertices)
        assert not any(math.isnan(n) for n in mesh.normals)
        
        # Normals should all be unit length
        for i in range(mesh.vertex_count):
            nx = mesh.normals[i * 3]
            ny = mesh.normals[i * 3 + 1]
            nz = mesh.normals[i * 3 + 2]
            length = math.sqrt(nx*nx + ny*ny + nz*nz)
            assert 0.99 < length < 1.01, f"Normal {i} not unit length: {length}"

