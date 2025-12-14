"""
Unit tests for production planning validator.

Tests ProductionPlanningValidator with v1.1 field names.
"""

import pytest
from datetime import date, datetime, timezone
from magnet.production.validators import (
    ProductionPlanningValidator,
    get_production_planning_definition,
    register_production_validators,
    determinize_dict,
)
from magnet.validators.taxonomy import (
    ValidatorState,
    ValidationResult,
    ValidatorCategory,
)


class MockStateManager:
    """Mock StateManager for testing."""

    def __init__(self, data: dict = None):
        self._data = data or {}
        self._writes = {}

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

    def write(self, key: str, value, agent: str, description: str):
        """Record a write operation."""
        self._writes[key] = {
            "value": value,
            "agent": agent,
            "description": description,
        }

    def set(self, key: str, value, source=None):
        """Set value by dotted key."""
        self._writes[key] = {"value": value, "agent": source or "", "description": ""}

    def get_written(self, key: str):
        """Get a written value."""
        if key in self._writes:
            return self._writes[key]["value"]
        return None


class TestProductionPlanningValidator:
    """Tests for ProductionPlanningValidator."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        defn = get_production_planning_definition()
        return ProductionPlanningValidator(defn)

    @pytest.fixture
    def state_25m_workboat(self):
        """Create state for 25m workboat."""
        return MockStateManager({
            "hull": {
                "lwl": 25.0,
                "beam": 6.0,
                "depth": 3.0,
            },
            "structure": {
                "material": "aluminum_5083",
                "frame_spacing_mm": 500.0,
                "bottom_plate_thickness_mm": 8.0,
                "side_plate_thickness_mm": 6.0,
                "deck_plate_thickness_mm": 5.0,
            },
        })

    @pytest.fixture
    def empty_context(self):
        """Empty validation context."""
        return {}

    def test_successful_validation(self, validator, state_25m_workboat, empty_context):
        """Test successful validation."""
        result = validator.validate(state_25m_workboat, empty_context)

        assert result.state in [ValidatorState.PASSED, ValidatorState.WARNING]
        assert result.error_count == 0

    def test_missing_dimensions_fails(self, validator, empty_context):
        """Test missing dimensions causes failure."""
        state = MockStateManager({})
        result = validator.validate(state, empty_context)

        assert result.state == ValidatorState.FAILED
        assert result.error_count > 0
        assert any("dimension" in f.message.lower() for f in result.findings)

    def test_zero_dimensions_fails(self, validator, empty_context):
        """Test zero dimensions causes failure."""
        state = MockStateManager({
            "hull": {"lwl": 0, "beam": 5.0, "depth": 2.5}
        })
        result = validator.validate(state, empty_context)

        assert result.state == ValidatorState.FAILED
        assert result.error_count > 0

    def test_writes_material_takeoff(self, validator, state_25m_workboat, empty_context):
        """Test material takeoff is written to state."""
        validator.validate(state_25m_workboat, empty_context)

        takeoff = state_25m_workboat.get_written("production.material_takeoff")
        assert takeoff is not None
        assert "items" in takeoff
        assert "summary" in takeoff

    def test_writes_assembly_sequence(self, validator, state_25m_workboat, empty_context):
        """Test assembly sequence is written to state."""
        validator.validate(state_25m_workboat, empty_context)

        sequence = state_25m_workboat.get_written("production.assembly_sequence")
        assert sequence is not None
        assert "packages" in sequence
        assert "summary" in sequence

    def test_writes_build_schedule(self, validator, state_25m_workboat, empty_context):
        """Test build schedule is written to state."""
        validator.validate(state_25m_workboat, empty_context)

        schedule = state_25m_workboat.get_written("production.build_schedule")
        assert schedule is not None
        assert "milestones" in schedule
        assert "summary" in schedule

    def test_writes_summary(self, validator, state_25m_workboat, empty_context):
        """Test production summary is written to state."""
        validator.validate(state_25m_workboat, empty_context)

        summary = state_25m_workboat.get_written("production.summary")
        assert summary is not None
        assert "material_weight_kg" in summary
        assert "work_packages" in summary
        assert "total_work_hours" in summary
        assert "build_duration_days" in summary

    def test_context_start_date_used(self, validator, state_25m_workboat):
        """Test start date from context is used."""
        context = {"start_date": date(2025, 6, 1)}
        validator.validate(state_25m_workboat, context)

        schedule = state_25m_workboat.get_written("production.build_schedule")
        assert schedule["summary"]["start_date"] == "2025-06-01"

    def test_context_start_date_string(self, validator, state_25m_workboat):
        """Test start date as string is parsed."""
        context = {"start_date": "2025-07-01"}
        validator.validate(state_25m_workboat, context)

        schedule = state_25m_workboat.get_written("production.build_schedule")
        assert schedule["summary"]["start_date"] == "2025-07-01"

    def test_default_material_used(self, validator, empty_context):
        """Test default material is used when not specified."""
        state = MockStateManager({
            "hull": {"lwl": 20.0, "beam": 5.0, "depth": 2.5},
            # No structure.material
        })
        result = validator.validate(state, empty_context)

        assert result.state in [ValidatorState.PASSED, ValidatorState.WARNING]

        # Material takeoff should still work with default aluminum
        takeoff = state.get_written("production.material_takeoff")
        assert takeoff is not None

    def test_result_has_timing(self, validator, state_25m_workboat, empty_context):
        """Test result has timing information."""
        result = validator.validate(state_25m_workboat, empty_context)

        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.completed_at >= result.started_at

    def test_result_validator_id(self, validator, state_25m_workboat, empty_context):
        """Test result has correct validator ID."""
        result = validator.validate(state_25m_workboat, empty_context)

        assert result.validator_id == "production/planning"


class TestValidatorDefinition:
    """Tests for validator definition."""

    def test_definition_properties(self):
        """Test definition has required properties."""
        defn = get_production_planning_definition()

        assert defn.validator_id == "production/planning"
        assert defn.name == "Production Planning"
        assert defn.category == ValidatorCategory.PRODUCTION
        assert len(defn.depends_on_parameters) > 0
        assert len(defn.produces_parameters) > 0

    def test_depends_on_parameters(self):
        """Test definition depends on required parameters."""
        defn = get_production_planning_definition()

        # Should depend on hull dimensions
        assert "hull.lwl" in defn.depends_on_parameters
        assert "hull.beam" in defn.depends_on_parameters
        assert "hull.depth" in defn.depends_on_parameters

    def test_produces_parameters(self):
        """Test definition produces expected parameters."""
        defn = get_production_planning_definition()

        assert "production.material_takeoff" in defn.produces_parameters
        assert "production.assembly_sequence" in defn.produces_parameters
        assert "production.build_schedule" in defn.produces_parameters
        assert "production.summary" in defn.produces_parameters


class TestRegisterValidators:
    """Tests for validator registration."""

    def test_register_validators(self):
        """Test validators can be registered."""
        registry = {}
        register_production_validators(registry)

        assert "production/planning" in registry
        assert isinstance(registry["production/planning"], ProductionPlanningValidator)


class TestDeterminizeDict:
    """Tests for determinize_dict helper."""

    def test_sorts_keys(self):
        """Test dictionary keys are sorted."""
        data = {"z": 1, "a": 2, "m": 3}
        result = determinize_dict(data)

        assert list(result.keys()) == ["a", "m", "z"]

    def test_rounds_floats(self):
        """Test floats are rounded."""
        data = {"value": 3.14159265359}
        result = determinize_dict(data, precision=4)

        assert result["value"] == 3.1416

    def test_handles_nested(self):
        """Test handles nested structures."""
        data = {
            "outer": {
                "inner": 1.234567,
            },
        }
        result = determinize_dict(data, precision=3)

        assert result["outer"]["inner"] == 1.235

    def test_handles_lists(self):
        """Test handles lists."""
        data = {
            "items": [
                {"value": 1.111111},
                {"value": 2.222222},
            ],
        }
        result = determinize_dict(data, precision=2)

        assert result["items"][0]["value"] == 1.11
        assert result["items"][1]["value"] == 2.22

    def test_preserves_other_types(self):
        """Test preserves non-float types."""
        data = {
            "string": "test",
            "int": 42,
            "bool": True,
            "none": None,
        }
        result = determinize_dict(data)

        assert result["string"] == "test"
        assert result["int"] == 42
        assert result["bool"] is True
        assert result["none"] is None
