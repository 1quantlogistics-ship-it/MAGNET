"""
production/schedule.py - Build schedule generator.

BRAVO OWNS THIS FILE.

Module 11 v1.1 - Build schedule from work packages.

v1.1 NOTE: Schedule code unchanged from v1.0 - no field name changes.
"""

from __future__ import annotations
from datetime import date, timedelta
from typing import TYPE_CHECKING, List, Dict, Optional

from .enums import ProductionPhase
from .models import (
    BuildSchedule,
    ScheduleMilestone,
    AssemblySequenceResult,
    MaterialTakeoffResult,
)

if TYPE_CHECKING:
    from ..core.state_manager import StateManager


class BuildScheduler:
    """
    Build schedule generator.

    Converts work packages and material requirements into a time-based
    schedule with milestones.
    """

    # Default phase durations as percentage of total
    PHASE_PERCENTAGES = {
        ProductionPhase.DESIGN: 0.10,
        ProductionPhase.MATERIAL_PROCUREMENT: 0.08,
        ProductionPhase.FABRICATION: 0.15,
        ProductionPhase.SUBASSEMBLY: 0.15,
        ProductionPhase.ASSEMBLY: 0.20,
        ProductionPhase.OUTFITTING: 0.15,
        ProductionPhase.PAINTING: 0.05,
        ProductionPhase.LAUNCH: 0.02,
        ProductionPhase.SEA_TRIALS: 0.05,
        ProductionPhase.DELIVERY: 0.05,
    }

    def __init__(
        self,
        work_days_per_week: int = 5,
        hours_per_day: float = 8.0,
        crew_size: int = 4,
    ):
        """
        Initialize build scheduler.

        Args:
            work_days_per_week: Working days per week (default 5)
            hours_per_day: Working hours per day (default 8)
            crew_size: Number of workers for parallel work
        """
        self.work_days_per_week = work_days_per_week
        self.hours_per_day = hours_per_day
        self.crew_size = crew_size

    def generate_schedule(
        self,
        state: "StateManager",
        assembly_result: Optional[AssemblySequenceResult] = None,
        material_result: Optional[MaterialTakeoffResult] = None,
        start_date: Optional[date] = None,
    ) -> BuildSchedule:
        """
        Generate build schedule.

        Args:
            state: StateManager with vessel data
            assembly_result: Pre-calculated assembly sequence (optional)
            material_result: Pre-calculated material takeoff (optional)
            start_date: Project start date (default today)

        Returns:
            BuildSchedule with milestones and timeline
        """
        schedule = BuildSchedule(
            work_days_per_week=self.work_days_per_week,
            hours_per_day=self.hours_per_day,
        )

        # Use today if no start date
        if start_date is None:
            start_date = date.today()

        schedule.start_date = start_date

        # Get vessel size for scaling
        lwl = state.get("hull.lwl", 0)
        if lwl <= 0:
            return schedule

        # Estimate total work hours
        if assembly_result and assembly_result.total_work_hours > 0:
            total_hours = assembly_result.total_work_hours
        else:
            # Parametric estimate based on length
            total_hours = self._estimate_total_hours(lwl)

        # Convert hours to working days
        hours_per_day_effective = self.hours_per_day * min(self.crew_size, 4) * 0.7
        total_work_days = int(total_hours / hours_per_day_effective)

        # Add procurement lead time based on material weight
        procurement_days = self._estimate_procurement_days(material_result, lwl)

        # Calculate phase durations
        phase_days = self._calculate_phase_days(total_work_days, procurement_days)

        # Create milestones
        current_date = start_date
        milestone_counter = 0

        for phase in ProductionPhase:
            days = phase_days.get(phase, 0)
            if days <= 0:
                continue

            milestone_counter += 1

            # Determine dependencies
            dependencies = []
            if schedule.milestones:
                dependencies = [schedule.milestones[-1].milestone_id]

            # Create milestone
            milestone = ScheduleMilestone(
                milestone_id=f"MS-{milestone_counter:03d}",
                name=self._get_phase_name(phase),
                phase=phase,
                planned_date=current_date,
                duration_days=days,
                dependencies=dependencies,
                is_critical=phase in self._critical_phases(),
            )
            schedule.milestones.append(milestone)

            # Advance date (skip weekends if needed)
            current_date = self._add_working_days(current_date, days)

        # Set end date
        schedule.end_date = current_date
        schedule.total_days = (current_date - start_date).days

        return schedule

    def _estimate_total_hours(self, lwl: float) -> float:
        """Estimate total work hours based on vessel length."""
        # Parametric: ~100 hours per meter of length for aluminum workboat
        base_hours = lwl * 100

        # Non-linear scaling for larger vessels
        if lwl > 20:
            base_hours *= 1.2
        if lwl > 30:
            base_hours *= 1.3

        return base_hours

    def _estimate_procurement_days(
        self,
        material_result: Optional[MaterialTakeoffResult],
        lwl: float,
    ) -> int:
        """Estimate material procurement lead time."""
        if material_result and material_result.total_weight_kg > 0:
            weight_mt = material_result.total_weight_kg / 1000.0
            # ~1 day per 2 tonnes, min 14 days
            return max(14, int(weight_mt / 2))
        else:
            # Parametric based on length
            return max(14, int(lwl * 0.8))

    def _calculate_phase_days(
        self, total_work_days: int, procurement_days: int
    ) -> Dict[ProductionPhase, int]:
        """Calculate duration for each phase."""
        phase_days = {}

        for phase, percentage in self.PHASE_PERCENTAGES.items():
            if phase == ProductionPhase.MATERIAL_PROCUREMENT:
                # Use actual procurement estimate
                days = procurement_days
            else:
                days = int(total_work_days * percentage)

            # Minimum duration for each phase
            min_days = {
                ProductionPhase.DESIGN: 7,
                ProductionPhase.MATERIAL_PROCUREMENT: 14,
                ProductionPhase.FABRICATION: 7,
                ProductionPhase.SUBASSEMBLY: 5,
                ProductionPhase.ASSEMBLY: 7,
                ProductionPhase.OUTFITTING: 5,
                ProductionPhase.PAINTING: 3,
                ProductionPhase.LAUNCH: 1,
                ProductionPhase.SEA_TRIALS: 2,
                ProductionPhase.DELIVERY: 1,
            }

            phase_days[phase] = max(days, min_days.get(phase, 1))

        return phase_days

    def _get_phase_name(self, phase: ProductionPhase) -> str:
        """Get human-readable phase name."""
        names = {
            ProductionPhase.DESIGN: "Design Complete",
            ProductionPhase.MATERIAL_PROCUREMENT: "Materials Delivered",
            ProductionPhase.FABRICATION: "Fabrication Complete",
            ProductionPhase.SUBASSEMBLY: "Subassemblies Complete",
            ProductionPhase.ASSEMBLY: "Hull Assembly Complete",
            ProductionPhase.OUTFITTING: "Outfitting Complete",
            ProductionPhase.PAINTING: "Painting Complete",
            ProductionPhase.LAUNCH: "Launch",
            ProductionPhase.SEA_TRIALS: "Sea Trials Complete",
            ProductionPhase.DELIVERY: "Delivery",
        }
        return names.get(phase, phase.value.replace("_", " ").title())

    def _critical_phases(self) -> List[ProductionPhase]:
        """Return phases that are on critical path."""
        return [
            ProductionPhase.DESIGN,
            ProductionPhase.MATERIAL_PROCUREMENT,
            ProductionPhase.ASSEMBLY,
            ProductionPhase.LAUNCH,
            ProductionPhase.DELIVERY,
        ]

    def _add_working_days(self, start: date, days: int) -> date:
        """Add working days to a date, accounting for weekends."""
        if self.work_days_per_week >= 7:
            return start + timedelta(days=days)

        current = start
        days_added = 0

        while days_added < days:
            current += timedelta(days=1)
            # Skip weekends (Saturday=5, Sunday=6)
            if self.work_days_per_week <= 5 and current.weekday() >= 5:
                continue
            elif self.work_days_per_week == 6 and current.weekday() == 6:
                continue
            days_added += 1

        return current

    def estimate_delivery_date(
        self,
        state: "StateManager",
        start_date: Optional[date] = None,
    ) -> Optional[date]:
        """
        Quick estimate of delivery date without full schedule.

        Args:
            state: StateManager with vessel data
            start_date: Project start date (default today)

        Returns:
            Estimated delivery date
        """
        lwl = state.get("hull.lwl", 0)
        if lwl <= 0:
            return None

        if start_date is None:
            start_date = date.today()

        # Quick estimate: ~3-4 days per meter of length
        days_per_meter = 3.5
        if lwl > 20:
            days_per_meter = 4.0
        if lwl > 30:
            days_per_meter = 4.5

        total_days = int(lwl * days_per_meter)

        # Add buffer
        total_days = int(total_days * 1.1)

        return self._add_working_days(start_date, total_days)
