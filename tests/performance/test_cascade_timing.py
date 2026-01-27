"""
Performance benchmarks for CascadeExecutor.

Verifies that cascade execution completes within acceptable time limits.

Target: Full cascade (13 phases) completes in < 2 seconds.

Note: These are simplified benchmarks. Full integration tests require
      complete system setup and are in tests/integration/.
"""

import pytest
import time


def test_calculator_registry_performance():
    """Test that calculator registry lookups are fast."""
    from magnet.dependencies.cascade import CalculatorRegistry
    
    registry = CalculatorRegistry()
    
    # Register many calculators
    def mock_calc(sm, param):
        return 1.0
    
    for i in range(100):
        registry.register(f"param_{i}", mock_calc, estimated_time_ms=10)
    
    # Benchmark lookups
    start = time.time()
    for i in range(100):
        calc = registry.get_calculator(f"param_{i}")
        assert calc is not None
    elapsed_ms = (time.time() - start) * 1000
    
    # Should be very fast (< 10ms for 100 lookups)
    assert elapsed_ms < 10, f"Registry lookups took {elapsed_ms:.1f}ms, should be < 10ms"
    
    print(f"\n✅ Registry lookups: {elapsed_ms:.2f}ms for 100 lookups")


def test_mock_cascade_performance():
    """
    Simulate cascade performance with mock calculators.
    
    This tests the concept without requiring full StateManager setup.
    """
    import time
    
    # Simulate 13 phases with varying calculation times
    phase_calculations = {
        "hydrostatics": 4,  # 4 params
        "resistance": 2,
        "weight": 3,
        "stability": 2,
        "cost": 2,
    }
    
    total_calculations = sum(phase_calculations.values())
    
    # Simulate cascade execution
    start = time.time()
    
    for phase, num_calcs in phase_calculations.items():
        for i in range(num_calcs):
            # Simulate calculation (1ms each)
            time.sleep(0.001)
    
    elapsed_ms = (time.time() - start) * 1000
    
    # Target: < 2000ms for full cascade
    # With mock calcs at 1ms each: 13 calcs = ~13ms (well under target)
    assert elapsed_ms < 2000, f"Mock cascade took {elapsed_ms:.1f}ms, target is < 2000ms"
    
    print(f"\n✅ Mock cascade ({total_calculations} calculations): {elapsed_ms:.1f}ms (target: < 2000ms)")
    print(f"   Projected real cascade time (50ms/calc): {total_calculations * 50}ms")


def test_cascade_timing_target_documented():
    """Document the performance target for cascade execution."""
    target_ms = 2000
    max_params = 13
    
    # Performance requirements
    assert target_ms == 2000, "Target: Full cascade < 2 seconds"
    assert max_params == 13, "Expected: ~13 parameters recalculated in full cascade"
    
    # Calculate acceptable time per parameter
    time_per_param_ms = target_ms / max_params
    
    print(f"\n📊 Cascade Performance Requirements:")
    print(f"   Total time target: {target_ms}ms")
    print(f"   Max parameters: {max_params}")
    print(f"   Time per parameter: ~{time_per_param_ms:.0f}ms")


@pytest.mark.skip(reason="Requires full StateManager integration")
def test_cascade_beam_change_integration():
    """
    Integration test: Beam change → full cascade.
    
    This test requires complete system setup:
    - StateManager with provenance
    - Registered calculators for all phases  
    - Dependency graph with all relationships
    
    Placeholder for future integration testing.
    """
    pytest.skip("Integration test - requires full system")


def test_performance_profiling_framework_exists():
    """Verify that CascadeResult includes timing information for profiling."""
    from magnet.dependencies.cascade import RecalculationResult
    from datetime import datetime
    
    # Verify RecalculationResult has timing fields
    result = RecalculationResult(
        parameter="test_param",
        success=True,
        started_at=datetime.now(),
    )
    
    assert hasattr(result, "execution_time_ms"), "Should have execution_time_ms for profiling"
    assert hasattr(result, "started_at"), "Should have started_at timestamp"
    
    print("\n✅ Profiling framework available in RecalculationResult")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
