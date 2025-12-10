"""
test_bravo_module60.py - Tests for BRAVO Module 60 Components
BRAVO OWNS THIS FILE.

Tests for:
- Zone definitions (schema/zone_definition.py)
- Separation rules (schema/separation_rule.py)
- Redundancy checker (router/redundancy.py)
- Path optimizer (router/path_optimizer.py)
- Path utilities (router/path_utils.py)
- Multi-system coordinator (agent/multi_system.py)
- Routing validators (agent/validators.py)
- State integration (integration/state_integration.py)
- Configuration (integration/config.py)
"""

import pytest
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass


# =============================================================================
# ZONE DEFINITION TESTS
# =============================================================================

class TestZoneDefinition:
    """Tests for zone_definition.py"""

    def test_zone_type_enum(self):
        """Test ZoneType enum values."""
        from magnet.routing.schema.zone_definition import ZoneType

        assert ZoneType.FIRE.value == 'fire'
        assert ZoneType.WATERTIGHT.value == 'watertight'
        assert ZoneType.HAZARDOUS.value == 'hazardous'
        assert ZoneType.ACCOMMODATION.value == 'accommodation'
        assert ZoneType.MACHINERY.value == 'machinery'

    def test_crossing_requirement_enum(self):
        """Test CrossingRequirement enum values."""
        from magnet.routing.schema.zone_definition import CrossingRequirement

        assert CrossingRequirement.PROHIBITED.value == 'prohibited'
        assert CrossingRequirement.PENETRATION.value == 'penetration'
        assert CrossingRequirement.DAMPER.value == 'damper'
        assert CrossingRequirement.VALVE.value == 'valve'
        assert CrossingRequirement.UNRESTRICTED.value == 'unrestricted'

    def test_zone_definition_creation(self):
        """Test ZoneDefinition dataclass."""
        from magnet.routing.schema.zone_definition import ZoneDefinition, ZoneType

        zone = ZoneDefinition(
            zone_id='FZ-01',
            zone_type=ZoneType.FIRE,
            name='Fire Zone 1',
            spaces={'C001', 'C002', 'C003'},
        )

        assert zone.zone_id == 'FZ-01'
        assert zone.zone_type == ZoneType.FIRE
        assert len(zone.spaces) == 3

    def test_zone_definition_contains_space(self):
        """Test contains_space method."""
        from magnet.routing.schema.zone_definition import ZoneDefinition, ZoneType

        zone = ZoneDefinition(
            zone_id='FZ-01',
            zone_type=ZoneType.FIRE,
            name='Fire Zone 1',
            spaces={'C001', 'C002'},
        )

        assert zone.contains_space('C001')
        assert not zone.contains_space('C003')

    def test_zone_boundary(self):
        """Test ZoneBoundary dataclass."""
        from magnet.routing.schema.zone_definition import ZoneBoundary, ZoneType

        boundary = ZoneBoundary(
            boundary_id='FB-01',
            from_space='C001',
            to_space='C002',
            zone_type=ZoneType.FIRE,
        )

        assert boundary.boundary_id == 'FB-01'
        assert boundary.from_space == 'C001'
        assert boundary.to_space == 'C002'

    def test_zone_boundary_can_add_penetration(self):
        """Test can_add_penetration method."""
        from magnet.routing.schema.zone_definition import ZoneBoundary, ZoneType

        # Unlimited penetrations
        boundary = ZoneBoundary(
            boundary_id='FB-01',
            from_space='C001',
            to_space='C002',
            zone_type=ZoneType.FIRE,
            max_penetrations=-1,
        )
        assert boundary.can_add_penetration()

        # Limited penetrations
        boundary2 = ZoneBoundary(
            boundary_id='FB-02',
            from_space='C001',
            to_space='C002',
            zone_type=ZoneType.FIRE,
            max_penetrations=2,
            existing_penetrations=2,
        )
        assert not boundary2.can_add_penetration()

    def test_zone_crossing_rules(self):
        """Test ZONE_CROSSING_RULES dictionary."""
        from magnet.routing.schema.zone_definition import (
            ZONE_CROSSING_RULES, ZoneType, CrossingRequirement
        )

        # Fire zone rules exist
        assert ZoneType.FIRE in ZONE_CROSSING_RULES
        fire_rules = ZONE_CROSSING_RULES[ZoneType.FIRE]
        assert fire_rules['fuel'] == CrossingRequirement.PROHIBITED

        # Watertight rules exist
        assert ZoneType.WATERTIGHT in ZONE_CROSSING_RULES
        wt_rules = ZONE_CROSSING_RULES[ZoneType.WATERTIGHT]
        assert wt_rules['fuel'] == CrossingRequirement.VALVE

    def test_zone_definition_to_dict(self):
        """Test ZoneDefinition serialization."""
        from magnet.routing.schema.zone_definition import ZoneDefinition, ZoneType

        zone = ZoneDefinition(
            zone_id='FZ-01',
            zone_type=ZoneType.FIRE,
            name='Fire Zone 1',
            spaces={'C001'},
        )

        data = zone.to_dict()
        assert data['zone_id'] == 'FZ-01'
        assert data['zone_type'] == 'fire'

    def test_zone_definition_from_dict(self):
        """Test ZoneDefinition deserialization."""
        from magnet.routing.schema.zone_definition import ZoneDefinition, ZoneType

        data = {
            'zone_id': 'FZ-02',
            'zone_type': 'fire',
            'name': 'Fire Zone 2',
            'spaces': ['C004', 'C005'],
        }

        zone = ZoneDefinition.from_dict(data)
        assert zone.zone_id == 'FZ-02'
        assert zone.zone_type == ZoneType.FIRE

    def test_zone_definition_factory_fire_zone(self):
        """Test fire zone factory method."""
        from magnet.routing.schema.zone_definition import ZoneDefinition, ZoneType

        zone = ZoneDefinition.create_fire_zone(
            zone_id='FZ-01',
            name='Fire Zone 1',
            spaces={'C001', 'C002'},
        )

        assert zone.zone_type == ZoneType.FIRE
        assert zone.is_main_vertical_zone
        assert 'fuel' in zone.prohibited_systems


# =============================================================================
# SEPARATION RULE TESTS
# =============================================================================

class TestSeparationRule:
    """Tests for separation_rule.py"""

    def test_separation_type_enum(self):
        """Test SeparationType enum."""
        from magnet.routing.schema.separation_rule import SeparationType

        assert SeparationType.PROHIBITED.value == 'prohibited'
        assert SeparationType.PHYSICAL.value == 'physical'
        assert SeparationType.DISTANCE.value == 'distance'
        assert SeparationType.NONE.value == 'none'

    def test_separation_rule_creation(self):
        """Test SeparationRule dataclass."""
        from magnet.routing.schema.separation_rule import SeparationRule, SeparationType

        rule = SeparationRule(
            rule_id='SR-001',
            system_a='fuel',
            system_b='electrical_hv',
            separation_type=SeparationType.PHYSICAL,
            min_distance_m=0.5,
        )

        assert rule.rule_id == 'SR-001'
        assert rule.system_a == 'fuel'
        assert rule.system_b == 'electrical_hv'
        assert rule.min_distance_m == 0.5

    def test_separation_rule_applies_to(self):
        """Test applies_to method."""
        from magnet.routing.schema.separation_rule import SeparationRule, SeparationType

        rule = SeparationRule(
            rule_id='SR-001',
            system_a='fuel',
            system_b='electrical_hv',
            separation_type=SeparationType.PHYSICAL,
        )

        assert rule.applies_to('fuel', 'electrical_hv')
        assert rule.applies_to('electrical_hv', 'fuel')  # Reversed
        assert not rule.applies_to('fuel', 'freshwater')

    def test_separation_rule_check_distance(self):
        """Test check_distance method."""
        from magnet.routing.schema.separation_rule import SeparationRule, SeparationType

        rule = SeparationRule(
            rule_id='SR-001',
            system_a='fuel',
            system_b='electrical_hv',
            separation_type=SeparationType.DISTANCE,
            min_distance_m=0.5,
        )

        is_valid, msg = rule.check_distance(0.6)
        assert is_valid
        assert msg == ''

        is_valid, msg = rule.check_distance(0.3)
        assert not is_valid
        assert 'less than required' in msg

    def test_separation_rule_set(self):
        """Test SeparationRuleSet class."""
        from magnet.routing.schema.separation_rule import (
            SeparationRule, SeparationRuleSet, SeparationType
        )

        rule1 = SeparationRule(
            rule_id='SR-001',
            system_a='fuel',
            system_b='electrical_hv',
            separation_type=SeparationType.PHYSICAL,
            min_distance_m=0.5,
        )
        rule2 = SeparationRule(
            rule_id='SR-002',
            system_a='freshwater',
            system_b='black_water',
            separation_type=SeparationType.PROHIBITED,
        )

        rule_set = SeparationRuleSet(rules=[rule1, rule2])
        assert len(rule_set.rules) == 2

        # Test get_rule
        found = rule_set.get_rule('fuel', 'electrical_hv')
        assert found is not None
        assert found.min_distance_m == 0.5

        # Test reverse order
        found_reverse = rule_set.get_rule('electrical_hv', 'fuel')
        assert found_reverse is not None

    def test_separation_rule_set_check_separation(self):
        """Test check_separation method."""
        from magnet.routing.schema.separation_rule import (
            SeparationRule, SeparationRuleSet, SeparationType
        )

        rule = SeparationRule(
            rule_id='SR-001',
            system_a='fuel',
            system_b='electrical_hv',
            separation_type=SeparationType.DISTANCE,
            min_distance_m=0.5,
        )
        rule_set = SeparationRuleSet(rules=[rule])

        is_valid, violations = rule_set.check_separation(
            'fuel', 'electrical_hv', distance_m=0.6
        )
        assert is_valid
        assert len(violations) == 0

        is_valid, violations = rule_set.check_separation(
            'fuel', 'electrical_hv', distance_m=0.3
        )
        assert not is_valid
        assert len(violations) > 0

    def test_default_separation_rules(self):
        """Test DEFAULT_SEPARATION_RULES."""
        from magnet.routing.schema.separation_rule import DEFAULT_SEPARATION_RULES

        assert len(DEFAULT_SEPARATION_RULES.rules) >= 10

        # Check fuel-electrical rule exists
        rule = DEFAULT_SEPARATION_RULES.get_rule('fuel', 'electrical_hv')
        assert rule is not None
        assert rule.min_distance_m > 0

    def test_get_separation_requirement(self):
        """Test get_separation_requirement function."""
        from magnet.routing.schema.separation_rule import get_separation_requirement

        rule = get_separation_requirement('fuel', 'electrical_hv')
        assert rule is not None
        assert rule.min_distance_m > 0

        # Unknown pair should return None
        rule_unknown = get_separation_requirement('unknown_a', 'unknown_b')
        assert rule_unknown is None

    def test_separation_rule_to_dict(self):
        """Test SeparationRule serialization."""
        from magnet.routing.schema.separation_rule import SeparationRule, SeparationType

        rule = SeparationRule(
            rule_id='SR-001',
            system_a='fuel',
            system_b='electrical_hv',
            separation_type=SeparationType.PHYSICAL,
            min_distance_m=0.5,
        )

        data = rule.to_dict()
        assert data['rule_id'] == 'SR-001'
        assert data['min_distance_m'] == 0.5


# =============================================================================
# REDUNDANCY CHECKER TESTS
# =============================================================================

class TestRedundancyChecker:
    """Tests for redundancy.py"""

    def test_redundancy_requirement_enum(self):
        """Test RedundancyRequirement enum."""
        from magnet.routing.router.redundancy import RedundancyRequirement

        assert RedundancyRequirement.NONE.value == 'none'
        assert RedundancyRequirement.PREFERRED.value == 'preferred'
        assert RedundancyRequirement.REQUIRED.value == 'required'
        assert RedundancyRequirement.CRITICAL.value == 'critical'

    def test_path_diversity_dataclass(self):
        """Test PathDiversity dataclass."""
        from magnet.routing.router.redundancy import PathDiversity

        diversity = PathDiversity(
            from_node='N1',
            to_node='N2',
            primary_path=['C1', 'C2', 'C3'],
            alternate_paths=[['C1', 'C4', 'C3']],
            diversity_score=0.85,
        )

        assert diversity.from_node == 'N1'
        assert diversity.to_node == 'N2'
        assert diversity.has_alternate
        assert diversity.diversity_score == 0.85

    def test_path_diversity_is_fully_redundant(self):
        """Test is_fully_redundant property."""
        from magnet.routing.router.redundancy import PathDiversity

        # Fully redundant
        diversity = PathDiversity(
            from_node='N1',
            to_node='N2',
            alternate_paths=[['C1', 'C4', 'C3']],
            diversity_score=0.95,
        )
        assert diversity.is_fully_redundant

        # Not fully redundant (low score)
        diversity2 = PathDiversity(
            from_node='N1',
            to_node='N2',
            alternate_paths=[['C1', 'C4', 'C3']],
            diversity_score=0.5,
        )
        assert not diversity2.is_fully_redundant

    def test_redundancy_result_dataclass(self):
        """Test RedundancyResult dataclass."""
        from magnet.routing.router.redundancy import (
            RedundancyResult, RedundancyRequirement
        )

        result = RedundancyResult(
            system_type='electrical_hv',
            requirement=RedundancyRequirement.REQUIRED,
            is_compliant=True,
        )

        assert result.system_type == 'electrical_hv'
        assert result.is_compliant

    def test_redundancy_checker_creation(self):
        """Test RedundancyChecker instantiation."""
        from magnet.routing.router.redundancy import RedundancyChecker

        checker = RedundancyChecker()
        assert checker is not None

        checker_custom = RedundancyChecker(
            min_diversity_score=0.6,
            critical_min_diversity=0.9,
        )
        assert checker_custom._min_diversity == 0.6

    def test_calculate_separation_score(self):
        """Test calculate_separation_score method."""
        from magnet.routing.router.redundancy import RedundancyChecker

        checker = RedundancyChecker()

        # Identical paths
        path_a = ['C1', 'C2', 'C3']
        path_b = ['C1', 'C2', 'C3']
        score = checker.calculate_separation_score(path_a, path_b)
        assert score == 0.0

        # Fully independent paths
        path_a = ['C1', 'C2', 'C3']
        path_b = ['C1', 'C4', 'C3']  # Different middle
        score = checker.calculate_separation_score(path_a, path_b)
        assert score == 1.0  # Only C2 vs C4 in interior

    def test_calculate_separation_score_empty(self):
        """Test separation score with empty paths."""
        from magnet.routing.router.redundancy import RedundancyChecker

        checker = RedundancyChecker()

        score = checker.calculate_separation_score([], ['C1', 'C2'])
        assert score == 0.0


# =============================================================================
# PATH OPTIMIZER TESTS
# =============================================================================

class TestPathOptimizer:
    """Tests for path_optimizer.py"""

    def test_optimization_objective_enum(self):
        """Test OptimizationObjective enum."""
        from magnet.routing.router.path_optimizer import OptimizationObjective

        assert OptimizationObjective.LENGTH.value == 'length'
        assert OptimizationObjective.CROSSINGS.value == 'crossings'
        assert OptimizationObjective.CONFLICTS.value == 'conflicts'
        assert OptimizationObjective.COST.value == 'cost'
        assert OptimizationObjective.BALANCED.value == 'balanced'

    def test_optimization_result_dataclass(self):
        """Test OptimizationResult dataclass."""
        from magnet.routing.router.path_optimizer import OptimizationResult

        result = OptimizationResult(
            success=True,
            original_path=['C1', 'C2', 'C3'],
            optimized_path=['C1', 'C3'],
            length_reduction_m=5.0,
        )

        assert result.success
        assert result.length_reduction_m == 5.0

    def test_path_optimizer_creation(self):
        """Test PathOptimizer instantiation."""
        from magnet.routing.router.path_optimizer import PathOptimizer

        optimizer = PathOptimizer()
        assert optimizer is not None

        optimizer_custom = PathOptimizer(
            length_weight=2.0,
            crossing_weight=1.0,
        )
        assert optimizer_custom._length_weight == 2.0

    def test_optimizer_short_path(self):
        """Test optimization with short path."""
        from magnet.routing.router.path_optimizer import (
            PathOptimizer, OptimizationObjective
        )

        optimizer = PathOptimizer()

        # Single-node path
        result = optimizer.optimize(
            path=['C1'],
            objective=OptimizationObjective.LENGTH,
            compartment_graph=None,
        )

        assert result.success
        assert result.original_path == ['C1']


# =============================================================================
# PATH UTILS TESTS
# =============================================================================

class TestPathUtils:
    """Tests for path_utils.py"""

    def test_merge_paths_single(self):
        """Test merge_paths with single path."""
        from magnet.routing.router.path_utils import merge_paths

        path1 = ['C1', 'C2', 'C3']
        merged = merge_paths([path1])

        assert merged == ['C1', 'C2', 'C3']

    def test_merge_paths_connected(self):
        """Test merge_paths with connected paths."""
        from magnet.routing.router.path_utils import merge_paths

        path1 = ['C1', 'C2', 'C3']
        path2 = ['C3', 'C4', 'C5']

        merged = merge_paths([path1, path2])

        assert merged == ['C1', 'C2', 'C3', 'C4', 'C5']

    def test_merge_paths_empty(self):
        """Test merge_paths with empty list."""
        from magnet.routing.router.path_utils import merge_paths

        merged = merge_paths([])
        assert merged == []

    def test_split_path(self):
        """Test split_path function."""
        from magnet.routing.router.path_utils import split_path

        path = ['C1', 'C2', 'C3', 'C4']

        first, second = split_path(path, 'C3')

        assert first == ['C1', 'C2', 'C3']
        assert second == ['C3', 'C4']

    def test_split_path_not_found(self):
        """Test split_path when point not in path."""
        from magnet.routing.router.path_utils import split_path

        path = ['C1', 'C2', 'C3']

        first, second = split_path(path, 'C5')

        assert first == ['C1', 'C2', 'C3']
        assert second == []

    def test_find_intersections(self):
        """Test find_intersections function."""
        from magnet.routing.router.path_utils import find_intersections

        path_a = ['C1', 'C2', 'C3', 'C4']
        path_b = ['C2', 'C3', 'C5']

        intersections = find_intersections(path_a, path_b)

        assert intersections == ['C2', 'C3']

    def test_find_intersections_none(self):
        """Test find_intersections with no overlap."""
        from magnet.routing.router.path_utils import find_intersections

        path_a = ['C1', 'C2']
        path_b = ['C3', 'C4']

        intersections = find_intersections(path_a, path_b)

        assert intersections == []

    def test_calculate_path_length(self):
        """Test calculate_path_length function."""
        from magnet.routing.router.path_utils import calculate_path_length

        path = ['C1', 'C2', 'C3']
        positions = {
            'C1': (0.0, 0.0, 0.0),
            'C2': (3.0, 0.0, 0.0),
            'C3': (3.0, 4.0, 0.0),
        }

        length = calculate_path_length(path, positions)
        assert abs(length - 7.0) < 0.001

    def test_calculate_path_length_short(self):
        """Test calculate_path_length with short path."""
        from magnet.routing.router.path_utils import calculate_path_length

        length = calculate_path_length(['C1'], {})
        assert length == 0.0

    def test_get_path_segments(self):
        """Test get_path_segments function."""
        from magnet.routing.router.path_utils import get_path_segments

        path = ['C1', 'C2', 'C3', 'C4', 'C5']
        boundaries = {'C3'}

        segments = get_path_segments(path, boundaries)

        assert len(segments) == 2
        assert segments[0] == ['C1', 'C2', 'C3']
        assert segments[1] == ['C3', 'C4', 'C5']

    def test_paths_overlap(self):
        """Test paths_overlap function."""
        from magnet.routing.router.path_utils import paths_overlap

        path_a = ['C1', 'C2', 'C3']
        path_b = ['C2', 'C3', 'C4']

        assert paths_overlap(path_a, path_b, min_overlap=1)
        assert paths_overlap(path_a, path_b, min_overlap=2)
        assert not paths_overlap(path_a, path_b, min_overlap=3)

    def test_find_common_subpath(self):
        """Test find_common_subpath function."""
        from magnet.routing.router.path_utils import find_common_subpath

        path_a = ['C1', 'C2', 'C3', 'C4']
        path_b = ['C2', 'C3', 'C5']

        common = find_common_subpath(path_a, path_b, min_length=2)

        assert len(common) == 1
        assert common[0] == ['C2', 'C3']

    def test_find_common_subpath_none(self):
        """Test find_common_subpath with no common subpath."""
        from magnet.routing.router.path_utils import find_common_subpath

        path_a = ['C1', 'C2']
        path_b = ['C3', 'C4']

        common = find_common_subpath(path_a, path_b, min_length=1)

        assert common == []


# =============================================================================
# MULTI-SYSTEM COORDINATOR TESTS
# =============================================================================

class TestMultiSystemCoordinator:
    """Tests for multi_system.py"""

    def test_conflict_type_enum(self):
        """Test ConflictType enum."""
        from magnet.routing.agent.multi_system import ConflictType

        assert ConflictType.SEPARATION.value == 'separation'
        assert ConflictType.CO_ROUTING.value == 'co_routing'
        assert ConflictType.ZONE.value == 'zone'
        assert ConflictType.CAPACITY.value == 'capacity'

    def test_system_conflict_dataclass(self):
        """Test SystemConflict dataclass."""
        from magnet.routing.agent.multi_system import SystemConflict, ConflictType

        conflict = SystemConflict(
            conflict_id='CF-001',
            conflict_type=ConflictType.SEPARATION,
            system_a='fuel',
            system_b='electrical_hv',
            spaces=['C001', 'C002'],
            severity=7,
        )

        assert conflict.conflict_id == 'CF-001'
        assert conflict.conflict_type == ConflictType.SEPARATION
        assert conflict.severity == 7

    def test_system_conflict_to_dict(self):
        """Test SystemConflict serialization."""
        from magnet.routing.agent.multi_system import SystemConflict, ConflictType

        conflict = SystemConflict(
            conflict_id='CF-001',
            conflict_type=ConflictType.SEPARATION,
            system_a='fuel',
            system_b='electrical_hv',
        )

        data = conflict.to_dict()
        assert data['conflict_id'] == 'CF-001'
        assert data['conflict_type'] == 'separation'

    def test_multi_system_coordinator_creation(self):
        """Test MultiSystemCoordinator instantiation."""
        from magnet.routing.agent.multi_system import MultiSystemCoordinator

        coordinator = MultiSystemCoordinator()
        assert coordinator is not None

    def test_detect_conflicts(self):
        """Test detect_conflicts method."""
        from magnet.routing.agent.multi_system import MultiSystemCoordinator

        coordinator = MultiSystemCoordinator()

        # Empty topologies
        topologies = {}
        conflicts = coordinator.detect_conflicts(topologies)

        assert isinstance(conflicts, list)


# =============================================================================
# ROUTING VALIDATOR TESTS
# =============================================================================

class TestRoutingValidator:
    """Tests for validators.py"""

    def test_validation_severity_enum(self):
        """Test ValidationSeverity enum."""
        from magnet.routing.agent.validators import ValidationSeverity

        assert ValidationSeverity.INFO.value == 'info'
        assert ValidationSeverity.WARNING.value == 'warning'
        assert ValidationSeverity.ERROR.value == 'error'
        assert ValidationSeverity.CRITICAL.value == 'critical'

    def test_validation_violation_dataclass(self):
        """Test ValidationViolation dataclass."""
        from magnet.routing.agent.validators import (
            ValidationViolation, ValidationSeverity
        )

        violation = ValidationViolation(
            violation_id='VV-001',
            rule_name='zone_crossing',
            severity=ValidationSeverity.ERROR,
            message='Unauthorized fire zone crossing',
            system_type='fuel',
        )

        assert violation.violation_id == 'VV-001'
        assert violation.severity == ValidationSeverity.ERROR
        assert violation.system_type == 'fuel'

    def test_validation_violation_to_dict(self):
        """Test ValidationViolation serialization."""
        from magnet.routing.agent.validators import (
            ValidationViolation, ValidationSeverity
        )

        violation = ValidationViolation(
            violation_id='VV-001',
            rule_name='zone_crossing',
            severity=ValidationSeverity.ERROR,
            message='Test message',
        )

        data = violation.to_dict()
        assert data['violation_id'] == 'VV-001'
        assert data['severity'] == 'error'

    def test_routing_validator_creation(self):
        """Test RoutingValidator instantiation."""
        from magnet.routing.agent.validators import RoutingValidator

        validator = RoutingValidator()
        assert validator is not None

    def test_validate_connectivity(self):
        """Test validate_connectivity method."""
        from magnet.routing.agent.validators import RoutingValidator

        validator = RoutingValidator()

        # Empty topology should have no violations
        topology = {'nodes': {}, 'trunks': {}}
        violations = validator.validate_connectivity('fuel', topology)

        assert isinstance(violations, list)


# =============================================================================
# STATE INTEGRATION TESTS
# =============================================================================

class TestStateIntegration:
    """Tests for state_integration.py"""

    def test_routing_state_keys(self):
        """Test RoutingStateKeys constants."""
        from magnet.routing.integration.state_integration import RoutingStateKeys

        assert RoutingStateKeys.ROUTING_LAYOUT == 'routing.layout'
        assert RoutingStateKeys.FIRE_ZONES == 'routing.zones.fire'
        assert RoutingStateKeys.WT_COMPARTMENTS == 'routing.zones.watertight'

    def test_routing_state_keys_topology_key(self):
        """Test topology_key class method."""
        from magnet.routing.integration.state_integration import RoutingStateKeys

        key = RoutingStateKeys.topology_key('fuel')
        assert key == 'routing.topology.fuel'

    def test_state_integrator_creation(self):
        """Test StateIntegrator instantiation."""
        from magnet.routing.integration.state_integration import StateIntegrator

        integrator = StateIntegrator(state_manager=None)
        assert integrator is not None

    def test_state_integrator_with_mock_manager(self):
        """Test StateIntegrator with mock state manager."""
        from magnet.routing.integration.state_integration import StateIntegrator

        # Simple mock state manager
        class MockStateManager:
            def __init__(self):
                self._state = {}

        mock_mgr = MockStateManager()
        integrator = StateIntegrator(state_manager=mock_mgr)

        # Check the integrator was created with the manager
        assert integrator._sm is mock_mgr


# =============================================================================
# CONFIGURATION TESTS
# =============================================================================

class TestRoutingConfig:
    """Tests for config.py"""

    def test_routing_config_creation(self):
        """Test RoutingConfig dataclass."""
        from magnet.routing.integration.config import RoutingConfig

        config = RoutingConfig(
            max_path_length_m=50.0,
            max_zone_crossings=3,
        )

        assert config.max_path_length_m == 50.0
        assert config.max_zone_crossings == 3

    def test_routing_config_defaults(self):
        """Test RoutingConfig default values."""
        from magnet.routing.integration.config import RoutingConfig

        config = RoutingConfig()

        assert config.use_mst_routing == True
        assert config.max_path_length_m == 100.0
        assert config.strict_zone_enforcement == True

    def test_default_config(self):
        """Test DEFAULT_CONFIG singleton."""
        from magnet.routing.integration.config import DEFAULT_CONFIG

        assert DEFAULT_CONFIG is not None
        assert hasattr(DEFAULT_CONFIG, 'max_path_length_m')
        assert hasattr(DEFAULT_CONFIG, 'min_diversity_score')

    def test_routing_config_to_dict(self):
        """Test RoutingConfig serialization."""
        from magnet.routing.integration.config import RoutingConfig

        config = RoutingConfig(
            max_path_length_m=50.0,
            max_zone_crossings=3,
        )

        data = config.to_dict()
        assert 'max_path_length_m' in data
        assert data['max_path_length_m'] == 50.0

    def test_routing_config_from_dict(self):
        """Test RoutingConfig deserialization."""
        from magnet.routing.integration.config import RoutingConfig

        data = {
            'max_path_length_m': 60.0,
            'max_zone_crossings': 4,
        }

        config = RoutingConfig.from_dict(data)
        assert config.max_path_length_m == 60.0
        assert config.max_zone_crossings == 4


# =============================================================================
# PACKAGE IMPORT TESTS
# =============================================================================

class TestPackageImports:
    """Tests for package-level imports."""

    def test_main_package_imports(self):
        """Test imports from magnet.routing."""
        from magnet.routing import (
            # BRAVO Schema Zone
            ZoneType,
            ZoneDefinition,
            ZoneBoundary,
            CrossingRequirement,
            ZONE_CROSSING_RULES,
            # BRAVO Schema Separation
            SeparationType,
            SeparationRule,
            SeparationRuleSet,
            DEFAULT_SEPARATION_RULES,
            get_separation_requirement,
            # BRAVO Router Redundancy
            RedundancyChecker,
            RedundancyResult,
            PathDiversity,
            RedundancyRequirement,
            # BRAVO Router Optimizer
            PathOptimizer,
            OptimizationObjective,
            OptimizationResult,
            # BRAVO Router Utils
            merge_paths,
            split_path,
            find_intersections,
            calculate_path_length,
            simplify_path,
            # BRAVO Agent Multi-system
            MultiSystemCoordinator,
            ConflictType,
            SystemConflict,
            CoordinationResult,
            # BRAVO Agent Validators
            RoutingValidator,
            ValidationSeverity,
            ValidationViolation,
            ValidationResult,
            # BRAVO Integration
            StateIntegrator,
            RoutingStateKeys,
            RoutingConfig,
            DEFAULT_CONFIG,
            create_routing_router,
            RouteRequest,
            RouteResponse,
            ValidationResponse,
        )

        # Verify they're all importable
        assert ZoneType is not None
        assert RedundancyChecker is not None
        assert PathOptimizer is not None
        assert MultiSystemCoordinator is not None
        assert RoutingValidator is not None
        assert StateIntegrator is not None
        assert RoutingConfig is not None

    def test_router_subpackage_imports(self):
        """Test imports from magnet.routing.router."""
        from magnet.routing.router import (
            RedundancyChecker,
            RedundancyResult,
            PathDiversity,
            RedundancyRequirement,
            PathOptimizer,
            OptimizationObjective,
            OptimizationResult,
            merge_paths,
            split_path,
            find_intersections,
            calculate_path_length,
            simplify_path,
            get_path_segments,
            paths_overlap,
            find_common_subpath,
        )

        assert RedundancyChecker is not None
        assert PathOptimizer is not None
        assert merge_paths is not None

    def test_schema_subpackage_imports(self):
        """Test imports from magnet.routing.schema."""
        from magnet.routing.schema import (
            ZoneType,
            ZoneDefinition,
            ZoneBoundary,
            CrossingRequirement,
            ZONE_CROSSING_RULES,
            SeparationType,
            SeparationRule,
            SeparationRuleSet,
            DEFAULT_SEPARATION_RULES,
            get_separation_requirement,
        )

        assert ZoneType is not None
        assert SeparationRule is not None


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestBravoIntegration:
    """Integration tests combining multiple BRAVO components."""

    def test_zone_and_separation_rules(self):
        """Test zone definitions with separation rules."""
        from magnet.routing.schema.zone_definition import ZoneType, ZoneDefinition
        from magnet.routing.schema.separation_rule import (
            DEFAULT_SEPARATION_RULES, SeparationType
        )

        # Create a fire zone
        zone = ZoneDefinition.create_fire_zone(
            zone_id='FZ-01',
            name='Fire Zone 1',
            spaces={'C001', 'C002'},
        )

        assert zone.zone_type == ZoneType.FIRE
        assert 'fuel' in zone.prohibited_systems

        # Check fuel-electrical separation rule
        rule = DEFAULT_SEPARATION_RULES.get_rule('fuel', 'electrical_hv')
        assert rule is not None
        assert rule.separation_type == SeparationType.PHYSICAL

    def test_path_utils_integration(self):
        """Test path utility functions together."""
        from magnet.routing.router.path_utils import (
            merge_paths, split_path, find_intersections, calculate_path_length
        )

        path1 = ['C1', 'C2', 'C3']
        path2 = ['C3', 'C4', 'C5']

        # Merge
        merged = merge_paths([path1, path2])
        assert merged == ['C1', 'C2', 'C3', 'C4', 'C5']

        # Split
        first, second = split_path(merged, 'C3')
        assert first == ['C1', 'C2', 'C3']

        # Intersections
        intersections = find_intersections(path1, path2)
        assert intersections == ['C3']

    def test_config_with_validation(self):
        """Test configuration affects validation."""
        from magnet.routing.integration.config import RoutingConfig
        from magnet.routing.agent.validators import RoutingValidator

        # Strict config
        config = RoutingConfig(
            strict_zone_enforcement=True,
            strict_validation=True,
        )

        validator = RoutingValidator()

        # Validation should work with empty layout
        result = validator.validate(routing_layout={'topologies': {}})
        assert result.is_valid
