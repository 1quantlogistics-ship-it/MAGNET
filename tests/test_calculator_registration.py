"""
Tests for calculator registry initialization.

Verifies that all calculators are properly registered with CascadeExecutor.
"""

import pytest
from magnet.dependencies.cascade import CalculatorRegistry
from magnet.dependencies.calculator_registry_init import (
    register_all_calculators,
    create_registry_and_register,
)


def test_register_all_calculators():
    """Test that register_all_calculators registers calculators."""
    registry = CalculatorRegistry()
    register_all_calculators(registry)
    
    # Should have registered geometry calculators
    geometry_params = registry.list_calculators()
    assert len(geometry_params) > 0, "Should register at least one calculator"
    
    # Check for key geometry parameters
    assert "hull.geometry" in geometry_params
    assert "design_program" in geometry_params


def test_create_registry_and_register():
    """Test convenience function creates and registers."""
    registry = create_registry_and_register()
    
    assert isinstance(registry, CalculatorRegistry)
    assert len(registry.list_calculators()) > 0


def test_geometry_calculators_registered():
    """Test that NEW geometry calculators are registered."""
    registry = CalculatorRegistry()
    register_all_calculators(registry)
    
    # NEW path calculators
    expected_geometry = [
        "hull.geometry",
        "resources.geometry.section",
        "resources.geometry.body",
        "resources.geometry.surface",
        "design_program",
    ]
    
    registered = registry.list_calculators()
    for param in expected_geometry:
        assert param in registered, f"Expected {param} to be registered"


def test_hydrostatics_calculators_registered():
    """Test that hydrostatics calculators are registered."""
    registry = CalculatorRegistry()
    register_all_calculators(registry)
    
    expected_hydro = [
        "hull.displacement_m3",
        "stability.gm_m",
        "stability.bm_m",
        "stability.kb_m",
    ]
    
    registered = registry.list_calculators()
    for param in expected_hydro:
        assert param in registered, f"Expected {param} to be registered"


def test_calculator_callable():
    """Test that registered calculators are callable."""
    registry = create_registry_and_register()
    
    calculator = registry.get_calculator("hull.geometry")
    assert calculator is not None
    assert callable(calculator)


def test_calculator_metadata():
    """Test that calculators have proper metadata."""
    registry = create_registry_and_register()
    
    # Geometry calculators should have estimated time
    time_ms = registry.get_estimated_time("hull.geometry")
    assert time_ms > 0, "Should have estimated execution time"
    
    # Geometry compilation requires lock
    # (This test just verifies metadata exists, not the actual locking)
    assert registry.has_calculator("hull.geometry")


def test_no_enumeration_in_registration():
    """
    INVARIANT: Calculator registration must not introduce enumeration.
    
    Verify that the registration module itself doesn't use hull_type in code.
    
    Note: Comments mentioning hull_type are acceptable for documentation.
    """
    import inspect
    from magnet.dependencies import calculator_registry_init
    
    source = inspect.getsource(calculator_registry_init)
    
    # Remove comments before checking
    lines = source.split('\n')
    code_lines = [line.split('#')[0] for line in lines]
    code_only = '\n'.join(code_lines)
    
    forbidden = ["HullFamily", "HullType"]
    for term in forbidden:
        assert term not in code_only, f"Registration module code must not contain '{term}'"
    
    # hull_type is allowed in comments but not in executable code
    # Check it's not used as a variable, parameter, or dictionary key
    assert "hull_type=" not in code_only
    assert '"hull_type"' not in code_only
    assert "'hull_type'" not in code_only


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

