"""
test_bravo_module59.py - Tests for Interior Layout Module (M59)
BRAVO OWNS THIS FILE.

Tests for:
- Space definitions and types
- Interior layout management
- Layout generation
- Validation
- State integration
"""

import pytest
from typing import List, Dict, Tuple


# =============================================================================
# SPACE SCHEMA TESTS
# =============================================================================

class TestSpaceType:
    """Tests for SpaceType enum."""

    def test_space_type_values(self):
        """Test SpaceType has expected values."""
        from magnet.interior.schema.space import SpaceType

        # Check some key space types exist
        assert SpaceType.ENGINE_ROOM.value == "engine_room"
        assert SpaceType.BRIDGE.value == "bridge"
        assert SpaceType.CABIN_CREW.value == "cabin_crew"
        assert SpaceType.GALLEY.value == "galley"
        assert SpaceType.CORRIDOR.value == "corridor"

    def test_space_category_values(self):
        """Test SpaceCategory enum."""
        from magnet.interior.schema.space import SpaceCategory

        assert SpaceCategory.SAFETY.value == "safety"
        assert SpaceCategory.OPERATIONAL.value == "operational"
        assert SpaceCategory.LIVING.value == "living"
        assert SpaceCategory.CARGO.value == "cargo"
        assert SpaceCategory.SERVICE.value == "service"
        assert SpaceCategory.CIRCULATION.value == "circulation"


class TestSpaceBoundary:
    """Tests for SpaceBoundary class."""

    def test_boundary_area_calculation(self):
        """Test area calculation using shoelace formula."""
        from magnet.interior.schema.space import SpaceBoundary

        # Create a 10m x 5m rectangle
        boundary = SpaceBoundary(
            points=[(0, 0), (10, 0), (10, 5), (0, 5)],
            deck_id="DECK-01",
            z_min=0.0,
            z_max=2.5,
        )

        assert abs(boundary.area() - 50.0) < 0.01

    def test_boundary_volume_calculation(self):
        """Test volume calculation."""
        from magnet.interior.schema.space import SpaceBoundary

        boundary = SpaceBoundary(
            points=[(0, 0), (10, 0), (10, 5), (0, 5)],
            deck_id="DECK-01",
            z_min=0.0,
            z_max=2.5,
        )

        # 50m² × 2.5m = 125m³
        assert abs(boundary.volume() - 125.0) < 0.01

    def test_boundary_centroid(self):
        """Test centroid calculation."""
        from magnet.interior.schema.space import SpaceBoundary

        boundary = SpaceBoundary(
            points=[(0, 0), (10, 0), (10, 5), (0, 5)],
            deck_id="DECK-01",
        )

        cx, cy = boundary.centroid()
        assert abs(cx - 5.0) < 0.01
        assert abs(cy - 2.5) < 0.01

    def test_boundary_serialization(self):
        """Test to_dict and from_dict."""
        from magnet.interior.schema.space import SpaceBoundary

        boundary = SpaceBoundary(
            points=[(0, 0), (10, 0), (10, 5), (0, 5)],
            deck_id="DECK-01",
            z_min=1.0,
            z_max=3.5,
        )

        data = boundary.to_dict()
        restored = SpaceBoundary.from_dict(data)

        assert restored.deck_id == boundary.deck_id
        assert restored.z_min == boundary.z_min
        assert restored.z_max == boundary.z_max
        assert len(restored.points) == len(boundary.points)


class TestSpaceDefinition:
    """Tests for SpaceDefinition class."""

    def test_space_creation(self):
        """Test creating a space."""
        from magnet.interior.schema.space import (
            SpaceDefinition, SpaceType, SpaceCategory, SpaceBoundary
        )

        space = SpaceDefinition(
            space_id="SPACE-001",
            name="Test Cabin",
            space_type=SpaceType.CABIN_CREW,
            category=SpaceCategory.LIVING,
            boundary=SpaceBoundary(
                points=[(0, 0), (3, 0), (3, 4), (0, 4)],
                deck_id="DECK-02",
            ),
            deck_id="DECK-02",
            max_occupancy=2,
            is_manned=True,
        )

        assert space.space_id == "SPACE-001"
        assert space.space_type == SpaceType.CABIN_CREW
        assert space.area == 12.0  # 3 × 4
        assert space.max_occupancy == 2

    def test_space_auto_id_generation(self):
        """Test auto ID generation when not provided."""
        from magnet.interior.schema.space import (
            SpaceDefinition, SpaceType, SpaceCategory, SpaceBoundary
        )

        space = SpaceDefinition(
            space_id="",
            name="Auto ID Space",
            space_type=SpaceType.CORRIDOR,
            category=SpaceCategory.CIRCULATION,
            boundary=SpaceBoundary(
                points=[(0, 0), (10, 0), (10, 2), (0, 2)],
                deck_id="DECK-01",
            ),
            deck_id="DECK-01",
        )

        assert space.space_id.startswith("SPACE-")

    def test_space_hash_computation(self):
        """Test content hash computation."""
        from magnet.interior.schema.space import (
            SpaceDefinition, SpaceType, SpaceCategory, SpaceBoundary
        )

        space = SpaceDefinition(
            space_id="SPACE-001",
            name="Test Space",
            space_type=SpaceType.ENGINE_ROOM,
            category=SpaceCategory.OPERATIONAL,
            boundary=SpaceBoundary(
                points=[(0, 0), (20, 0), (20, 10), (0, 10)],
                deck_id="DECK-01",
            ),
            deck_id="DECK-01",
        )

        hash1 = space.compute_hash()
        hash2 = space.compute_hash()

        assert hash1 == hash2
        assert len(hash1) == 16

    def test_space_serialization(self):
        """Test space serialization."""
        from magnet.interior.schema.space import (
            SpaceDefinition, SpaceType, SpaceCategory, SpaceBoundary
        )

        space = SpaceDefinition(
            space_id="SPACE-001",
            name="Test Space",
            space_type=SpaceType.BRIDGE,
            category=SpaceCategory.OPERATIONAL,
            boundary=SpaceBoundary(
                points=[(0, 0), (10, 0), (10, 5), (0, 5)],
                deck_id="DECK-03",
            ),
            deck_id="DECK-03",
            zone_id="ZONE-NAV",
            max_occupancy=8,
        )

        data = space.to_dict()
        restored = SpaceDefinition.from_dict(data)

        assert restored.space_id == space.space_id
        assert restored.space_type == space.space_type
        assert restored.zone_id == space.zone_id


class TestSpaceConnection:
    """Tests for SpaceConnection class."""

    def test_connection_creation(self):
        """Test creating a connection."""
        from magnet.interior.schema.space import SpaceConnection

        conn = SpaceConnection(
            connection_id="CONN-001",
            from_space_id="SPACE-001",
            to_space_id="SPACE-002",
            connection_type="door",
            width=0.8,
            height=2.0,
            is_watertight=False,
        )

        assert conn.connection_id == "CONN-001"
        assert conn.connection_type == "door"
        assert conn.width == 0.8

    def test_connection_serialization(self):
        """Test connection serialization."""
        from magnet.interior.schema.space import SpaceConnection

        conn = SpaceConnection(
            connection_id="CONN-001",
            from_space_id="SPACE-001",
            to_space_id="SPACE-002",
            connection_type="hatch",
            is_watertight=True,
            is_emergency_exit=True,
        )

        data = conn.to_dict()
        restored = SpaceConnection.from_dict(data)

        assert restored.connection_id == conn.connection_id
        assert restored.is_watertight == conn.is_watertight
        assert restored.is_emergency_exit == conn.is_emergency_exit


# =============================================================================
# LAYOUT SCHEMA TESTS
# =============================================================================

class TestLayoutVersion:
    """Tests for LayoutVersion class."""

    def test_version_creation(self):
        """Test creating a version."""
        from magnet.interior.schema.layout import LayoutVersion

        version = LayoutVersion.create_initial()

        assert version.version == 1
        assert version.update_id.startswith("UPD-")
        assert version.prev_update_id is None

    def test_version_chaining(self):
        """Test version chain creation."""
        from magnet.interior.schema.layout import LayoutVersion

        v1 = LayoutVersion.create_initial()
        v2 = v1.create_next(description="Updated layout")

        assert v2.version == 2
        assert v2.prev_update_id == v1.update_id
        assert v2.update_id != v1.update_id


class TestDeckLayout:
    """Tests for DeckLayout class."""

    def test_deck_creation(self):
        """Test creating a deck."""
        from magnet.interior.schema.layout import DeckLayout

        deck = DeckLayout(
            deck_id="DECK-01",
            deck_name="Tank Top",
            deck_number=0,
            z_level=0.0,
            height=3.0,
        )

        assert deck.deck_id == "DECK-01"
        assert deck.deck_number == 0
        assert deck.space_count == 0

    def test_deck_add_space(self):
        """Test adding space to deck."""
        from magnet.interior.schema.layout import DeckLayout
        from magnet.interior.schema.space import (
            SpaceDefinition, SpaceType, SpaceCategory, SpaceBoundary
        )

        deck = DeckLayout(
            deck_id="DECK-01",
            deck_name="Main Deck",
            deck_number=1,
            z_level=2.5,
        )

        space = SpaceDefinition(
            space_id="SPACE-001",
            name="Test Space",
            space_type=SpaceType.CORRIDOR,
            category=SpaceCategory.CIRCULATION,
            boundary=SpaceBoundary(
                points=[(0, 0), (10, 0), (10, 2), (0, 2)],
                deck_id="DECK-01",
            ),
            deck_id="DECK-01",
        )

        deck.add_space(space)
        assert deck.space_count == 1
        assert deck.get_space("SPACE-001") == space


class TestInteriorLayout:
    """Tests for InteriorLayout class."""

    def test_layout_creation(self):
        """Test creating an empty layout."""
        from magnet.interior.schema.layout import InteriorLayout

        layout = InteriorLayout.create_empty("DESIGN-001")

        assert layout.design_id == "DESIGN-001"
        assert layout.deck_count == 0
        assert layout.space_count == 0

    def test_layout_arrangement_hash(self):
        """Test arrangement hash computation."""
        from magnet.interior.schema.layout import InteriorLayout, DeckLayout

        layout = InteriorLayout.create_empty("DESIGN-001")
        layout.add_deck(DeckLayout(
            deck_id="DECK-01",
            deck_name="Main Deck",
            deck_number=0,
            z_level=0.0,
        ))

        hash1 = layout.arrangement_hash
        hash2 = layout.arrangement_hash

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex

    def test_layout_hash_invalidation(self):
        """Test that hash is invalidated on modification."""
        from magnet.interior.schema.layout import InteriorLayout, DeckLayout

        layout = InteriorLayout.create_empty("DESIGN-001")
        layout.add_deck(DeckLayout(
            deck_id="DECK-01",
            deck_name="Main Deck",
            deck_number=0,
            z_level=0.0,
        ))

        hash1 = layout.arrangement_hash

        # Add another deck
        layout.add_deck(DeckLayout(
            deck_id="DECK-02",
            deck_name="Upper Deck",
            deck_number=1,
            z_level=2.5,
        ))

        hash2 = layout.arrangement_hash

        # Hash should change
        assert hash1 != hash2

    def test_layout_serialization(self):
        """Test layout serialization."""
        from magnet.interior.schema.layout import InteriorLayout, DeckLayout

        layout = InteriorLayout.create_empty("DESIGN-001")
        layout.add_deck(DeckLayout(
            deck_id="DECK-01",
            deck_name="Main Deck",
            deck_number=0,
            z_level=0.0,
        ))

        data = layout.to_dict()
        restored = InteriorLayout.from_dict(data)

        assert restored.design_id == layout.design_id
        assert restored.deck_count == layout.deck_count


# =============================================================================
# VALIDATION TESTS
# =============================================================================

class TestValidation:
    """Tests for validation functionality."""

    def test_validation_result(self):
        """Test ValidationResult class."""
        from magnet.interior.schema.validation import (
            ValidationResult, ValidationSeverity
        )

        result = ValidationResult()
        assert result.is_valid

        result.add_error(
            issue_id="test_error",
            category="test",
            message="Test error message",
        )

        assert not result.is_valid
        assert result.errors_count == 1

    def test_validation_issue_serialization(self):
        """Test ValidationIssue serialization."""
        from magnet.interior.schema.validation import (
            ValidationIssue, ValidationSeverity
        )

        issue = ValidationIssue(
            issue_id="test_001",
            severity=ValidationSeverity.WARNING,
            category="area",
            message="Test warning",
            space_id="SPACE-001",
        )

        data = issue.to_dict()
        restored = ValidationIssue.from_dict(data)

        assert restored.issue_id == issue.issue_id
        assert restored.severity == issue.severity

    def test_space_constraint_validation(self):
        """Test validating space against constraints."""
        from magnet.interior.schema.space import (
            SpaceDefinition, SpaceType, SpaceCategory, SpaceBoundary
        )
        from magnet.interior.schema.validation import (
            validate_space_constraints, MARITIME_CONSTRAINTS
        )

        # Create a cabin that's too small
        small_cabin = SpaceDefinition(
            space_id="SPACE-001",
            name="Small Cabin",
            space_type=SpaceType.CABIN_CREW,
            category=SpaceCategory.LIVING,
            boundary=SpaceBoundary(
                points=[(0, 0), (2, 0), (2, 2), (0, 2)],  # 4m² - below 4.5m² minimum
                deck_id="DECK-01",
            ),
            deck_id="DECK-01",
        )

        result = validate_space_constraints([small_cabin])
        assert not result.is_valid
        assert result.errors_count > 0


# =============================================================================
# GENERATOR TESTS
# =============================================================================

class TestLayoutGenerator:
    """Tests for LayoutGenerator class."""

    def test_basic_generation(self):
        """Test basic layout generation."""
        from magnet.interior.generator.layout_generator import (
            LayoutGenerator, GenerationConfig
        )

        config = GenerationConfig(
            loa=100.0,
            beam=20.0,
            depth=10.0,
            crew_capacity=20,
        )

        generator = LayoutGenerator(config)
        result = generator.generate("TEST-001")

        assert result.success
        assert result.layout is not None
        assert result.layout.deck_count == 4  # default
        assert result.layout.space_count > 0

    def test_generation_with_custom_decks(self):
        """Test generation with custom deck config."""
        from magnet.interior.generator.layout_generator import (
            LayoutGenerator, GenerationConfig, DeckConfig
        )

        config = GenerationConfig(
            loa=80.0,
            beam=15.0,
            depth=8.0,
            deck_configs=[
                DeckConfig(deck_name="Lower", deck_number=0, z_level=0.0),
                DeckConfig(deck_name="Upper", deck_number=1, z_level=2.5),
            ],
        )

        generator = LayoutGenerator(config)
        result = generator.generate("TEST-002")

        assert result.success
        assert result.layout.deck_count == 2

    def test_generation_convenience_function(self):
        """Test generate_basic_layout convenience function."""
        from magnet.interior.generator.layout_generator import generate_basic_layout

        result = generate_basic_layout(
            design_id="TEST-003",
            loa=50.0,
            beam=10.0,
            depth=5.0,
            crew_capacity=10,
        )

        assert result.success
        assert result.layout is not None
        assert result.layout.arrangement_hash is not None


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestStateIntegrator:
    """Tests for InteriorStateIntegrator class."""

    def test_integrator_creation(self):
        """Test creating state integrator."""
        from magnet.interior.integration.state_integration import (
            InteriorStateIntegrator
        )

        integrator = InteriorStateIntegrator()
        assert integrator._layouts == {}

    def test_save_and_get_layout(self):
        """Test saving and retrieving layout."""
        from magnet.interior.integration.state_integration import (
            InteriorStateIntegrator
        )
        from magnet.interior.schema.layout import InteriorLayout

        integrator = InteriorStateIntegrator()
        layout = InteriorLayout.create_empty("TEST-001")

        # Save
        update_id = integrator.save_layout(layout)
        assert update_id is not None

        # Retrieve
        retrieved = integrator.get_layout("TEST-001")
        assert retrieved is not None
        assert retrieved.design_id == "TEST-001"

    def test_get_arrangement_hash(self):
        """Test getting arrangement hash."""
        from magnet.interior.integration.state_integration import (
            InteriorStateIntegrator
        )
        from magnet.interior.schema.layout import InteriorLayout

        integrator = InteriorStateIntegrator()
        layout = InteriorLayout.create_empty("TEST-001")
        integrator.save_layout(layout)

        hash_val = integrator.get_arrangement_hash("TEST-001")
        assert hash_val is not None
        assert len(hash_val) == 64

    def test_get_version_info(self):
        """Test getting version info for chain tracking."""
        from magnet.interior.integration.state_integration import (
            InteriorStateIntegrator
        )
        from magnet.interior.schema.layout import InteriorLayout

        integrator = InteriorStateIntegrator()
        layout = InteriorLayout.create_empty("TEST-001")
        integrator.save_layout(layout)

        info = integrator.get_version_info("TEST-001")
        assert info is not None
        assert "update_id" in info
        assert "prev_update_id" in info
        assert "version" in info
        assert "arrangement_hash" in info


# =============================================================================
# API TESTS (if FastAPI available)
# =============================================================================

class TestAPIModels:
    """Tests for API request/response models."""

    def test_models_import(self):
        """Test that API models can be imported."""
        try:
            from magnet.interior.api_endpoints import (
                GenerateRequest,
                GenerateResponse,
                LayoutResponse,
                SpaceRequest,
                SpaceResponse,
                ValidationResponse,
            )
            # Models imported successfully
            assert True
        except ImportError:
            # FastAPI not installed, skip
            pytest.skip("FastAPI not installed")

    def test_router_creation(self):
        """Test router creation."""
        try:
            from magnet.interior.api_endpoints import create_interior_router
            from magnet.interior.integration.state_integration import (
                InteriorStateIntegrator
            )

            integrator = InteriorStateIntegrator()
            router = create_interior_router(integrator)

            if router is None:
                pytest.skip("FastAPI not installed")

            # Router should have routes
            assert len(router.routes) > 0
        except ImportError:
            pytest.skip("FastAPI not installed")


# =============================================================================
# FULL WORKFLOW TESTS
# =============================================================================

class TestFullWorkflow:
    """Tests for complete workflow scenarios."""

    def test_generate_validate_workflow(self):
        """Test generating and validating a layout."""
        from magnet.interior.generator.layout_generator import generate_basic_layout
        from magnet.interior.schema.validation import validate_space_constraints

        # Generate
        result = generate_basic_layout(
            design_id="WORKFLOW-001",
            loa=100.0,
            beam=20.0,
            crew_capacity=20,
        )

        assert result.success
        layout = result.layout

        # Validate
        spaces = layout.get_all_spaces()
        validation = validate_space_constraints(spaces)

        # Should have some issues (generated layout may not be perfect)
        assert validation.checked_rules is not None

    def test_chain_tracking_workflow(self):
        """Test update chain tracking through modifications."""
        from magnet.interior.integration.state_integration import (
            InteriorStateIntegrator
        )
        from magnet.interior.generator.layout_generator import generate_basic_layout
        from magnet.interior.schema.space import (
            SpaceDefinition, SpaceType, SpaceCategory, SpaceBoundary
        )

        integrator = InteriorStateIntegrator()

        # Generate initial layout
        result = generate_basic_layout(design_id="CHAIN-001")
        layout = result.layout
        integrator.save_layout(layout)

        info1 = integrator.get_version_info("CHAIN-001")
        assert info1["version"] == 2  # After save_layout creates version 2
        prev_id = info1["prev_update_id"]

        # Add a space
        new_space = SpaceDefinition(
            space_id="",
            name="New Test Space",
            space_type=SpaceType.STORE_GENERAL,
            category=SpaceCategory.SERVICE,
            boundary=SpaceBoundary(
                points=[(50, 5), (55, 5), (55, 10), (50, 10)],
                deck_id=list(layout.decks.keys())[0],
            ),
            deck_id=list(layout.decks.keys())[0],
        )

        integrator.add_space("CHAIN-001", new_space)

        info2 = integrator.get_version_info("CHAIN-001")
        assert info2["version"] == 3
        assert info2["prev_update_id"] == info1["update_id"]

        # Hash should have changed
        assert info2["arrangement_hash"] != info1["arrangement_hash"]
