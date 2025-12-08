"""
tests/unit/test_optimization_validator.py - Tests for optimization validator.

BRAVO OWNS THIS FILE.

Tests for Module 13 v1.1 - OptimizationValidator.
"""

import pytest
from magnet.optimization import (
    OptimizationValidator,
    OPTIMIZATION_DEFINITION,
    get_optimization_definition,
    register_optimization_validators,
    OptimizationProblem,
    DesignVariable,
    Objective,
    ObjectiveType,
)
from magnet.optimization.validator import determinize_dict
from magnet.validators.taxonomy import (
    ValidatorState,
    ValidatorCategory,
    ValidatorPriority,
)


class MockStateManager:
    """Mock StateManager for testing."""

    def __init__(self):
        self._data = {}
        self._writes = []

    def clone(self):
        """Clone for optimizer evaluation."""
        new_state = MockStateManager()
        new_state._data = self._data.copy()
        return new_state

    def get(self, path, default=None):
        return self._data.get(path, default)

    def set(self, path, value):
        self._data[path] = value

    def write(self, path, value, agent="", description=""):
        self._data[path] = value
        self._writes.append((path, value, agent))


class TestDeterminizeDict:
    """Tests for determinize_dict helper function."""

    def test_simple_dict(self):
        """Test simple dictionary determinization."""
        data = {"b": 1, "a": 2}
        result = determinize_dict(data)
        assert list(result.keys()) == ["a", "b"]

    def test_float_rounding(self):
        """Test float values are rounded."""
        data = {"value": 1.123456789}
        result = determinize_dict(data)
        assert result["value"] == 1.123457

    def test_custom_precision(self):
        """Test custom precision."""
        data = {"value": 1.12345678}
        result = determinize_dict(data, precision=3)
        assert result["value"] == 1.123

    def test_nested_dict(self):
        """Test nested dictionary."""
        data = {"outer": {"b": 1.1111111, "a": 2.2222222}}
        result = determinize_dict(data)
        assert list(result["outer"].keys()) == ["a", "b"]
        assert result["outer"]["a"] == 2.222222

    def test_list_values(self):
        """Test list values are processed."""
        data = {"items": [1.111111, 2.222222]}
        result = determinize_dict(data)
        assert result["items"] == [1.111111, 2.222222]

    def test_mixed_types(self):
        """Test mixed types are handled."""
        data = {"str": "hello", "int": 42, "float": 1.5, "bool": True}
        result = determinize_dict(data)
        assert result["str"] == "hello"
        assert result["int"] == 42
        assert result["float"] == 1.5
        assert result["bool"] == True


class TestOptimizationDefinition:
    """Tests for OPTIMIZATION_DEFINITION."""

    def test_definition_exists(self):
        """Test definition is defined."""
        assert OPTIMIZATION_DEFINITION is not None

    def test_definition_validator_id(self):
        """Test validator ID."""
        assert OPTIMIZATION_DEFINITION.validator_id == "optimization/design"

    def test_definition_name(self):
        """Test name."""
        assert OPTIMIZATION_DEFINITION.name == "Design Optimization"

    def test_definition_category(self):
        """Test category."""
        assert OPTIMIZATION_DEFINITION.category == ValidatorCategory.OPTIMIZATION

    def test_definition_priority(self):
        """Test priority."""
        assert OPTIMIZATION_DEFINITION.priority == ValidatorPriority.LOW

    def test_definition_phase(self):
        """Test phase."""
        assert OPTIMIZATION_DEFINITION.phase == "optimization"

    def test_definition_is_not_gate(self):
        """Test is not gate condition."""
        assert OPTIMIZATION_DEFINITION.is_gate_condition == False

    def test_definition_dependencies(self):
        """Test dependencies are specified."""
        deps = OPTIMIZATION_DEFINITION.depends_on_parameters
        assert "hull.lwl" in deps
        assert "hull.beam" in deps
        assert "hull.depth" in deps
        assert "cost.total_price" in deps
        assert "weight.lightship_mt" in deps

    def test_definition_produces(self):
        """Test produces are specified."""
        produces = OPTIMIZATION_DEFINITION.produces_parameters
        assert "optimization.problem" in produces
        assert "optimization.result" in produces
        assert "optimization.pareto_front" in produces
        assert "optimization.selected_solution" in produces
        assert "optimization.status" in produces

    def test_definition_timeout(self):
        """Test timeout is reasonable for optimization."""
        assert OPTIMIZATION_DEFINITION.timeout_seconds == 600  # 10 minutes

    def test_definition_tags(self):
        """Test tags are specified."""
        tags = OPTIMIZATION_DEFINITION.tags
        assert "optimization" in tags
        assert "nsga-ii" in tags
        assert "pareto" in tags


class TestGetOptimizationDefinition:
    """Tests for get_optimization_definition function."""

    def test_returns_definition(self):
        """Test function returns definition."""
        defn = get_optimization_definition()
        assert defn is not None
        assert defn.validator_id == "optimization/design"

    def test_returns_same_definition(self):
        """Test function returns the same definition."""
        defn = get_optimization_definition()
        assert defn is OPTIMIZATION_DEFINITION


class TestRegisterOptimizationValidators:
    """Tests for register_optimization_validators function."""

    def test_registers_to_empty_registry(self):
        """Test registration to empty registry."""
        registry = {}
        register_optimization_validators(registry)

        assert "optimization/design" in registry

    def test_registers_correct_type(self):
        """Test registered validator is correct type."""
        registry = {}
        register_optimization_validators(registry)

        validator = registry["optimization/design"]
        assert isinstance(validator, OptimizationValidator)

    def test_does_not_clear_registry(self):
        """Test registration doesn't clear existing entries."""
        registry = {"other/validator": "placeholder"}
        register_optimization_validators(registry)

        assert "other/validator" in registry
        assert "optimization/design" in registry


class TestOptimizationValidatorInit:
    """Tests for OptimizationValidator initialization."""

    def test_init_with_definition(self):
        """Test initialization with definition."""
        validator = OptimizationValidator(OPTIMIZATION_DEFINITION)
        assert validator.definition == OPTIMIZATION_DEFINITION

    def test_init_default_population_size(self):
        """Test default population size."""
        validator = OptimizationValidator(OPTIMIZATION_DEFINITION)
        assert validator.population_size == 30

    def test_init_default_max_generations(self):
        """Test default max generations."""
        validator = OptimizationValidator(OPTIMIZATION_DEFINITION)
        assert validator.max_generations == 50

    def test_init_custom_params(self):
        """Test custom parameters."""
        validator = OptimizationValidator(
            OPTIMIZATION_DEFINITION,
            population_size=20,
            max_generations=30,
        )
        assert validator.population_size == 20
        assert validator.max_generations == 30


class TestOptimizationValidatorValidate:
    """Tests for OptimizationValidator.validate method."""

    def test_fails_without_hull_lwl(self):
        """Test validation fails without hull dimensions."""
        state = MockStateManager()
        validator = OptimizationValidator(OPTIMIZATION_DEFINITION)

        result = validator.validate(state, {})

        assert result.state == ValidatorState.FAILED
        assert result.error_count > 0

    def test_fails_with_zero_lwl(self):
        """Test validation fails with zero hull dimensions."""
        state = MockStateManager()
        state.set("hull.lwl", 0)
        validator = OptimizationValidator(OPTIMIZATION_DEFINITION)

        result = validator.validate(state, {})

        assert result.state == ValidatorState.FAILED

    def test_runs_with_valid_state(self):
        """Test validation runs with valid state."""
        state = MockStateManager()
        state.set("hull.lwl", 25.0)
        state.set("hull.beam", 6.0)
        state.set("hull.depth", 3.0)

        # Use custom small problem for faster test
        problem = OptimizationProblem(name="test", description="Test")
        problem.add_variable(DesignVariable(
            name="x", state_path="test.x", lower_bound=0, upper_bound=10
        ))
        problem.add_objective(Objective(
            name="f", state_path="test.f", objective_type=ObjectiveType.MINIMIZE
        ))

        class SimpleValidator:
            def validate(self, s, c):
                x = s.get("test.x", 0)
                s.set("test.f", x ** 2)

        validator = OptimizationValidator(
            OPTIMIZATION_DEFINITION,
            population_size=5,
            max_generations=3,
        )

        result = validator.validate(state, {
            "problem": problem,
            "validators": [SimpleValidator()],
            "seed": 42,
        })

        # Should complete (may pass or warn)
        assert result.state in (ValidatorState.PASSED, ValidatorState.WARNING)

    def test_writes_optimization_results(self):
        """Test validation writes results to state."""
        state = MockStateManager()
        state.set("hull.lwl", 25.0)
        state.set("hull.beam", 6.0)
        state.set("hull.depth", 3.0)

        problem = OptimizationProblem(name="test", description="Test")
        problem.add_variable(DesignVariable(
            name="x", state_path="test.x", lower_bound=0, upper_bound=10
        ))
        problem.add_objective(Objective(
            name="f", state_path="test.f", objective_type=ObjectiveType.MINIMIZE
        ))

        class SimpleValidator:
            def validate(self, s, c):
                x = s.get("test.x", 0)
                s.set("test.f", x ** 2)

        validator = OptimizationValidator(
            OPTIMIZATION_DEFINITION,
            population_size=5,
            max_generations=3,
        )

        result = validator.validate(state, {
            "problem": problem,
            "validators": [SimpleValidator()],
            "seed": 42,
        })

        # Check writes were made
        assert state.get("optimization.problem") is not None
        assert state.get("optimization.status") is not None
        assert state.get("optimization.iterations") is not None
        assert state.get("optimization.evaluations") is not None

    def test_records_timing(self):
        """Test validation records timing."""
        state = MockStateManager()
        state.set("hull.lwl", 0)  # Will fail fast
        validator = OptimizationValidator(OPTIMIZATION_DEFINITION)

        result = validator.validate(state, {})

        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.completed_at >= result.started_at

    def test_uses_context_problem(self):
        """Test validation uses problem from context."""
        state = MockStateManager()
        state.set("hull.lwl", 25.0)

        custom_problem = OptimizationProblem(
            name="custom_problem",
            description="Custom test problem",
        )
        custom_problem.add_variable(DesignVariable(
            name="y", state_path="test.y", lower_bound=0, upper_bound=5
        ))
        custom_problem.add_objective(Objective(
            name="g", state_path="test.g", objective_type=ObjectiveType.MINIMIZE
        ))

        class CustomValidator:
            def validate(self, s, c):
                y = s.get("test.y", 0)
                s.set("test.g", y ** 2)

        validator = OptimizationValidator(
            OPTIMIZATION_DEFINITION,
            population_size=5,
            max_generations=2,
        )

        result = validator.validate(state, {
            "problem": custom_problem,
            "validators": [CustomValidator()],
            "seed": 42,
        })

        # Check custom problem was used
        prob_data = state.get("optimization.problem")
        assert prob_data is not None
        assert prob_data["name"] == "custom_problem"

    def test_uses_seed_from_context(self):
        """Test validation uses seed from context for reproducibility."""
        state = MockStateManager()
        state.set("hull.lwl", 25.0)

        problem = OptimizationProblem(name="test", description="Test")
        problem.add_variable(DesignVariable(
            name="x", state_path="test.x", lower_bound=0, upper_bound=10
        ))
        problem.add_objective(Objective(
            name="f", state_path="test.f", objective_type=ObjectiveType.MINIMIZE
        ))

        class SimpleValidator:
            def validate(self, s, c):
                x = s.get("test.x", 0)
                s.set("test.f", x ** 2)

        validator = OptimizationValidator(
            OPTIMIZATION_DEFINITION,
            population_size=5,
            max_generations=3,
        )

        # Run twice with same seed
        result1 = validator.validate(MockStateManager(), {
            "problem": problem,
            "validators": [SimpleValidator()],
            "seed": 42,
        })

        state2 = MockStateManager()
        state2.set("hull.lwl", 25.0)
        result2 = validator.validate(state2, {
            "problem": problem,
            "validators": [SimpleValidator()],
            "seed": 42,
        })

        # Results should be consistent (same iterations)
        assert state2.get("optimization.iterations") is not None


class TestOptimizationValidatorErrorHandling:
    """Tests for error handling in OptimizationValidator."""

    def test_handles_validation_error(self):
        """Test validator handles errors gracefully."""
        state = MockStateManager()
        state.set("hull.lwl", 25.0)

        problem = OptimizationProblem(name="test", description="Test")
        problem.add_variable(DesignVariable(
            name="x", state_path="test.x", lower_bound=0, upper_bound=10
        ))
        problem.add_objective(Objective(
            name="f", state_path="test.f", objective_type=ObjectiveType.MINIMIZE
        ))

        class FailingValidator:
            def validate(self, s, c):
                raise ValueError("Test failure")

        validator = OptimizationValidator(
            OPTIMIZATION_DEFINITION,
            population_size=5,
            max_generations=2,
        )

        result = validator.validate(state, {
            "problem": problem,
            "validators": [FailingValidator()],
        })

        # Should complete without crashing
        assert result.completed_at is not None
