"""
tests/unit/test_glue.py - Tests for Modules 41-45 (System Glue Layer)

Tests:
- Section 41: Protocol (schemas, escalation, cycle_executor)
- Section 42: Explanation Engine
- Section 43: Error Taxonomy
- Section 44: Transaction Model
- Section 45: Design Lifecycle
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch


# ============================================================================
# SECTION 41: PROTOCOL TESTS
# ============================================================================

class TestProtocolSchemas:
    """Test protocol schemas."""

    def test_proposal_status_enum(self):
        """Test ProposalStatus enum values."""
        from magnet.protocol.schemas import ProposalStatus

        assert ProposalStatus.PENDING.value == "pending"
        assert ProposalStatus.APPROVED.value == "approved"
        assert ProposalStatus.REJECTED.value == "rejected"

    def test_decision_type_enum(self):
        """Test DecisionType enum values."""
        from magnet.protocol.schemas import DecisionType

        assert DecisionType.APPROVE.value == "approve"
        assert DecisionType.REVISE.value == "revise"
        assert DecisionType.ESCALATE.value == "escalate"

    def test_parameter_change_to_dict(self):
        """Test ParameterChange serialization."""
        from magnet.protocol.schemas import ParameterChange

        change = ParameterChange(
            path="hull.beam",
            old_value=5.0,
            new_value=6.0,
            unit="m",
            reasoning="Increased for stability",
        )

        d = change.to_dict()
        assert d["path"] == "hull.beam"
        assert d["old_value"] == 5.0
        assert d["new_value"] == 6.0

    def test_proposal_creation(self):
        """Test Proposal creation with defaults."""
        from magnet.protocol.schemas import Proposal, ProposalStatus

        proposal = Proposal(agent_id="test_agent", phase="concept")

        assert proposal.agent_id == "test_agent"
        assert proposal.phase == "concept"
        assert proposal.status == ProposalStatus.PENDING
        assert len(proposal.proposal_id) == 8

    def test_validation_finding(self):
        """Test ValidationFinding with v1.1 defaults."""
        from magnet.protocol.schemas import ValidationFinding

        # v1.1: validator_name has default
        finding = ValidationFinding(
            severity="error",
            code="ERR001",
            message="Test error",
        )

        assert finding.validator_name == "unknown"
        assert finding.severity == "error"

    def test_validation_result_counts(self):
        """Test ValidationResult error/warning counts."""
        from magnet.protocol.schemas import ValidationResult, ValidationFinding

        findings = [
            ValidationFinding(severity="error", message="Error 1"),
            ValidationFinding(severity="error", message="Error 2"),
            ValidationFinding(severity="warning", message="Warning 1"),
        ]

        result = ValidationResult(
            proposal_id="test",
            passed=False,
            findings=findings,
        )

        assert result.error_count == 2
        assert result.warning_count == 1

    def test_agent_decision(self):
        """Test AgentDecision creation."""
        from magnet.protocol.schemas import AgentDecision, DecisionType

        decision = AgentDecision(
            agent_id="test_agent",
            decision=DecisionType.REVISE,
            reasoning="Need to adjust values",
            revision_plan="Increase beam by 10%",
        )

        assert decision.decision == DecisionType.REVISE
        d = decision.to_dict()
        assert d["decision"] == "revise"


class TestEscalation:
    """Test escalation system."""

    def test_escalation_level_enum(self):
        """Test EscalationLevel enum."""
        from magnet.protocol.escalation import EscalationLevel

        assert EscalationLevel.AGENT.value == "agent"
        assert EscalationLevel.SUPERVISOR.value == "supervisor"
        assert EscalationLevel.HUMAN.value == "human"

    def test_standard_rules_exist(self):
        """Test standard escalation rules are defined."""
        from magnet.protocol.escalation import STANDARD_RULES

        assert len(STANDARD_RULES) >= 4
        rule_ids = [r.rule_id for r in STANDARD_RULES]
        assert "ESC-TIMEOUT" in rule_ids
        assert "ESC-MAX-ITER" in rule_ids

    def test_escalation_handler_check(self):
        """Test EscalationHandler condition checking."""
        from magnet.protocol.escalation import EscalationHandler

        handler = EscalationHandler()

        # Max iterations context
        context = {"iteration": 5, "max_iterations": 5}
        rule = handler.check_escalation_needed(context)
        assert rule is not None
        assert "MAX-ITER" in rule.rule_id

    def test_escalation_handler_timeout(self):
        """Test timeout escalation."""
        from magnet.protocol.escalation import EscalationHandler

        handler = EscalationHandler()

        context = {"elapsed_seconds": 400, "timeout_seconds": 300}
        rule = handler.check_escalation_needed(context)
        assert rule is not None
        assert "TIMEOUT" in rule.rule_id


class TestCycleLogger:
    """Test cycle logging."""

    def test_log_entry_to_dict(self):
        """Test CycleLogEntry serialization."""
        from magnet.protocol.cycle_logger import CycleLogEntry

        entry = CycleLogEntry(
            entry_id="log_001",
            cycle_id="cycle_001",
            iteration=1,
            event_type="proposal",
            message="Test proposal",
        )

        d = entry.to_dict()
        assert d["cycle_id"] == "cycle_001"
        assert d["event_type"] == "proposal"

    def test_cycle_logger_log_validation(self):
        """Test logging validation."""
        from magnet.protocol.cycle_logger import CycleLogger

        logger = CycleLogger()

        # Create mock result
        mock_result = MagicMock()
        mock_result.passed = True
        mock_result.error_count = 0
        mock_result.warning_count = 1
        mock_result.to_dict.return_value = {"passed": True}

        entry = logger.log_validation("cycle_001", 1, mock_result)

        assert entry.event_type == "validation"
        assert "passed" in entry.message

    def test_cycle_logger_get_entries(self):
        """Test filtering entries."""
        from magnet.protocol.cycle_logger import CycleLogger

        logger = CycleLogger()

        # Create mock proposal
        mock_proposal = MagicMock()
        mock_proposal.proposal_id = "prop_001"
        mock_proposal.to_dict.return_value = {}

        logger.log_proposal("cycle_001", 1, mock_proposal)
        logger.log_proposal("cycle_002", 1, mock_proposal)

        entries = logger.get_entries(cycle_id="cycle_001")
        assert len(entries) == 1


class TestCycleExecutor:
    """Test cycle executor."""

    def test_cycle_config_defaults(self):
        """Test CycleConfig default values."""
        from magnet.protocol.cycle_executor import CycleConfig

        config = CycleConfig()

        assert config.max_iterations == 5
        assert config.timeout_seconds == 300.0
        assert config.use_transactions is True

    def test_cycle_state_to_dict(self):
        """Test CycleState serialization."""
        from magnet.protocol.cycle_executor import CycleState

        state = CycleState(
            cycle_id="test_cycle",
            iteration=2,
        )

        d = state.to_dict()
        assert d["cycle_id"] == "test_cycle"
        assert d["iteration"] == 2


# ============================================================================
# SECTION 42: EXPLANATION ENGINE TESTS
# ============================================================================

class TestExplanationSchemas:
    """Test explanation schemas."""

    def test_explanation_level_enum(self):
        """Test ExplanationLevel enum."""
        from magnet.explain.schemas import ExplanationLevel

        assert ExplanationLevel.SUMMARY.value == "summary"
        assert ExplanationLevel.EXPERT.value == "expert"

    def test_parameter_diff(self):
        """Test ParameterDiff."""
        from magnet.explain.schemas import ParameterDiff

        diff = ParameterDiff(
            path="hull.beam",
            name="Beam",
            old_value=5.0,
            new_value=6.0,
            change_percent=20.0,
            significance="major",
        )

        d = diff.to_dict()
        assert d["change_percent"] == 20.0
        assert d["significance"] == "major"

    def test_validator_summary_default_name(self):
        """Test v1.1 validator_name default."""
        from magnet.explain.schemas import ValidatorSummary

        summary = ValidatorSummary(passed=True)

        assert summary.validator_name == "unknown"

    def test_warning_to_dict(self):
        """Test Warning serialization."""
        from magnet.explain.schemas import Warning

        warning = Warning(
            severity="error",
            category="stability",
            message="GM too low",
            suggestion="Increase beam",
        )

        d = warning.to_dict()
        assert d["severity"] == "error"
        assert d["suggestion"] == "Increase beam"


class TestTraceCollector:
    """Test trace collector."""

    def test_calculation_step(self):
        """Test CalculationStep."""
        from magnet.explain.trace_collector import CalculationStep

        step = CalculationStep(
            step_id=1,
            name="Block Coefficient",
            formula="Cb = V / (L * B * T)",
            inputs={"L": 30, "B": 6, "T": 1.5},
            output=0.45,
        )

        d = step.to_dict()
        assert d["step"] == 1
        assert d["formula"] == "Cb = V / (L * B * T)"

    def test_trace_collector_flow(self):
        """Test trace collector workflow."""
        from magnet.explain.trace_collector import TraceCollector

        collector = TraceCollector()

        # Start trace
        trace = collector.start_trace("trace_001", "GMCalculator")
        assert trace.trace_id == "trace_001"

        # Add steps
        trace.add_step(
            name="Calculate KB",
            formula="KB = 0.53 * T",
            inputs={"T": 1.5},
            output=0.795,
        )

        # Complete
        collector.complete_trace("trace_001", 0.5)

        # Retrieve
        completed = collector.get_trace("trace_001")
        assert completed.final_result == 0.5


class TestNarrativeGenerator:
    """Test narrative generator."""

    def test_get_parameter_name(self):
        """Test parameter name lookup."""
        from magnet.explain.narrative import NarrativeGenerator

        gen = NarrativeGenerator()

        assert gen.get_parameter_name("hull.beam") == "Beam"
        assert gen.get_parameter_name("hull.loa") == "Length Overall"

        # v1.1: Test aliases
        assert gen.get_parameter_name("performance.max_speed_kts") == "Maximum Speed"
        assert gen.get_parameter_name("performance.max_speed_knots") == "Maximum Speed"

    def test_generate_diffs(self):
        """Test diff generation."""
        from magnet.explain.narrative import NarrativeGenerator

        gen = NarrativeGenerator()

        old_state = {"hull": {"beam": 5.0}}
        new_state = {"hull": {"beam": 6.0}}

        diffs = gen._generate_diffs(old_state, new_state)

        assert len(diffs) == 1
        assert diffs[0].old_value == 5.0
        assert diffs[0].new_value == 6.0
        assert diffs[0].change_percent == 20.0


class TestFormatters:
    """Test explanation formatters."""

    def test_chat_formatter(self):
        """Test ChatFormatter."""
        from magnet.explain.formatters import ChatFormatter
        from magnet.explain.schemas import Explanation, ExplanationLevel

        formatter = ChatFormatter()

        explanation = Explanation(
            level=ExplanationLevel.STANDARD,
            summary="Test summary",
            narrative="Test narrative",
        )

        output = formatter.format(explanation)

        assert "**Summary:**" in output
        assert "Test summary" in output

    def test_dashboard_formatter(self):
        """Test DashboardFormatter."""
        from magnet.explain.formatters import DashboardFormatter
        from magnet.explain.schemas import Explanation, ValidatorSummary

        formatter = DashboardFormatter()

        explanation = Explanation(
            summary="All passed",
            validator_summaries=[
                ValidatorSummary(validator_name="bounds", passed=True),
            ],
        )

        output = formatter.format(explanation)

        assert "## Status:" in output
        assert "[PASSED]" in output


# ============================================================================
# SECTION 43: ERROR TAXONOMY TESTS
# ============================================================================

class TestErrorTaxonomy:
    """Test error taxonomy."""

    def test_error_severity_enum(self):
        """Test ErrorSeverity enum."""
        from magnet.errors.taxonomy import ErrorSeverity

        assert ErrorSeverity.ERROR.value == "error"
        assert ErrorSeverity.CRITICAL.value == "critical"

    def test_error_code_enum(self):
        """Test ErrorCode values."""
        from magnet.errors.taxonomy import ErrorCode

        assert ErrorCode.VAL_FAILED.value == 1001
        assert ErrorCode.BND_EXCEEDED.value == 3001
        assert ErrorCode.STA_TRANSACTION.value == 5005  # v1.1

    def test_magnet_error_creation(self):
        """Test MAGNETError creation."""
        from magnet.errors.taxonomy import MAGNETError, ErrorCode, ErrorSeverity

        error = MAGNETError(
            code=ErrorCode.BND_EXCEEDED,
            severity=ErrorSeverity.ERROR,
            message="Value out of bounds",
            path="hull.beam",
        )

        assert len(error.error_id) == 8
        assert error.recoverable is True

    def test_create_validation_error(self):
        """Test validation error factory."""
        from magnet.errors.taxonomy import create_validation_error

        error = create_validation_error(
            message="Invalid value",
            source="bounds_validator",
            path="hull.draft",
            actual=10.0,
            expected=5.0,
        )

        assert error.code.value == 1001
        assert error.path == "hull.draft"

    def test_create_bounds_error(self):
        """Test bounds error factory."""
        from magnet.errors.taxonomy import create_bounds_error

        error = create_bounds_error(
            message="Beam too small",
            source="bounds",
            path="hull.beam",
            actual=2.0,
            min_val=3.0,
            max_val=10.0,
        )

        assert "adjust_value" in error.recovery_options

    def test_create_physics_error(self):
        """Test physics error factory."""
        from magnet.errors.taxonomy import create_physics_error

        error = create_physics_error(
            message="Negative displacement",
            source="physics",
        )

        assert error.recoverable is False
        assert error.severity.value == "critical"

    def test_create_transaction_error(self):
        """Test v1.1 transaction error factory."""
        from magnet.errors.taxonomy import create_transaction_error

        error = create_transaction_error(
            message="Transaction failed",
            transaction_id="tx_001",
        )

        assert error.transaction_id == "tx_001"
        assert "rollback" in error.recovery_options


class TestRecovery:
    """Test error recovery."""

    def test_recovery_strategy_enum(self):
        """Test RecoveryStrategy enum."""
        from magnet.errors.recovery import RecoveryStrategy

        assert RecoveryStrategy.RETRY.value == "retry"
        assert RecoveryStrategy.FALLBACK.value == "fallback"

    def test_recovery_strategies_exist(self):
        """Test recovery strategies are defined."""
        from magnet.errors.recovery import RECOVERY_STRATEGIES
        from magnet.errors.taxonomy import ErrorCode

        assert ErrorCode.BND_MINIMUM in RECOVERY_STRATEGIES
        assert ErrorCode.STA_TRANSACTION in RECOVERY_STRATEGIES  # v1.1

    def test_recovery_executor_no_strategies(self):
        """Test recovery with no strategies."""
        from magnet.errors.recovery import RecoveryExecutor
        from magnet.errors.taxonomy import MAGNETError, ErrorCode

        executor = RecoveryExecutor()

        error = MAGNETError(
            code=ErrorCode.VAL_SCHEMA,  # No auto strategies
            message="Schema error",
        )

        result = executor.attempt_recovery(error, auto_only=True)

        assert result.success is False
        assert result.requires_escalation is True


class TestErrorAggregator:
    """Test error aggregator."""

    def test_add_and_count(self):
        """Test adding errors and counting."""
        from magnet.errors.aggregator import ErrorAggregator
        from magnet.errors.taxonomy import MAGNETError, ErrorSeverity

        agg = ErrorAggregator()

        agg.add(MAGNETError(severity=ErrorSeverity.ERROR, message="Error 1"))
        agg.add(MAGNETError(severity=ErrorSeverity.WARNING, message="Warning 1"))

        assert agg.has_errors() is True
        assert agg.has_critical() is False

    def test_generate_report(self):
        """Test report generation."""
        from magnet.errors.aggregator import ErrorAggregator
        from magnet.errors.taxonomy import MAGNETError, ErrorSeverity

        agg = ErrorAggregator()

        agg.add(MAGNETError(severity=ErrorSeverity.ERROR, message="E1"))
        agg.add(MAGNETError(severity=ErrorSeverity.CRITICAL, message="C1"))

        report = agg.generate_report()

        assert report.total_errors == 2
        assert len(report.critical_errors) == 1
        assert "critical" in report.summary.lower()


# ============================================================================
# SECTION 44: TRANSACTION MODEL TESTS
# ============================================================================

class TestTransactionSchemas:
    """Test transaction schemas."""

    def test_transaction_status_enum(self):
        """Test TransactionStatus enum."""
        from magnet.transactions.schemas import TransactionStatus

        assert TransactionStatus.ACTIVE.value == "active"
        assert TransactionStatus.COMMITTED.value == "committed"

    def test_isolation_level_enum(self):
        """Test IsolationLevel enum."""
        from magnet.transactions.schemas import IsolationLevel

        assert IsolationLevel.READ_COMMITTED.value == "read_committed"

    def test_state_change(self):
        """Test StateChange creation."""
        from magnet.transactions.schemas import StateChange

        change = StateChange(
            change_id="ch_001",
            transaction_id="tx_001",
            path="hull.beam",
            old_value=5.0,
            new_value=6.0,
        )

        d = change.to_dict()
        assert d["path"] == "hull.beam"

    def test_transaction_creation(self):
        """Test Transaction creation."""
        from magnet.transactions.schemas import Transaction, TransactionStatus

        tx = Transaction(
            source="test",
            description="Test transaction",
        )

        assert len(tx.transaction_id) == 8
        assert tx.status == TransactionStatus.PENDING


class TestTransactionManager:
    """Test transaction manager."""

    def test_begin_transaction(self):
        """Test beginning a transaction."""
        from magnet.transactions.manager import TransactionManager
        from magnet.transactions.schemas import TransactionStatus

        mock_state = MagicMock()
        manager = TransactionManager(mock_state)

        tx = manager.begin(source="test")

        assert tx.status == TransactionStatus.ACTIVE
        assert manager.active_transaction_id == tx.transaction_id

    def test_commit_transaction(self):
        """Test committing a transaction."""
        from magnet.transactions.manager import TransactionManager

        mock_state = MagicMock()
        manager = TransactionManager(mock_state)

        tx = manager.begin()
        result = manager.commit(tx.transaction_id)

        assert result is True
        assert manager.active_transaction is None

    def test_rollback_transaction(self):
        """Test rolling back a transaction."""
        from magnet.transactions.manager import TransactionManager

        mock_state = MagicMock()
        manager = TransactionManager(mock_state)

        tx = manager.begin()
        result = manager.rollback(tx.transaction_id)

        assert result is True
        assert manager.active_transaction is None

    def test_nested_transactions(self):
        """Test nested transactions."""
        from magnet.transactions.manager import TransactionManager

        mock_state = MagicMock()
        manager = TransactionManager(mock_state)

        tx1 = manager.begin(source="outer")
        tx2 = manager.begin(source="inner")

        assert tx2.parent_transaction_id == tx1.transaction_id

    def test_context_manager(self):
        """Test transaction context manager."""
        from magnet.transactions.manager import TransactionManager

        mock_state = MagicMock()
        manager = TransactionManager(mock_state)

        with manager.transaction(source="test"):
            assert manager.active_transaction is not None

        assert manager.active_transaction is None

    def test_atomic_batch(self):
        """Test AtomicBatch."""
        from magnet.transactions.manager import AtomicBatch

        mock_state = MagicMock()

        with AtomicBatch(mock_state) as batch:
            batch.write("hull.beam", 6.0)

        # Verify write was called
        assert mock_state.set.called or mock_state.write.called


# ============================================================================
# SECTION 45: DESIGN LIFECYCLE TESTS
# ============================================================================

class TestVersions:
    """Test version management."""

    def test_version_status_enum(self):
        """Test VersionStatus enum."""
        from magnet.lifecycle.versions import VersionStatus

        assert VersionStatus.DRAFT.value == "draft"
        assert VersionStatus.RELEASED.value == "released"

    def test_design_version_string(self):
        """Test version string generation."""
        from magnet.lifecycle.versions import DesignVersion

        version = DesignVersion(major=1, minor=2, patch=3)

        assert version.version_string == "1.2.3"

    def test_design_branch(self):
        """Test DesignBranch."""
        from magnet.lifecycle.versions import DesignBranch

        branch = DesignBranch(
            branch_id="br_001",
            name="feature-test",
            branch_type="feature",
        )

        d = branch.to_dict()
        assert d["name"] == "feature-test"

    def test_compute_state_hash_deterministic(self):
        """Test v1.1 deterministic hashing."""
        from magnet.lifecycle.versions import compute_state_hash

        state = {"hull": {"beam": 5.0, "draft": 1.5}}

        hash1 = compute_state_hash(state)
        hash2 = compute_state_hash(state)

        assert hash1 == hash2

    def test_compute_state_hash_excludes_timestamps(self):
        """Test hash excludes timestamp fields."""
        from magnet.lifecycle.versions import compute_state_hash
        from datetime import datetime

        state1 = {"hull": {"beam": 5.0}, "created_at": "2024-01-01"}
        state2 = {"hull": {"beam": 5.0}, "created_at": "2024-12-01"}

        # Should be same hash (created_at excluded)
        assert compute_state_hash(state1) == compute_state_hash(state2)


class TestLifecycleManager:
    """Test lifecycle manager."""

    def test_create_version(self):
        """Test creating a version."""
        from magnet.lifecycle.manager import LifecycleManager

        mock_state = MagicMock()
        mock_state.to_dict.return_value = {"hull": {"beam": 5.0}}

        manager = LifecycleManager(mock_state)

        version = manager.create_version(
            description="Initial version",
            changes=["Created hull"],
        )

        assert version.major == 0
        assert version.minor == 1
        assert version.patch == 0

    def test_version_bump(self):
        """Test version bumping."""
        from magnet.lifecycle.manager import LifecycleManager

        mock_state = MagicMock()
        mock_state.to_dict.return_value = {"hull": {"beam": 5.0}}

        manager = LifecycleManager(mock_state)

        v1 = manager.create_version(description="v1")
        v2 = manager.create_version(description="v2", bump="minor")
        v3 = manager.create_version(description="v3", bump="major")

        assert v1.version_string == "0.1.0"
        assert v2.version_string == "0.2.0"
        assert v3.version_string == "1.0.0"

    def test_list_versions(self):
        """Test listing versions."""
        from magnet.lifecycle.manager import LifecycleManager

        mock_state = MagicMock()
        mock_state.to_dict.return_value = {}

        manager = LifecycleManager(mock_state)

        manager.create_version(description="v1")
        manager.create_version(description="v2")

        versions = manager.list_versions()

        assert len(versions) == 2


class TestDesignExporter:
    """Test design export."""

    def test_export_format_enum(self):
        """Test ExportFormat enum."""
        from magnet.lifecycle.export import ExportFormat

        assert ExportFormat.JSON.value == "json"
        assert ExportFormat.CSV.value == "csv"

    def test_export_config_defaults(self):
        """Test ExportConfig defaults."""
        from magnet.lifecycle.export import ExportConfig

        config = ExportConfig()

        assert config.include_hull is True
        assert config.pretty_print is True

    def test_export_summary(self):
        """Test summary export."""
        from magnet.lifecycle.export import DesignExporter

        mock_state = MagicMock()
        mock_state.to_dict.return_value = {
            "hull": {"loa": 30.0, "beam": 6.0, "draft": 1.5},
        }

        exporter = DesignExporter(mock_state)
        summary = exporter.export_summary()

        assert "hull" in summary
        assert summary["hull"]["loa_m"] == 30.0


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestGlueIntegration:
    """Integration tests for glue modules."""

    def test_protocol_cycle_flow(self):
        """Test basic protocol cycle flow."""
        from magnet.protocol.schemas import (
            Proposal, ParameterChange, ValidationResult, AgentDecision, DecisionType
        )

        # Create proposal
        proposal = Proposal(
            agent_id="test_agent",
            phase="concept",
            changes=[
                ParameterChange(
                    path="hull.beam",
                    old_value=5.0,
                    new_value=6.0,
                )
            ],
        )

        # Create validation result
        result = ValidationResult(
            proposal_id=proposal.proposal_id,
            passed=True,
            validators_run=["bounds"],
        )

        # Agent decision
        decision = AgentDecision(
            agent_id=proposal.agent_id,
            decision=DecisionType.APPROVE,
        )

        assert proposal.to_dict()["status"] == "pending"
        assert result.passed is True
        assert decision.decision == DecisionType.APPROVE

    def test_error_to_explanation_flow(self):
        """Test error to explanation flow."""
        from magnet.errors.taxonomy import create_bounds_error
        from magnet.explain.schemas import Warning

        # Create error
        error = create_bounds_error(
            message="Beam exceeds maximum",
            source="bounds_validator",
            path="hull.beam",
            actual=15.0,
            min_val=3.0,
            max_val=12.0,
        )

        # Convert to warning for explanation
        warning = Warning(
            severity="error",
            category=error.source,
            message=error.message,
            suggestion="Reduce beam to within bounds",
        )

        assert warning.severity == "error"
        assert "beam" in warning.message.lower()

    def test_transaction_with_lifecycle(self):
        """Test transaction and lifecycle integration."""
        from magnet.transactions.manager import TransactionManager
        from magnet.lifecycle.manager import LifecycleManager

        mock_state = MagicMock()
        mock_state.to_dict.return_value = {"hull": {"beam": 5.0}}

        # Begin transaction
        tx_manager = TransactionManager(mock_state)
        lifecycle = LifecycleManager(mock_state)

        with tx_manager.transaction(source="design_change"):
            # Create version within transaction
            version = lifecycle.create_version(description="Within tx")
            assert version is not None

        # Transaction should be committed
        assert tx_manager.active_transaction is None
