"""
Unit tests for production material takeoff.

Tests MaterialTakeoff calculator with v1.1 field names.
"""

import pytest
from magnet.production.material_takeoff import MaterialTakeoff
from magnet.production.models import MaterialItem, MaterialTakeoffResult, MATERIAL_DENSITIES
from magnet.production.enums import MaterialCategory


class MockStateManager:
    """Mock StateManager for testing."""

    def __init__(self, data: dict = None):
        self._data = data or {}

    def get(self, key: str, default=None):
        """Get value by dotted key."""
        keys = key.split(".")
        current = self._data
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current


class TestMaterialTakeoff:
    """Tests for MaterialTakeoff calculator."""

    @pytest.fixture
    def calculator(self):
        """Create calculator instance."""
        return MaterialTakeoff()

    @pytest.fixture
    def state_25m_workboat(self):
        """Create state for 25m aluminum workboat."""
        return MockStateManager({
            "hull": {
                "lwl": 25.0,
                "beam": 6.0,
                "depth": 3.0,
            },
            "structure": {
                "material": "aluminum_5083",
                "bottom_plate_thickness_mm": 8.0,
                "side_plate_thickness_mm": 6.0,
                "deck_plate_thickness_mm": 5.0,
                "frame_spacing_mm": 500.0,
            },
        })

    def test_basic_calculation(self, calculator, state_25m_workboat):
        """Test basic material takeoff calculation."""
        result = calculator.calculate(state_25m_workboat)

        assert isinstance(result, MaterialTakeoffResult)
        assert result.item_count > 0
        assert result.plate_area_m2 > 0
        assert result.profile_length_m > 0
        assert result.total_weight_kg > 0

    def test_empty_dimensions_returns_empty_result(self, calculator):
        """Test empty dimensions return empty result."""
        state = MockStateManager({})
        result = calculator.calculate(state)

        assert result.item_count == 0
        assert result.total_weight_kg == 0

    def test_zero_dimensions_returns_empty_result(self, calculator):
        """Test zero dimensions return empty result."""
        state = MockStateManager({
            "hull": {"lwl": 0, "beam": 0, "depth": 0}
        })
        result = calculator.calculate(state)

        assert result.item_count == 0
        assert result.total_weight_kg == 0

    def test_plate_items_created(self, calculator, state_25m_workboat):
        """Test plate items are created."""
        result = calculator.calculate(state_25m_workboat)

        plate_items = [i for i in result.items if i.category == MaterialCategory.PLATE]
        assert len(plate_items) >= 4  # Bottom, side, deck, transom, bulkheads

        # Check bottom shell
        bottom = next((i for i in plate_items if "Bottom" in i.description), None)
        assert bottom is not None
        assert bottom.thickness_mm == 8.0  # From state
        assert bottom.area_m2 > 0
        assert bottom.weight_kg > 0

    def test_profile_items_created(self, calculator, state_25m_workboat):
        """Test profile items are created."""
        result = calculator.calculate(state_25m_workboat)

        profile_items = [i for i in result.items if i.category == MaterialCategory.PROFILE]
        assert len(profile_items) >= 4  # Longitudinals, frames, deck beams, keel

        # Check frames
        frames = next((i for i in profile_items if "Frame" in i.description), None)
        assert frames is not None
        assert frames.length_m > 0
        assert frames.weight_kg > 0

    def test_scrap_factor_applied(self, calculator, state_25m_workboat):
        """Test scrap factor is applied to total weight."""
        result = calculator.calculate(state_25m_workboat)

        base_weight = result.plate_weight_kg + result.profile_weight_kg
        expected_total = base_weight * 1.15  # Default scrap factor

        assert abs(result.total_weight_kg - expected_total) < 0.1

    def test_custom_scrap_factor(self, state_25m_workboat):
        """Test custom scrap factor."""
        calculator = MaterialTakeoff(scrap_factor=1.25)
        result = calculator.calculate(state_25m_workboat)

        assert result.scrap_factor == 1.25
        base_weight = result.plate_weight_kg + result.profile_weight_kg
        expected_total = base_weight * 1.25

        assert abs(result.total_weight_kg - expected_total) < 0.1

    def test_material_density_used(self, calculator):
        """Test correct material density is used for plates."""
        state = MockStateManager({
            "hull": {"lwl": 20.0, "beam": 5.0, "depth": 2.5},
            "structure": {"material": "steel_mild"},
        })
        result = calculator.calculate(state)

        # Steel is ~3x heavier than aluminum per volume
        alu_state = MockStateManager({
            "hull": {"lwl": 20.0, "beam": 5.0, "depth": 2.5},
            "structure": {"material": "aluminum_5083"},
        })
        alu_result = calculator.calculate(alu_state)

        # Compare plate weights (profiles use fixed kg/m, so density doesn't affect them)
        weight_ratio = result.plate_weight_kg / alu_result.plate_weight_kg
        expected_ratio = MATERIAL_DENSITIES["steel_mild"] / MATERIAL_DENSITIES["aluminum_5083"]
        # Plate weight should scale with density ratio
        assert abs(weight_ratio - expected_ratio) < 0.1

    def test_frame_spacing_affects_profiles(self, calculator):
        """Test frame spacing affects profile quantities."""
        # Smaller spacing = more frames
        small_spacing = MockStateManager({
            "hull": {"lwl": 20.0, "beam": 5.0, "depth": 2.5},
            "structure": {"frame_spacing_mm": 300.0},
        })
        large_spacing = MockStateManager({
            "hull": {"lwl": 20.0, "beam": 5.0, "depth": 2.5},
            "structure": {"frame_spacing_mm": 600.0},
        })

        small_result = calculator.calculate(small_spacing)
        large_result = calculator.calculate(large_spacing)

        # Smaller spacing should have more profile length
        assert small_result.profile_length_m > large_result.profile_length_m

    def test_larger_vessel_more_material(self, calculator):
        """Test larger vessel has more material."""
        small = MockStateManager({
            "hull": {"lwl": 15.0, "beam": 4.0, "depth": 2.0},
        })
        large = MockStateManager({
            "hull": {"lwl": 30.0, "beam": 8.0, "depth": 4.0},
        })

        small_result = calculator.calculate(small)
        large_result = calculator.calculate(large)

        # Large vessel should have significantly more material
        assert large_result.total_weight_kg > small_result.total_weight_kg * 4

    def test_inner_bottom_for_large_vessels(self, calculator):
        """Test inner bottom added for vessels > 15m."""
        small = MockStateManager({
            "hull": {"lwl": 12.0, "beam": 4.0, "depth": 2.0},
        })
        large = MockStateManager({
            "hull": {"lwl": 20.0, "beam": 6.0, "depth": 3.0},
        })

        small_result = calculator.calculate(small)
        large_result = calculator.calculate(large)

        small_has_inner = any("Inner Bottom" in i.description for i in small_result.items)
        large_has_inner = any("Inner Bottom" in i.description for i in large_result.items)

        assert not small_has_inner
        assert large_has_inner

    def test_result_to_dict(self, calculator, state_25m_workboat):
        """Test result serialization."""
        result = calculator.calculate(state_25m_workboat)
        data = result.to_dict()

        assert "items" in data
        assert "summary" in data
        assert "item_count" in data
        assert data["item_count"] == result.item_count
        assert data["summary"]["total_weight_kg"] == round(result.total_weight_kg, 1)

    def test_item_ids_unique(self, calculator, state_25m_workboat):
        """Test all item IDs are unique."""
        result = calculator.calculate(state_25m_workboat)
        ids = [item.item_id for item in result.items]

        assert len(ids) == len(set(ids))

    def test_item_id_prefixes(self, calculator, state_25m_workboat):
        """Test item IDs have correct prefixes."""
        result = calculator.calculate(state_25m_workboat)

        for item in result.items:
            if item.category == MaterialCategory.PLATE:
                assert item.item_id.startswith("PLT-")
            elif item.category == MaterialCategory.PROFILE:
                assert item.item_id.startswith("PRF-")


class TestMaterialItem:
    """Tests for MaterialItem dataclass."""

    def test_create_plate_item(self):
        """Test creating plate item."""
        item = MaterialItem(
            item_id="PLT-0001",
            category=MaterialCategory.PLATE,
            material_type="aluminum_5083",
            description="Bottom Shell",
            thickness_mm=8.0,
            area_m2=150.0,
            weight_kg=3192.0,
            unit="m2",
            quantity=150.0,
        )

        assert item.item_id == "PLT-0001"
        assert item.category == MaterialCategory.PLATE
        assert item.thickness_mm == 8.0
        assert item.area_m2 == 150.0

    def test_create_profile_item(self):
        """Test creating profile item."""
        item = MaterialItem(
            item_id="PRF-0001",
            category=MaterialCategory.PROFILE,
            material_type="aluminum_5083",
            description="Longitudinal Stiffeners",
            length_m=500.0,
            weight_kg=1750.0,
            unit="m",
            quantity=500.0,
        )

        assert item.item_id == "PRF-0001"
        assert item.category == MaterialCategory.PROFILE
        assert item.length_m == 500.0

    def test_item_to_dict(self):
        """Test item serialization."""
        item = MaterialItem(
            item_id="PLT-0001",
            category=MaterialCategory.PLATE,
            material_type="aluminum_5083",
            description="Bottom Shell",
            thickness_mm=8.0,
            area_m2=150.0,
            weight_kg=3192.0,
        )

        data = item.to_dict()
        assert data["item_id"] == "PLT-0001"
        assert data["category"] == "plate"
        assert data["thickness_mm"] == 8.0


class TestMaterialDensities:
    """Tests for material density constants."""

    def test_aluminum_densities(self):
        """Test aluminum densities are reasonable."""
        assert 2600 <= MATERIAL_DENSITIES["aluminum_5083"] <= 2750
        assert 2600 <= MATERIAL_DENSITIES["aluminum_5086"] <= 2750
        assert 2650 <= MATERIAL_DENSITIES["aluminum_6061"] <= 2750

    def test_steel_densities(self):
        """Test steel densities are reasonable."""
        assert 7800 <= MATERIAL_DENSITIES["steel_mild"] <= 7900
        assert 7800 <= MATERIAL_DENSITIES["steel_hts"] <= 7900

    def test_composite_densities(self):
        """Test composite densities are reasonable."""
        assert 1500 <= MATERIAL_DENSITIES["composite"] <= 2000
        assert 1700 <= MATERIAL_DENSITIES["frp"] <= 1900
