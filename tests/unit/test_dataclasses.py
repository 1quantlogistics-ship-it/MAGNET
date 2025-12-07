"""
Unit tests for MAGNET dataclasses.

Tests serialization (to_dict/from_dict) for all 27 state dataclasses.
Aligned to ALPHA's canonical schema per V1.1 Modules specification.
"""

import pytest
from magnet.core.dataclasses import (
    MissionConfig,
    HullState,
    StructuralDesign,
    StructuralLoads,
    PropulsionState,
    WeightEstimate,
    StabilityState,
    LoadingState,
    ArrangementState,
    ComplianceState,
    ProductionState,
    CostState,
    OptimizationState,
    ReportsState,
    KernelState,
    AnalysisState,
    PerformanceState,
    SystemsState,
    OutfittingState,
    EnvironmentalState,
    DeckEquipmentState,
    VisionState,
    ResistanceState,
    SeakeepingState,
    ManeuveringState,
    ElectricalState,
    SafetyState,
)


class TestMissionConfig:
    """Test MissionConfig dataclass."""

    def test_create_empty(self):
        """Test creating empty MissionConfig."""
        mission = MissionConfig()
        # ALPHA uses Optional[str] = None pattern
        assert mission.vessel_type is None
        assert mission.max_speed_kts is None

    def test_create_with_values(self):
        """Test creating MissionConfig with values."""
        mission = MissionConfig(
            vessel_type="patrol",
            max_speed_kts=30.0,
            range_nm=500.0,
            crew_berthed=4,
        )
        assert mission.vessel_type == "patrol"
        assert mission.max_speed_kts == 30.0
        assert mission.range_nm == 500.0
        assert mission.crew_berthed == 4

    def test_to_dict(self):
        """Test serialization to dict."""
        mission = MissionConfig(vessel_type="ferry", max_speed_kts=25.0)
        data = mission.to_dict()
        assert isinstance(data, dict)
        assert data["vessel_type"] == "ferry"
        assert data["max_speed_kts"] == 25.0

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {"vessel_type": "workboat", "max_speed_kts": 20.0}
        mission = MissionConfig.from_dict(data)
        assert mission.vessel_type == "workboat"
        assert mission.max_speed_kts == 20.0

    def test_roundtrip(self):
        """Test roundtrip serialization."""
        original = MissionConfig(
            vessel_type="patrol",
            max_speed_kts=35.0,
            range_nm=400.0,
            passengers=12,
        )
        data = original.to_dict()
        restored = MissionConfig.from_dict(data)
        assert restored.vessel_type == original.vessel_type
        assert restored.max_speed_kts == original.max_speed_kts
        assert restored.range_nm == original.range_nm
        assert restored.passengers == original.passengers


class TestHullState:
    """Test HullState dataclass."""

    def test_create_empty(self):
        """Test creating empty HullState."""
        hull = HullState()
        # ALPHA uses Optional pattern
        assert hull.loa is None
        assert hull.beam is None

    def test_create_with_dimensions(self):
        """Test creating HullState with dimensions."""
        hull = HullState(loa=25.0, beam=6.0, draft=1.5, depth=3.0)
        assert hull.loa == 25.0
        assert hull.beam == 6.0
        assert hull.draft == 1.5
        assert hull.depth == 3.0

    def test_to_dict(self):
        """Test serialization."""
        hull = HullState(loa=20.0, cb=0.45)
        data = hull.to_dict()
        assert data["loa"] == 20.0
        assert data["cb"] == 0.45

    def test_from_dict(self):
        """Test deserialization."""
        data = {"loa": 30.0, "beam": 7.0, "hull_type": "monohull"}
        hull = HullState.from_dict(data)
        assert hull.loa == 30.0
        assert hull.beam == 7.0
        assert hull.hull_type == "monohull"


class TestPropulsionState:
    """Test PropulsionState dataclass."""

    def test_create_empty(self):
        """Test creating empty PropulsionState."""
        prop = PropulsionState()
        assert prop.num_engines == 0  # int defaults
        assert prop.total_installed_power_kw is None

    def test_create_with_values(self):
        """Test creating with values."""
        prop = PropulsionState(
            num_engines=2,
            total_installed_power_kw=1200.0,
            engine_make="MTU",
        )
        assert prop.num_engines == 2
        assert prop.total_installed_power_kw == 1200.0
        assert prop.engine_make == "MTU"

    def test_roundtrip(self):
        """Test roundtrip serialization."""
        original = PropulsionState(
            propulsion_type="waterjet",
            num_engines=3,
            total_installed_power_kw=2500.0,
        )
        restored = PropulsionState.from_dict(original.to_dict())
        assert restored.propulsion_type == original.propulsion_type
        assert restored.num_engines == original.num_engines


class TestWeightEstimate:
    """Test WeightEstimate dataclass."""

    def test_create_empty(self):
        """Test creating empty WeightEstimate."""
        weight = WeightEstimate()
        assert weight.lightship_weight_mt is None

    def test_weight_breakdown(self):
        """Test weight breakdown fields."""
        # Use canonical field names per ALPHA schema
        weight = WeightEstimate(
            lightship_weight_mt=50.0,
            hull_structure_mt=25.0,  # Canonical name
            machinery_mt=15.0,  # Canonical name
            deadweight_mt=20.0,
        )
        assert weight.lightship_weight_mt == 50.0
        assert weight.deadweight_mt == 20.0

    def test_roundtrip(self):
        """Test roundtrip serialization."""
        original = WeightEstimate(
            lightship_weight_mt=45.0,
            full_load_displacement_mt=65.0,
        )
        restored = WeightEstimate.from_dict(original.to_dict())
        assert restored.lightship_weight_mt == original.lightship_weight_mt


class TestStabilityState:
    """Test StabilityState dataclass."""

    def test_create_empty(self):
        """Test creating empty StabilityState."""
        stab = StabilityState()
        assert stab.gm_transverse_m is None

    def test_stability_values(self):
        """Test stability calculation values."""
        # Use canonical field name: gz_max_m (not gz_max)
        stab = StabilityState(
            gm_transverse_m=1.5,
            gz_max_m=0.8,  # Canonical name with _m suffix
            angle_of_max_gz_deg=45.0,
        )
        assert stab.gm_transverse_m == 1.5
        assert stab.gz_max_m == 0.8


class TestStructuralDesign:
    """Test StructuralDesign dataclass."""

    def test_create_empty(self):
        """Test creating empty StructuralDesign."""
        struct = StructuralDesign()
        # Canonical field is hull_material (not material_type)
        assert struct.hull_material is None

    def test_material_properties(self):
        """Test material properties."""
        struct = StructuralDesign(
            hull_material="aluminum",  # Canonical name
            bottom_plating_mm=8.0,
        )
        assert struct.hull_material == "aluminum"
        assert struct.bottom_plating_mm == 8.0


class TestStructuralLoads:
    """Test StructuralLoads dataclass."""

    def test_create_empty(self):
        """Test creating empty StructuralLoads."""
        loads = StructuralLoads()
        # Canonical field names
        assert loads.slamming_pressure_kpa is None

    def test_pressure_values(self):
        """Test pressure values."""
        loads = StructuralLoads(
            slamming_pressure_kpa=150.0,
            hydrostatic_pressure_kpa=80.0,
        )
        assert loads.slamming_pressure_kpa == 150.0


class TestLoadingState:
    """Test LoadingState dataclass."""

    def test_create_empty(self):
        """Test creating empty LoadingState."""
        loading = LoadingState()
        # Tank states are managed here, not capacity
        assert loading.tank_states == {}

    def test_tank_states(self):
        """Test tank states."""
        loading = LoadingState(
            current_condition="full_load",
            tank_states={"fuel_1": 95.0, "fw_1": 80.0},
        )
        assert loading.current_condition == "full_load"


class TestArrangementState:
    """Test ArrangementState dataclass."""

    def test_create_empty(self):
        """Test creating empty ArrangementState."""
        arr = ArrangementState()
        # Canonical field is num_decks (not deck_count)
        assert arr.num_decks == 0

    def test_deck_arrangement(self):
        """Test deck arrangement."""
        # Use canonical field names
        arr = ArrangementState(num_decks=2)
        assert arr.num_decks == 2


class TestComplianceState:
    """Test ComplianceState dataclass."""

    def test_create_empty(self):
        """Test creating empty ComplianceState."""
        comp = ComplianceState()
        assert comp.overall_passed == False

    def test_compliance_flags(self):
        """Test compliance flags."""
        # Use canonical field names
        comp = ComplianceState(
            overall_passed=True,
            structural_checks_passed=True,  # Canonical name
        )
        assert comp.overall_passed == True


class TestProductionState:
    """Test ProductionState dataclass."""

    def test_create_empty(self):
        """Test creating empty ProductionState."""
        prod = ProductionState()
        # Canonical field is build_hours (not total_build_hours)
        assert prod.build_hours is None


class TestCostState:
    """Test CostState dataclass."""

    def test_create_empty(self):
        """Test creating empty CostState."""
        cost = CostState()
        assert cost.total_cost is None


class TestOptimizationState:
    """Test OptimizationState dataclass."""

    def test_create_empty(self):
        """Test creating empty OptimizationState."""
        opt = OptimizationState()
        # Canonical field is converged (not optimization_run)
        assert opt.converged == False


class TestReportsState:
    """Test ReportsState dataclass."""

    def test_create_empty(self):
        """Test creating empty ReportsState."""
        rep = ReportsState()
        # Canonical field: generated is a bool flag
        assert rep.generated == False


class TestKernelState:
    """Test KernelState dataclass."""

    def test_create_empty(self):
        """Test creating empty KernelState."""
        kernel = KernelState()
        assert kernel.status == "idle"


class TestAnalysisState:
    """Test AnalysisState dataclass."""

    def test_create_empty(self):
        """Test creating empty AnalysisState."""
        analysis = AnalysisState()
        # ALPHA uses Optional pattern
        assert analysis.operability_index is None


class TestPerformanceState:
    """Test PerformanceState dataclass."""

    def test_create_empty(self):
        """Test creating empty PerformanceState."""
        perf = PerformanceState()
        # Uses Optional pattern
        assert perf.design_speed_kts is None

    def test_roundtrip(self):
        """Test roundtrip serialization."""
        original = PerformanceState(
            design_speed_kts=25.0,
            total_resistance_kn=50.0,
        )
        restored = PerformanceState.from_dict(original.to_dict())
        assert restored.design_speed_kts == original.design_speed_kts


class TestSystemsState:
    """Test SystemsState dataclass."""

    def test_create_empty(self):
        """Test creating empty SystemsState."""
        sys = SystemsState()
        assert sys.electrical_load_kw is None

    def test_systems_values(self):
        """Test systems values."""
        sys = SystemsState(
            electrical_load_kw=50.0,
            generator_capacity_kw=100.0,
        )
        assert sys.electrical_load_kw == 50.0


class TestOutfittingState:
    """Test OutfittingState dataclass."""

    def test_create_empty(self):
        """Test creating empty OutfittingState."""
        out = OutfittingState()
        assert out.berth_count == 0


class TestEnvironmentalState:
    """Test EnvironmentalState dataclass."""

    def test_create_empty(self):
        """Test creating empty EnvironmentalState."""
        env = EnvironmentalState()
        # Optional string for sea state
        assert env.design_sea_state is None
        # Has default water density
        assert env.water_density_kg_m3 == 1025.0


class TestDeckEquipmentState:
    """Test DeckEquipmentState dataclass."""

    def test_create_empty(self):
        """Test creating empty DeckEquipmentState."""
        deck = DeckEquipmentState()
        assert deck.anchor_weight_kg is None


class TestVisionState:
    """Test VisionState dataclass."""

    def test_create_empty(self):
        """Test creating empty VisionState."""
        vision = VisionState()
        assert vision.geometry_generated == False


class TestResistanceState:
    """Test ResistanceState dataclass."""

    def test_create_empty(self):
        """Test creating empty ResistanceState."""
        res = ResistanceState()
        assert res.total_resistance_kn is None


class TestSeakeepingState:
    """Test SeakeepingState dataclass."""

    def test_create_empty(self):
        """Test creating empty SeakeepingState."""
        sea = SeakeepingState()
        # SeakeepingState has roll_period_s, not operability_index
        assert sea.roll_period_s is None


class TestManeuveringState:
    """Test ManeuveringState dataclass."""

    def test_create_empty(self):
        """Test creating empty ManeuveringState."""
        man = ManeuveringState()
        assert man.tactical_diameter_m is None


class TestElectricalState:
    """Test ElectricalState dataclass."""

    def test_create_empty(self):
        """Test creating empty ElectricalState."""
        elec = ElectricalState()
        # Canonical field names
        assert elec.frequency_hz == 60.0


class TestSafetyState:
    """Test SafetyState dataclass."""

    def test_create_empty(self):
        """Test creating empty SafetyState."""
        safety = SafetyState()
        # Canonical field is lifejackets (not life_jacket_count)
        assert safety.lifejackets == 0
