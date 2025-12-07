"""
Unit tests for validators/taxonomy.py

Tests validator categories, types, definitions, and results.
"""

import pytest
from datetime import datetime

from magnet.validators.taxonomy import (
    ValidatorCategory,
    ValidatorPriority,
    ValidatorState,
    ResultSeverity,
    ResourceRequirements,
    ResourcePool,
    ValidatorDefinition,
    ValidationFinding,
    ValidationResult,
    create_passed_result,
    create_failed_result,
    create_error_result,
)


class TestValidatorEnums:
    """Test validator enums."""

    def test_validator_category_values(self):
        """Test ValidatorCategory enum values."""
        assert ValidatorCategory.PHYSICS.value == "physics"
        assert ValidatorCategory.BOUNDS.value == "bounds"
        assert ValidatorCategory.CLASS_RULES.value == "class_rules"
        assert ValidatorCategory.STABILITY.value == "stability"

    def test_validator_priority_ordering(self):
        """Test ValidatorPriority ordering."""
        assert ValidatorPriority.CRITICAL.value < ValidatorPriority.HIGH.value
        assert ValidatorPriority.HIGH.value < ValidatorPriority.NORMAL.value
        assert ValidatorPriority.NORMAL.value < ValidatorPriority.LOW.value

    def test_validator_state_values(self):
        """Test ValidatorState enum values."""
        assert ValidatorState.PENDING.value == "pending"
        assert ValidatorState.PASSED.value == "passed"
        assert ValidatorState.FAILED.value == "failed"
        assert ValidatorState.ERROR.value == "error"

    def test_error_vs_failed_distinction(self):
        """Test FIX #5: ERROR (code failure) vs FAILED (validation failure)."""
        # These are distinct states with different meanings
        assert ValidatorState.ERROR != ValidatorState.FAILED
        assert ValidatorState.ERROR.value == "error"  # Code failure
        assert ValidatorState.FAILED.value == "failed"  # Validation failure


class TestResourceRequirements:
    """Test ResourceRequirements dataclass."""

    def test_create_default(self):
        """Test default resource requirements."""
        req = ResourceRequirements()
        assert req.cpu_cores == 1
        assert req.ram_gb == 0.5
        assert req.gpu_required == False

    def test_create_custom(self):
        """Test custom resource requirements."""
        req = ResourceRequirements(cpu_cores=4, ram_gb=8.0, gpu_required=True)
        assert req.cpu_cores == 4
        assert req.ram_gb == 8.0
        assert req.gpu_required == True

    def test_fits_in_pool(self):
        """Test checking if requirements fit in pool."""
        req = ResourceRequirements(cpu_cores=2, ram_gb=4.0)
        pool = ResourcePool(cpu_cores=4, ram_gb=8.0)
        assert req.fits_in(pool) == True

    def test_does_not_fit_in_pool(self):
        """Test requirements exceeding pool."""
        req = ResourceRequirements(cpu_cores=8, ram_gb=16.0)
        pool = ResourcePool(cpu_cores=4, ram_gb=8.0)
        assert req.fits_in(pool) == False

    def test_to_dict(self):
        """Test serialization."""
        req = ResourceRequirements(cpu_cores=2, ram_gb=4.0)
        data = req.to_dict()
        assert data["cpu_cores"] == 2
        assert data["ram_gb"] == 4.0

    def test_from_dict(self):
        """Test deserialization."""
        data = {"cpu_cores": 4, "ram_gb": 8.0, "gpu_required": True}
        req = ResourceRequirements.from_dict(data)
        assert req.cpu_cores == 4
        assert req.ram_gb == 8.0
        assert req.gpu_required == True


class TestResourcePool:
    """Test ResourcePool dataclass."""

    def test_allocate_success(self):
        """Test successful allocation."""
        pool = ResourcePool(cpu_cores=4, ram_gb=8.0)
        req = ResourceRequirements(cpu_cores=2, ram_gb=4.0)

        assert pool.allocate(req) == True
        assert pool.cpu_cores == 2
        assert pool.ram_gb == 4.0

    def test_allocate_failure(self):
        """Test failed allocation (insufficient resources)."""
        pool = ResourcePool(cpu_cores=2, ram_gb=4.0)
        req = ResourceRequirements(cpu_cores=4, ram_gb=8.0)

        assert pool.allocate(req) == False
        assert pool.cpu_cores == 2  # Unchanged

    def test_release(self):
        """Test resource release."""
        pool = ResourcePool(cpu_cores=4, ram_gb=8.0)
        req = ResourceRequirements(cpu_cores=2, ram_gb=4.0)

        pool.allocate(req)
        pool.release(req)

        assert pool.cpu_cores == 4
        assert pool.ram_gb == 8.0


class TestValidatorDefinition:
    """Test ValidatorDefinition dataclass."""

    def test_create_minimal(self):
        """Test creating minimal definition."""
        defn = ValidatorDefinition(
            validator_id="test/validator",
            name="Test Validator",
            description="A test validator",
            category=ValidatorCategory.PHYSICS,
        )
        assert defn.validator_id == "test/validator"
        assert defn.priority == ValidatorPriority.NORMAL

    def test_create_full(self):
        """Test creating full definition."""
        defn = ValidatorDefinition(
            validator_id="physics/hydrostatics",
            name="Hydrostatics",
            description="Computes hydrostatics",
            category=ValidatorCategory.PHYSICS,
            priority=ValidatorPriority.CRITICAL,
            phase="hull_form",
            is_gate_condition=True,
            depends_on_validators=["bounds/hull"],
            depends_on_parameters=["hull.loa", "hull.beam"],
            produces_parameters=["hull.displacement_m3"],
            timeout_seconds=120,
            max_retries=3,
        )
        assert defn.is_gate_condition == True
        assert len(defn.depends_on_parameters) == 2
        assert "hull.displacement_m3" in defn.produces_parameters

    def test_to_dict_roundtrip(self):
        """Test serialization roundtrip."""
        original = ValidatorDefinition(
            validator_id="test/roundtrip",
            name="Roundtrip Test",
            description="Tests roundtrip",
            category=ValidatorCategory.BOUNDS,
            priority=ValidatorPriority.HIGH,
            phase="mission",
            depends_on_parameters=["mission.max_speed_kts"],
        )

        data = original.to_dict()
        restored = ValidatorDefinition.from_dict(data)

        assert restored.validator_id == original.validator_id
        assert restored.category == original.category
        assert restored.priority == original.priority
        assert restored.depends_on_parameters == original.depends_on_parameters

    def test_hash(self):
        """Test validator definition is hashable."""
        defn = ValidatorDefinition(
            validator_id="test/hash",
            name="Hash Test",
            description="Tests hash",
            category=ValidatorCategory.PHYSICS,
        )
        # Should be usable in sets/dicts
        validators = {defn}
        assert defn in validators


class TestValidationFinding:
    """Test ValidationFinding dataclass."""

    def test_create_error(self):
        """Test creating error finding."""
        finding = ValidationFinding(
            finding_id="F001",
            severity=ResultSeverity.ERROR,
            message="Value out of range",
            parameter_path="hull.loa",
            expected_value="20-50",
            actual_value="60",
        )
        assert finding.severity == ResultSeverity.ERROR
        assert finding.parameter_path == "hull.loa"

    def test_create_warning(self):
        """Test creating warning finding."""
        finding = ValidationFinding(
            finding_id="W001",
            severity=ResultSeverity.WARNING,
            message="Value near limit",
            suggestion="Consider reducing speed",
        )
        assert finding.severity == ResultSeverity.WARNING

    def test_to_dict(self):
        """Test serialization."""
        finding = ValidationFinding(
            finding_id="F002",
            severity=ResultSeverity.ERROR,
            message="Test error",
            reference="ABS Rule 3-2-1",
        )
        data = finding.to_dict()
        assert data["finding_id"] == "F002"
        assert data["reference"] == "ABS Rule 3-2-1"


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_create_empty(self):
        """Test creating empty result."""
        result = ValidationResult(
            validator_id="test/empty",
            state=ValidatorState.PENDING,
            started_at=datetime.utcnow(),
        )
        assert result.error_count == 0
        assert result.warning_count == 0

    def test_add_finding(self):
        """Test adding findings."""
        result = ValidationResult(
            validator_id="test/findings",
            state=ValidatorState.RUNNING,
            started_at=datetime.utcnow(),
        )

        result.add_finding(ValidationFinding(
            finding_id="E1",
            severity=ResultSeverity.ERROR,
            message="Error 1",
        ))
        result.add_finding(ValidationFinding(
            finding_id="W1",
            severity=ResultSeverity.WARNING,
            message="Warning 1",
        ))

        assert result.error_count == 1
        assert result.warning_count == 1

    def test_passed_property(self):
        """Test passed property."""
        passed_result = ValidationResult(
            validator_id="test/passed",
            state=ValidatorState.PASSED,
            started_at=datetime.utcnow(),
        )
        assert passed_result.passed == True

        warning_result = ValidationResult(
            validator_id="test/warning",
            state=ValidatorState.WARNING,
            started_at=datetime.utcnow(),
        )
        assert warning_result.passed == True

        failed_result = ValidationResult(
            validator_id="test/failed",
            state=ValidatorState.FAILED,
            started_at=datetime.utcnow(),
        )
        assert failed_result.passed == False

    def test_is_execution_error(self):
        """Test FIX #5: is_execution_error property."""
        error_result = ValidationResult(
            validator_id="test/error",
            state=ValidatorState.ERROR,
            started_at=datetime.utcnow(),
            error_message="Code exception",
        )
        assert error_result.is_execution_error == True

        failed_result = ValidationResult(
            validator_id="test/failed",
            state=ValidatorState.FAILED,
            started_at=datetime.utcnow(),
        )
        assert failed_result.is_execution_error == False

    def test_to_dict_roundtrip(self):
        """Test serialization roundtrip."""
        original = ValidationResult(
            validator_id="test/roundtrip",
            state=ValidatorState.PASSED,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            execution_time_ms=150,
        )
        original.add_finding(ValidationFinding(
            finding_id="P1",
            severity=ResultSeverity.PASSED,
            message="All checks passed",
        ))

        data = original.to_dict()
        restored = ValidationResult.from_dict(data)

        assert restored.validator_id == original.validator_id
        assert restored.state == original.state
        assert len(restored.findings) == 1


class TestHelperFunctions:
    """Test helper functions."""

    def test_create_passed_result(self):
        """Test create_passed_result helper."""
        result = create_passed_result("test/pass", "All good")
        assert result.state == ValidatorState.PASSED
        assert result.passed == True
        assert len(result.findings) == 1

    def test_create_failed_result(self):
        """Test create_failed_result helper."""
        result = create_failed_result(
            "test/fail",
            "Value out of range",
            parameter_path="hull.loa",
        )
        assert result.state == ValidatorState.FAILED
        assert result.error_count == 1
        assert result.findings[0].parameter_path == "hull.loa"

    def test_create_error_result(self):
        """Test create_error_result helper."""
        result = create_error_result(
            "test/error",
            "Division by zero",
            traceback="Traceback...",
        )
        assert result.state == ValidatorState.ERROR
        assert result.is_execution_error == True
        assert result.error_message == "Division by zero"
