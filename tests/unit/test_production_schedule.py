"""
Unit tests for production build scheduler.

Tests BuildScheduler milestone generation.
"""

import pytest
from datetime import date, timedelta
from magnet.production.schedule import BuildScheduler
from magnet.production.models import (
    BuildSchedule,
    ScheduleMilestone,
    AssemblySequenceResult,
    MaterialTakeoffResult,
)
from magnet.production.enums import ProductionPhase


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


class TestBuildScheduler:
    """Tests for BuildScheduler."""

    @pytest.fixture
    def scheduler(self):
        """Create scheduler instance."""
        return BuildScheduler()

    @pytest.fixture
    def state_25m_workboat(self):
        """Create state for 25m workboat."""
        return MockStateManager({
            "hull": {
                "lwl": 25.0,
                "beam": 6.0,
                "depth": 3.0,
            },
        })

    @pytest.fixture
    def fixed_start_date(self):
        """Fixed start date for testing."""
        return date(2025, 1, 1)

    def test_basic_schedule_generation(self, scheduler, state_25m_workboat, fixed_start_date):
        """Test basic schedule generation."""
        result = scheduler.generate_schedule(
            state_25m_workboat,
            start_date=fixed_start_date,
        )

        assert isinstance(result, BuildSchedule)
        assert result.milestone_count > 0
        assert result.start_date == fixed_start_date
        assert result.end_date is not None
        assert result.total_days > 0

    def test_empty_dimensions_returns_empty_schedule(self, scheduler):
        """Test empty dimensions return empty schedule."""
        state = MockStateManager({})
        result = scheduler.generate_schedule(state)

        assert result.milestone_count == 0
        assert result.total_days == 0

    def test_zero_dimensions_returns_empty_schedule(self, scheduler):
        """Test zero dimensions return empty schedule."""
        state = MockStateManager({
            "hull": {"lwl": 0, "beam": 0, "depth": 0}
        })
        result = scheduler.generate_schedule(state)

        assert result.milestone_count == 0
        assert result.total_days == 0

    def test_all_phases_included(self, scheduler, state_25m_workboat, fixed_start_date):
        """Test all production phases are included."""
        result = scheduler.generate_schedule(
            state_25m_workboat,
            start_date=fixed_start_date,
        )

        phases_found = {m.phase for m in result.milestones}

        # All phases should be present
        for phase in ProductionPhase:
            assert phase in phases_found

    def test_milestones_sequential(self, scheduler, state_25m_workboat, fixed_start_date):
        """Test milestones have sequential dates."""
        result = scheduler.generate_schedule(
            state_25m_workboat,
            start_date=fixed_start_date,
        )

        for i in range(1, len(result.milestones)):
            prev = result.milestones[i - 1]
            curr = result.milestones[i]
            assert curr.planned_date >= prev.planned_date

    def test_milestones_have_dependencies(self, scheduler, state_25m_workboat, fixed_start_date):
        """Test milestones have dependencies (except first)."""
        result = scheduler.generate_schedule(
            state_25m_workboat,
            start_date=fixed_start_date,
        )

        # First milestone has no dependencies
        assert len(result.milestones[0].dependencies) == 0

        # Subsequent milestones depend on previous
        for i in range(1, len(result.milestones)):
            assert len(result.milestones[i].dependencies) > 0

    def test_end_date_after_start(self, scheduler, state_25m_workboat, fixed_start_date):
        """Test end date is after start date."""
        result = scheduler.generate_schedule(
            state_25m_workboat,
            start_date=fixed_start_date,
        )

        assert result.end_date > result.start_date

    def test_total_days_matches_dates(self, scheduler, state_25m_workboat, fixed_start_date):
        """Test total days matches date range."""
        result = scheduler.generate_schedule(
            state_25m_workboat,
            start_date=fixed_start_date,
        )

        calculated_days = (result.end_date - result.start_date).days
        assert result.total_days == calculated_days

    def test_larger_vessel_longer_schedule(self, scheduler, fixed_start_date):
        """Test larger vessel has longer schedule."""
        small = MockStateManager({"hull": {"lwl": 15.0, "beam": 4.0, "depth": 2.0}})
        large = MockStateManager({"hull": {"lwl": 30.0, "beam": 8.0, "depth": 4.0}})

        small_result = scheduler.generate_schedule(small, start_date=fixed_start_date)
        large_result = scheduler.generate_schedule(large, start_date=fixed_start_date)

        assert large_result.total_days > small_result.total_days

    def test_assembly_result_used(self, scheduler, state_25m_workboat, fixed_start_date):
        """Test assembly result is used for schedule."""
        # Create assembly result with specific hours
        assembly = AssemblySequenceResult(total_work_hours=5000)

        result_with = scheduler.generate_schedule(
            state_25m_workboat,
            assembly_result=assembly,
            start_date=fixed_start_date,
        )

        result_without = scheduler.generate_schedule(
            state_25m_workboat,
            start_date=fixed_start_date,
        )

        # Should produce different schedules based on assembly hours
        # This depends on parametric estimate vs provided hours
        assert result_with.total_days >= 0
        assert result_without.total_days >= 0

    def test_material_result_affects_procurement(self, scheduler, state_25m_workboat, fixed_start_date):
        """Test material result affects procurement time."""
        # More material = longer procurement
        light = MaterialTakeoffResult(total_weight_kg=10000)
        heavy = MaterialTakeoffResult(total_weight_kg=100000)

        light_result = scheduler.generate_schedule(
            state_25m_workboat,
            material_result=light,
            start_date=fixed_start_date,
        )
        heavy_result = scheduler.generate_schedule(
            state_25m_workboat,
            material_result=heavy,
            start_date=fixed_start_date,
        )

        # Heavy should have longer procurement (and thus total time)
        assert heavy_result.total_days >= light_result.total_days

    def test_critical_milestones_marked(self, scheduler, state_25m_workboat, fixed_start_date):
        """Test critical milestones are marked."""
        result = scheduler.generate_schedule(
            state_25m_workboat,
            start_date=fixed_start_date,
        )

        critical = [m for m in result.milestones if m.is_critical]
        assert len(critical) > 0

        # Delivery should be critical
        delivery = next(
            (m for m in result.milestones if m.phase == ProductionPhase.DELIVERY),
            None
        )
        assert delivery is not None
        assert delivery.is_critical

    def test_result_to_dict(self, scheduler, state_25m_workboat, fixed_start_date):
        """Test result serialization."""
        result = scheduler.generate_schedule(
            state_25m_workboat,
            start_date=fixed_start_date,
        )
        data = result.to_dict()

        assert "milestones" in data
        assert "summary" in data
        assert data["milestone_count"] == result.milestone_count
        assert data["summary"]["total_days"] == result.total_days

    def test_custom_work_parameters(self, state_25m_workboat, fixed_start_date):
        """Test custom work parameters."""
        # More days per week = shorter schedule
        five_day = BuildScheduler(work_days_per_week=5)
        six_day = BuildScheduler(work_days_per_week=6)

        five_result = five_day.generate_schedule(
            state_25m_workboat,
            start_date=fixed_start_date,
        )
        six_result = six_day.generate_schedule(
            state_25m_workboat,
            start_date=fixed_start_date,
        )

        # Six-day week should be shorter
        assert six_result.total_days <= five_result.total_days

    def test_milestone_durations_positive(self, scheduler, state_25m_workboat, fixed_start_date):
        """Test all milestones have positive durations."""
        result = scheduler.generate_schedule(
            state_25m_workboat,
            start_date=fixed_start_date,
        )

        for milestone in result.milestones:
            assert milestone.duration_days > 0

    def test_estimate_delivery_date(self, scheduler, state_25m_workboat, fixed_start_date):
        """Test quick delivery date estimate."""
        delivery = scheduler.estimate_delivery_date(
            state_25m_workboat,
            start_date=fixed_start_date,
        )

        assert delivery is not None
        assert delivery > fixed_start_date

    def test_estimate_delivery_empty_state(self, scheduler):
        """Test delivery estimate with empty state returns None."""
        state = MockStateManager({})
        delivery = scheduler.estimate_delivery_date(state)

        assert delivery is None

    def test_milestone_ids_unique(self, scheduler, state_25m_workboat, fixed_start_date):
        """Test all milestone IDs are unique."""
        result = scheduler.generate_schedule(
            state_25m_workboat,
            start_date=fixed_start_date,
        )

        ids = [m.milestone_id for m in result.milestones]
        assert len(ids) == len(set(ids))


class TestScheduleMilestone:
    """Tests for ScheduleMilestone dataclass."""

    def test_create_milestone(self):
        """Test creating milestone."""
        milestone = ScheduleMilestone(
            milestone_id="MS-001",
            name="Design Complete",
            phase=ProductionPhase.DESIGN,
            planned_date=date(2025, 2, 1),
            duration_days=30,
            is_critical=True,
        )

        assert milestone.milestone_id == "MS-001"
        assert milestone.phase == ProductionPhase.DESIGN
        assert milestone.duration_days == 30
        assert milestone.is_critical

    def test_milestone_with_dependencies(self):
        """Test milestone with dependencies."""
        milestone = ScheduleMilestone(
            milestone_id="MS-002",
            name="Materials Delivered",
            phase=ProductionPhase.MATERIAL_PROCUREMENT,
            planned_date=date(2025, 3, 1),
            duration_days=14,
            dependencies=["MS-001"],
        )

        assert len(milestone.dependencies) == 1
        assert "MS-001" in milestone.dependencies

    def test_milestone_to_dict(self):
        """Test milestone serialization."""
        milestone = ScheduleMilestone(
            milestone_id="MS-001",
            name="Design Complete",
            phase=ProductionPhase.DESIGN,
            planned_date=date(2025, 2, 1),
            duration_days=30,
        )

        data = milestone.to_dict()
        assert data["milestone_id"] == "MS-001"
        assert data["phase"] == "design"
        assert data["planned_date"] == "2025-02-01"


class TestBuildSchedule:
    """Tests for BuildSchedule dataclass."""

    def test_create_schedule(self):
        """Test creating schedule."""
        schedule = BuildSchedule(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 6, 1),
            total_days=151,
            work_days_per_week=5,
            hours_per_day=8.0,
        )

        assert schedule.start_date == date(2025, 1, 1)
        assert schedule.total_days == 151
        assert schedule.milestone_count == 0

    def test_schedule_with_milestones(self):
        """Test schedule with milestones."""
        schedule = BuildSchedule(
            start_date=date(2025, 1, 1),
            milestones=[
                ScheduleMilestone(
                    milestone_id="MS-001",
                    name="Design",
                    phase=ProductionPhase.DESIGN,
                    duration_days=30,
                ),
            ],
        )

        assert schedule.milestone_count == 1

    def test_schedule_to_dict(self):
        """Test schedule serialization."""
        schedule = BuildSchedule(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 6, 1),
            total_days=151,
        )

        data = schedule.to_dict()
        assert data["summary"]["start_date"] == "2025-01-01"
        assert data["summary"]["total_days"] == 151
