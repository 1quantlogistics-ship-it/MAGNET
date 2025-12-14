"""
Unit tests for MAGNET Compliance Module (Module 10).

Tests compliance framework, rule library, checkers, and validators.

v1.1 - Verified field names match Module 01 v1.8 StabilityState.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from magnet.compliance import (
    # Enums
    RegulatoryFramework,
    RuleCategory,
    FindingSeverity,
    ComplianceStatus,
    # Rule Schema
    RuleReference,
    RuleRequirement,
    Finding,
    # Rule Library
    RuleLibrary,
    RULE_LIBRARY,
    # Checkers
    StabilityRuleChecker,
    StructuralRuleChecker,
    FreeboardRuleChecker,
    get_checker,
    RULE_CHECKERS,
    # Engine
    ComplianceEngine,
    ComplianceReport,
    # Validators
    determinize_dict,
    get_compliance_validator_definition,
    get_stability_compliance_definition,
)


# =============================================================================
# MOCK STATE MANAGER
# =============================================================================

class MockStateManager:
    """Mock StateManager for testing."""

    def __init__(self, data: dict = None):
        self._data = data or {}

    def read(self, namespace: str, key: str, default=None):
        """Read value from mock state."""
        full_key = f"{namespace}.{key}"
        return self._data.get(full_key, default)

    def write(self, namespace: str, key: str, value):
        """Write value to mock state."""
        full_key = f"{namespace}.{key}"
        self._data[full_key] = value

    def get(self, path: str, default=None):
        """Get value by dot-notation path."""
        return self._data.get(path, default)

    def set(self, path: str, value, source=None):
        """Set value by dot-notation path."""
        self._data[path] = value


# =============================================================================
# ENUM TESTS
# =============================================================================

class TestEnums:
    """Test compliance enumerations."""

    def test_regulatory_framework_values(self):
        """Test all regulatory framework enum values exist."""
        assert RegulatoryFramework.ABS_HSNC.value == "abs_high_speed_naval_craft"
        assert RegulatoryFramework.ABS_HSC.value == "abs_high_speed_craft"
        assert RegulatoryFramework.DNV_HSLC.value == "dnv_high_speed_light_craft"
        assert RegulatoryFramework.USCG_SUBCHAPTER_T.value == "uscg_subchapter_t"
        assert RegulatoryFramework.HSC_CODE_2000.value == "hsc_code_2000"
        assert RegulatoryFramework.SOLAS.value == "solas"

    def test_rule_category_values(self):
        """Test rule category enum values."""
        assert RuleCategory.STABILITY.value == "stability"
        assert RuleCategory.STRUCTURAL.value == "structural"
        assert RuleCategory.FREEBOARD.value == "freeboard"
        assert RuleCategory.FIRE_SAFETY.value == "fire_safety"

    def test_finding_severity_values(self):
        """Test finding severity enum values."""
        assert FindingSeverity.PASS.value == "pass"
        assert FindingSeverity.ADVISORY.value == "advisory"
        assert FindingSeverity.WARNING.value == "warning"
        assert FindingSeverity.NON_CONFORMANCE.value == "non_conformance"
        assert FindingSeverity.CRITICAL.value == "critical"

    def test_compliance_status_values(self):
        """Test compliance status enum values."""
        assert ComplianceStatus.COMPLIANT.value == "compliant"
        assert ComplianceStatus.CONDITIONALLY_COMPLIANT.value == "conditionally_compliant"
        assert ComplianceStatus.REVIEW_REQUIRED.value == "review_required"
        assert ComplianceStatus.NON_COMPLIANT.value == "non_compliant"


# =============================================================================
# RULE SCHEMA TESTS
# =============================================================================

class TestRuleReference:
    """Test RuleReference dataclass."""

    def test_rule_reference_creation(self):
        """Test creating a rule reference."""
        ref = RuleReference(
            framework="ABS HSNC",
            section="3/2.1",
            paragraph="3.1.1",
            edition_year=2024,
        )
        assert ref.framework == "ABS HSNC"
        assert ref.section == "3/2.1"
        assert ref.paragraph == "3.1.1"
        assert ref.edition_year == 2024

    def test_to_citation(self):
        """Test citation generation."""
        ref = RuleReference("ABS HSNC", "3/2.1", "3.1.1")
        citation = ref.to_citation()
        assert "ABS HSNC" in citation
        assert "3/2.1" in citation
        assert "3.1.1" in citation

    def test_to_dict(self):
        """Test serialization to dict."""
        ref = RuleReference("ABS HSNC", "3/2.1", "3.1.1", edition_year=2024)
        d = ref.to_dict()
        assert d["framework"] == "ABS HSNC"
        assert d["section"] == "3/2.1"
        assert d["paragraph"] == "3.1.1"
        assert d["edition_year"] == 2024
        assert "citation" in d


class TestRuleRequirement:
    """Test RuleRequirement dataclass."""

    def test_rule_requirement_creation(self):
        """Test creating a rule requirement."""
        rule = RuleRequirement(
            rule_id="TEST-001",
            name="Test Rule",
            description="A test rule",
            category=RuleCategory.STABILITY,
            framework=RegulatoryFramework.ABS_HSNC,
            required_inputs=["stability.gm_m"],
            limit_value=0.15,
            limit_type="minimum",
            mandatory=True,
        )
        assert rule.rule_id == "TEST-001"
        assert rule.name == "Test Rule"
        assert rule.category == RuleCategory.STABILITY
        assert rule.limit_value == 0.15
        assert rule.mandatory is True

    def test_to_dict(self):
        """Test serialization to dict."""
        rule = RuleRequirement(
            rule_id="TEST-001",
            name="Test Rule",
            description="A test rule",
            category=RuleCategory.STABILITY,
            framework=RegulatoryFramework.ABS_HSNC,
        )
        d = rule.to_dict()
        assert d["rule_id"] == "TEST-001"
        assert d["category"] == "stability"
        assert d["framework"] == "abs_high_speed_naval_craft"


class TestFinding:
    """Test Finding dataclass."""

    def test_finding_creation(self):
        """Test creating a finding."""
        finding = Finding(
            finding_id="F-001",
            rule_id="TEST-001",
            rule_name="Test Rule",
            severity=FindingSeverity.PASS,
            status="pass",
            message="Test passed",
            actual_value=0.20,
            required_value=0.15,
            margin=0.05,
            margin_percent=33.3,
        )
        assert finding.finding_id == "F-001"
        assert finding.severity == FindingSeverity.PASS
        assert finding.status == "pass"
        assert finding.margin == 0.05

    def test_to_dict(self):
        """Test serialization to dict."""
        finding = Finding(
            finding_id="F-001",
            rule_id="TEST-001",
            rule_name="Test Rule",
            severity=FindingSeverity.PASS,
            status="pass",
            message="Test passed",
        )
        d = finding.to_dict()
        assert d["finding_id"] == "F-001"
        assert d["severity"] == "pass"
        assert d["status"] == "pass"


# =============================================================================
# RULE LIBRARY TESTS
# =============================================================================

class TestRuleLibrary:
    """Test RuleLibrary class."""

    def test_singleton_exists(self):
        """Test RULE_LIBRARY singleton exists."""
        assert RULE_LIBRARY is not None
        assert isinstance(RULE_LIBRARY, RuleLibrary)

    def test_abs_hsnc_rules_loaded(self):
        """Test ABS HSNC rules are loaded."""
        rules = RULE_LIBRARY.get_by_framework(RegulatoryFramework.ABS_HSNC)
        assert len(rules) > 0
        rule_ids = [r.rule_id for r in rules]
        assert "ABS-HSNC-3-2-1" in rule_ids  # GM minimum
        assert "ABS-HSNC-3-2-2" in rule_ids  # Area 0-30

    def test_hsc_code_rules_loaded(self):
        """Test HSC Code 2000 rules are loaded."""
        rules = RULE_LIBRARY.get_by_framework(RegulatoryFramework.HSC_CODE_2000)
        assert len(rules) > 0

    def test_uscg_rules_loaded(self):
        """Test USCG rules are loaded."""
        rules = RULE_LIBRARY.get_by_framework(RegulatoryFramework.USCG_SUBCHAPTER_T)
        assert len(rules) > 0

    def test_get_rule_by_id(self):
        """Test getting a specific rule by ID."""
        rule = RULE_LIBRARY.get("ABS-HSNC-3-2-1")
        assert rule is not None
        assert rule.name == "Intact Stability - Minimum GM"

    def test_get_by_category(self):
        """Test getting rules by category."""
        stability_rules = RULE_LIBRARY.get_by_category(RuleCategory.STABILITY)
        assert len(stability_rules) > 0
        for rule in stability_rules:
            assert rule.category == RuleCategory.STABILITY

    def test_get_applicable_rules(self):
        """Test filtering rules by vessel characteristics."""
        # All ABS HSNC rules for 35m patrol boat
        rules = RULE_LIBRARY.get_applicable_rules(
            framework=RegulatoryFramework.ABS_HSNC,
            vessel_type="patrol",
            length_m=35.0,
        )
        assert len(rules) > 0

    def test_v1_1_field_names(self):
        """Test v1.1 field names are correct."""
        # Verify stability field names match Module 01 v1.8
        gm_rule = RULE_LIBRARY.get("ABS-HSNC-3-2-1")
        assert "stability.gm_m" in gm_rule.required_inputs

        area_rule = RULE_LIBRARY.get("ABS-HSNC-3-2-2")
        assert "stability.area_0_30_m_rad" in area_rule.required_inputs

        angle_rule = RULE_LIBRARY.get("ABS-HSNC-3-2-6")
        # v1.1: angle_of_max_gz_deg (NOT angle_of_maximum_gz_deg)
        assert "stability.angle_of_max_gz_deg" in angle_rule.required_inputs


class TestRuleLibraryRegistration:
    """Test custom rule registration."""

    def test_register_custom_rule(self):
        """Test registering a custom rule."""
        library = RuleLibrary()
        initial_count = len(library.get_all_rules())

        custom_rule = RuleRequirement(
            rule_id="CUSTOM-001",
            name="Custom Test Rule",
            description="A custom test rule",
            category=RuleCategory.STABILITY,
            framework=RegulatoryFramework.ABS_HSNC,
        )
        library.register(custom_rule)

        assert len(library.get_all_rules()) == initial_count + 1
        retrieved = library.get("CUSTOM-001")
        assert retrieved is not None
        assert retrieved.name == "Custom Test Rule"


# =============================================================================
# RULE CHECKER TESTS
# =============================================================================

class TestStabilityRuleChecker:
    """Test StabilityRuleChecker class."""

    def test_checker_category(self):
        """Test checker has correct category."""
        checker = StabilityRuleChecker()
        assert checker.category == RuleCategory.STABILITY

    def test_check_with_missing_inputs(self):
        """Test check returns incomplete for missing inputs."""
        state = MockStateManager({})  # Empty state

        rule = RuleRequirement(
            rule_id="TEST-001",
            name="Test GM",
            description="Test",
            category=RuleCategory.STABILITY,
            framework=RegulatoryFramework.ABS_HSNC,
            required_inputs=["stability.gm_m"],
            limit_value=0.15,
            limit_type="minimum",
        )

        checker = StabilityRuleChecker()
        finding = checker.check(rule, state)

        assert finding.status == "incomplete"
        assert "Missing required inputs" in finding.message

    def test_check_passing_rule(self):
        """Test check for passing stability rule."""
        state = MockStateManager({
            "stability.gm_m": 0.50,  # Well above minimum
            "hull.beam": 8.0,
        })

        rule = RuleRequirement(
            rule_id="TEST-001",
            name="Test GM",
            description="Test",
            category=RuleCategory.STABILITY,
            framework=RegulatoryFramework.ABS_HSNC,
            required_inputs=["stability.gm_m"],
            limit_value=0.15,
            limit_type="minimum",
        )

        checker = StabilityRuleChecker()
        finding = checker.check(rule, state)

        assert finding.status == "pass"
        assert finding.severity == FindingSeverity.PASS
        assert finding.actual_value == 0.50
        assert finding.required_value == 0.15
        assert finding.margin > 0

    def test_check_failing_rule(self):
        """Test check for failing stability rule."""
        state = MockStateManager({
            "stability.gm_m": 0.10,  # Below minimum
            "hull.beam": 8.0,
        })

        rule = RuleRequirement(
            rule_id="TEST-001",
            name="Test GM",
            description="Test",
            category=RuleCategory.STABILITY,
            framework=RegulatoryFramework.ABS_HSNC,
            required_inputs=["stability.gm_m"],
            limit_value=0.15,
            limit_type="minimum",
            mandatory=True,
        )

        checker = StabilityRuleChecker()
        finding = checker.check(rule, state)

        assert finding.status == "fail"
        assert finding.severity == FindingSeverity.NON_CONFORMANCE
        assert finding.margin < 0


class TestStructuralRuleChecker:
    """Test StructuralRuleChecker class."""

    def test_checker_category(self):
        """Test checker has correct category."""
        checker = StructuralRuleChecker()
        assert checker.category == RuleCategory.STRUCTURAL

    def test_structural_returns_review_required(self):
        """Test structural checker returns review_required for complex rules."""
        state = MockStateManager({
            "structure.bottom_plate_thickness_mm": 6.0,
            "hull.lwl": 35.0,
        })

        rule = RuleRequirement(
            rule_id="ABS-HSNC-4-1-1",
            name="Bottom Plating",
            description="Test",
            category=RuleCategory.STRUCTURAL,
            framework=RegulatoryFramework.ABS_HSNC,
            required_inputs=["structure.bottom_plate_thickness_mm", "hull.lwl"],
        )

        checker = StructuralRuleChecker()
        finding = checker.check(rule, state)

        assert finding.status == "review_required"


class TestFreeboardRuleChecker:
    """Test FreeboardRuleChecker class."""

    def test_checker_category(self):
        """Test checker has correct category."""
        checker = FreeboardRuleChecker()
        assert checker.category == RuleCategory.FREEBOARD


class TestCheckerRegistry:
    """Test checker registry."""

    def test_get_stability_checker(self):
        """Test getting stability checker."""
        checker = get_checker(RuleCategory.STABILITY)
        assert checker is not None
        assert isinstance(checker, StabilityRuleChecker)

    def test_get_structural_checker(self):
        """Test getting structural checker."""
        checker = get_checker(RuleCategory.STRUCTURAL)
        assert checker is not None
        assert isinstance(checker, StructuralRuleChecker)

    def test_get_freeboard_checker(self):
        """Test getting freeboard checker."""
        checker = get_checker(RuleCategory.FREEBOARD)
        assert checker is not None
        assert isinstance(checker, FreeboardRuleChecker)

    def test_rule_checkers_dict(self):
        """Test RULE_CHECKERS dictionary."""
        assert RuleCategory.STABILITY in RULE_CHECKERS
        assert RuleCategory.STRUCTURAL in RULE_CHECKERS
        assert RuleCategory.FREEBOARD in RULE_CHECKERS


# =============================================================================
# COMPLIANCE ENGINE TESTS
# =============================================================================

class TestComplianceEngine:
    """Test ComplianceEngine class."""

    def test_engine_creation(self):
        """Test creating compliance engine."""
        engine = ComplianceEngine()
        assert engine.rule_library is not None

    def test_engine_with_custom_library(self):
        """Test engine with custom rule library."""
        custom_library = RuleLibrary()
        engine = ComplianceEngine(custom_library)
        assert engine.rule_library is custom_library

    def test_evaluate_with_passing_stability(self):
        """Test evaluation with passing stability parameters."""
        state = MockStateManager({
            "hull.lwl": 35.0,
            "hull.beam": 8.0,
            "hull.freeboard": 1.5,
            "mission.vessel_type": "patrol",
            "mission.vessel_name": "Test Vessel",
            "stability.gm_m": 1.0,
            "stability.gz_max_m": 0.50,
            "stability.angle_of_max_gz_deg": 30.0,
            "stability.area_0_30_m_rad": 0.08,
            "stability.area_0_40_m_rad": 0.12,
            "stability.area_30_40_m_rad": 0.05,
            "stability.range_deg": 60.0,
        })

        engine = ComplianceEngine()
        report = engine.evaluate(
            state=state,
            frameworks=[RegulatoryFramework.ABS_HSNC],
            vessel_type="patrol",
            length_m=35.0,
        )

        assert report is not None
        assert isinstance(report, ComplianceReport)
        assert report.total_rules > 0
        assert report.pass_count > 0

    def test_evaluate_single_framework(self):
        """Test single framework evaluation."""
        state = MockStateManager({
            "hull.lwl": 35.0,
            "mission.vessel_type": "patrol",
            "stability.gm_m": 1.0,
        })

        engine = ComplianceEngine()
        report = engine.evaluate_single_framework(
            state=state,
            framework=RegulatoryFramework.HSC_CODE_2000,
            vessel_type="patrol",
            length_m=35.0,
        )

        assert report.frameworks_checked == [RegulatoryFramework.HSC_CODE_2000]

    def test_evaluate_category(self):
        """Test category-specific evaluation."""
        state = MockStateManager({
            "stability.gm_m": 0.50,
            "hull.beam": 8.0,
        })

        engine = ComplianceEngine()
        findings = engine.evaluate_category(
            state=state,
            category=RuleCategory.STABILITY,
            frameworks=[RegulatoryFramework.ABS_HSNC],
        )

        assert isinstance(findings, list)
        # Should have findings for stability rules
        assert len(findings) > 0


class TestComplianceReport:
    """Test ComplianceReport class."""

    def test_report_creation(self):
        """Test creating compliance report."""
        report = ComplianceReport(
            report_id="CR-TEST001",
            vessel_name="Test Vessel",
            vessel_type="patrol",
            frameworks_checked=[RegulatoryFramework.ABS_HSNC],
        )
        assert report.report_id == "CR-TEST001"
        assert report.vessel_name == "Test Vessel"

    def test_report_to_dict(self):
        """Test report serialization."""
        report = ComplianceReport(
            report_id="CR-TEST001",
            vessel_name="Test Vessel",
            vessel_type="patrol",
            frameworks_checked=[RegulatoryFramework.ABS_HSNC],
        )
        report.pass_count = 5
        report.fail_count = 1
        report.total_rules = 6

        d = report.to_dict()
        assert d["report_id"] == "CR-TEST001"
        assert d["summary"]["pass_count"] == 5
        assert d["summary"]["fail_count"] == 1

    def test_get_pass_rate(self):
        """Test pass rate calculation."""
        report = ComplianceReport(
            report_id="CR-TEST001",
            vessel_name="Test Vessel",
            vessel_type="patrol",
            frameworks_checked=[RegulatoryFramework.ABS_HSNC],
        )
        report.pass_count = 8
        report.fail_count = 2

        pass_rate = report.get_pass_rate()
        assert pass_rate == 80.0

    def test_get_pass_rate_zero_evaluated(self):
        """Test pass rate with no evaluations."""
        report = ComplianceReport(
            report_id="CR-TEST001",
            vessel_name="Test Vessel",
            vessel_type="patrol",
            frameworks_checked=[],
        )
        assert report.get_pass_rate() == 0.0


# =============================================================================
# VALIDATOR DEFINITION TESTS
# =============================================================================

class TestValidatorDefinitions:
    """Test validator definition factory functions."""

    def test_compliance_validator_definition(self):
        """Test compliance validator definition."""
        definition = get_compliance_validator_definition()
        assert definition.validator_id == "compliance/regulatory"
        assert "stability/intact_gm" in definition.depends_on_validators
        assert "stability/gz_curve" in definition.depends_on_validators
        assert "compliance.status" in definition.produces_parameters
        assert "compliance.report" in definition.produces_parameters

    def test_stability_compliance_definition(self):
        """Test stability compliance validator definition."""
        definition = get_stability_compliance_definition()
        assert definition.validator_id == "compliance/stability"
        assert "stability/gz_curve" in definition.depends_on_validators
        assert "compliance.stability_status" in definition.produces_parameters


# =============================================================================
# UTILITY TESTS
# =============================================================================

class TestDeterminizeDict:
    """Test determinize_dict utility function."""

    def test_sorts_keys(self):
        """Test dictionary keys are sorted."""
        data = {"z": 1, "a": 2, "m": 3}
        result = determinize_dict(data)
        keys = list(result.keys())
        assert keys == ["a", "m", "z"]

    def test_rounds_floats(self):
        """Test floats are rounded."""
        data = {"value": 1.234567890123}
        result = determinize_dict(data, precision=4)
        assert result["value"] == 1.2346

    def test_handles_nested_dicts(self):
        """Test nested dictionaries are processed."""
        data = {"outer": {"z": 1, "a": 2}}
        result = determinize_dict(data)
        inner_keys = list(result["outer"].keys())
        assert inner_keys == ["a", "z"]

    def test_handles_lists(self):
        """Test lists are processed."""
        data = {"items": [{"b": 1}, {"a": 2}]}
        result = determinize_dict(data)
        assert result["items"][0] == {"b": 1}
        assert result["items"][1] == {"a": 2}

    def test_preserves_non_float_types(self):
        """Test non-float types are preserved."""
        data = {"string": "hello", "int": 42, "bool": True, "none": None}
        result = determinize_dict(data)
        assert result["string"] == "hello"
        assert result["int"] == 42
        assert result["bool"] is True
        assert result["none"] is None

    def test_deterministic_output(self):
        """Test output is deterministic."""
        data = {"z": 1.5, "a": {"c": 2.5, "b": 3.5}}
        result1 = determinize_dict(data)
        result2 = determinize_dict(data)
        assert result1 == result2
