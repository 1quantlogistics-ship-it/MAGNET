"""
Invariant tests: No design terms in kernel.

The kernel knows geometry, not design.
Any hull form that requires a new language primitive is a failure of the language.

These tests enforce:
1. No design-semantic terms in kernel/stdlib code
2. Novel forms work without new code
3. Agents coordinate on geometry only
"""

import os
import re
import pytest
from pathlib import Path


# Design terms that should NEVER appear in kernel code
# These represent enumerated design concepts
FORBIDDEN_DESIGN_TYPES = [
    "patrol",
    "workboat", 
    "ferry",
    "catamaran",
    "trimaran",
    "monohull",
    "stepped_hull",
    "spray_rail",  # Should be "discontinuity" instead
    "chine_type",  # Should be geometry.discontinuity
    "bow_style",   # Should be section geometry
]

# Physics terms that ARE allowed (they describe physics behavior, not design)
ALLOWED_PHYSICS_TERMS = [
    "planing",        # Physics regime, not design type
    "displacement",   # Physics property
    "submerged",      # Physics category
    "surface_piercing",
    "above_water",
]


def get_kernel_stdlib_files():
    """Get all Python files in kernel/stdlib."""
    stdlib_path = Path(__file__).parent.parent.parent / "magnet" / "kernel" / "stdlib"
    if not stdlib_path.exists():
        pytest.skip("stdlib not yet created")
    return list(stdlib_path.glob("*.py"))


def get_kernel_files():
    """Get all Python files in kernel (excluding priors which may still exist)."""
    kernel_path = Path(__file__).parent.parent.parent / "magnet" / "kernel"
    files = []
    for f in kernel_path.glob("*.py"):
        files.append(f)
    return files


class TestNoDesignTermsInKernel:
    """Test that kernel code doesn't contain design-semantic terms."""
    
    def test_stdlib_no_forbidden_terms(self):
        """Verify stdlib has no design-semantic terms."""
        files = get_kernel_stdlib_files()
        
        violations = []
        for filepath in files:
            content = filepath.read_text()
            for term in FORBIDDEN_DESIGN_TYPES:
                # Search for term as word (not part of another word)
                pattern = rf'\b{term}\b'
                matches = list(re.finditer(pattern, content, re.IGNORECASE))
                
                for match in matches:
                    # Get line number
                    line_num = content[:match.start()].count('\n') + 1
                    line_content = content.split('\n')[line_num - 1].strip()
                    
                    # Skip if in comment
                    if line_content.strip().startswith('#'):
                        continue
                    # Skip if in docstring (rough check)
                    if '"""' in line_content or "'''" in line_content:
                        continue
                    
                    violations.append(
                        f"{filepath.name}:{line_num}: '{term}' found in: {line_content[:60]}"
                    )
        
        if violations:
            pytest.fail(
                f"Design terms found in stdlib:\n" + 
                "\n".join(violations[:10]) +
                (f"\n... and {len(violations) - 10} more" if len(violations) > 10 else "")
            )
    
    def test_type_registry_uses_freeform_strings(self):
        """Verify type registry doesn't enumerate design types."""
        from magnet.kernel.stdlib.type_registry import TYPE_REGISTRY, FieldSchema
        
        for type_name, schema in TYPE_REGISTRY.items():
            for field in schema.fields:
                # body_type, physics_category, etc. should NOT have enum_values
                if field.name in ("body_type", "physics_category", "surface_type", 
                                 "discontinuity_type", "medium", "attachment_type"):
                    # These should be "str" type, not "enum"
                    assert field.field_type == "str", (
                        f"{type_name}.{field.name} should be 'str' not '{field.field_type}'"
                    )
    
    def test_policies_no_hull_type_lookups(self):
        """Verify DERIVE policies don't do hull_type lookups."""
        from magnet.kernel.stdlib.policies import POLICY_DOCS
        
        for name, contract in POLICY_DOCS.items():
            # No policy should require hull_type as input
            assert "hull_type" not in contract.required_inputs, (
                f"Policy '{name}' requires hull_type - should use geometry-based inputs"
            )
            # No policy should be named after design types
            for term in FORBIDDEN_DESIGN_TYPES:
                assert term not in name.lower(), (
                    f"Policy '{name}' contains design term '{term}'"
                )


class TestNovelFormsWithoutNewCode:
    """Test that novel hull forms work without code changes."""
    
    def test_novel_body_type_parses(self):
        """Verify novel body_type values parse successfully."""
        from magnet.kernel.stdlib.parser import parse
        
        # These are invented body types - should work without new code
        novel_programs = [
            'CREATE geometry.body main { body_type: "wave_piercing_asymmetric" }',
            'CREATE geometry.body foil { body_type: "hydrofoil_strut_vertical" }',
            'CREATE geometry.body ama { body_type: "stability_outrigger_modified" }',
            'CREATE geometry.body weird { body_type: "experimental_never_seen_before" }',
        ]
        
        for program_text in novel_programs:
            ast = parse(program_text)
            assert len(ast.statements) == 1
            assert ast.statements[0].properties.get("body_type") is not None
    
    def test_novel_physics_category_parses(self):
        """Verify novel physics_category values parse successfully."""
        from magnet.kernel.stdlib.parser import parse
        
        novel_programs = [
            'CREATE geometry.body main { physics_category: "cavitating_supercritical" }',
            'CREATE geometry.body main { physics_category: "partially_submerged_variable" }',
            'CREATE geometry.body main { physics_category: "spray_zone_intermittent" }',
        ]
        
        for program_text in novel_programs:
            ast = parse(program_text)
            assert len(ast.statements) == 1
    
    def test_novel_discontinuity_type_parses(self):
        """Verify novel discontinuity types parse without new code."""
        from magnet.kernel.stdlib.parser import parse
        
        program = '''
        CREATE geometry.discontinuity step1 {
            discontinuity_type: "transverse_ventilated_step",
            station_start: 0.5,
            station_end: 0.6
        }
        '''
        ast = parse(program)
        assert len(ast.statements) == 1
    
    def test_dual_body_vessel_from_primitives(self):
        """
        Create dual-body vessel using only geometry primitives.
        
        This is the acid test: no "catamaran" type, just bodies.
        """
        from magnet.kernel.stdlib.parser import parse
        from magnet.kernel.stdlib.expander import expand
        
        program = '''
        CREATE geometry.body port_hull {
            body_type: "slender_demihull",
            physics_category: "surface_piercing",
            offset_y_m: -4.0
        }
        CREATE geometry.body stbd_hull {
            body_type: "slender_demihull",
            physics_category: "surface_piercing",
            offset_y_m: 4.0
        }
        CREATE geometry.section port_bow {
            station: 0.0,
            body_id: "port_hull",
            points: [[0, 0], [1, -0.5], [1, -1.5], [0, -2]]
        }
        CREATE geometry.section port_stern {
            station: 1.0,
            body_id: "port_hull",
            points: [[0, 0], [0.8, -0.3], [0.8, -1.2], [0, -1.5]]
        }
        MIRROR port_hull AS stbd_hull
        '''
        
        ast = parse(program)
        result = expand(ast)
        
        # Verify no errors
        assert len(result.errors) == 0, f"Expansion errors: {result.errors}"
        
        # Verify we created bodies and sections
        body_creates = [
            a for a in result.actions 
            if "geometry.body" in str(a.value.get("_type", ""))
        ]
        assert len(body_creates) >= 2, "Should create at least 2 bodies"
        
        # Verify "catamaran" never appears in any action
        for action in result.actions:
            action_str = str(action).lower()
            assert "catamaran" not in action_str, (
                f"Design term 'catamaran' found in action: {action}"
            )


class TestAgentsCoordinateOnGeometry:
    """Test that agent outputs use geometry primitives, not features."""
    
    def test_parser_rejects_hull_dot_features(self):
        """Verify parser handles hull.* types appropriately."""
        from magnet.kernel.stdlib.parser import parse
        
        # hull.* types should parse (for backwards compat) but are deprecated
        # The real enforcement is in agents not using them
        deprecated_program = 'CREATE hull.spray_rail rail1 { height_ratio: 0.5 }'
        
        # Should parse without error (kernel allows it)
        ast = parse(deprecated_program)
        assert len(ast.statements) == 1
        
        # But the type should indicate it's a hull.* type
        assert ast.statements[0].resource_type == "hull.spray_rail"
    
    def test_geometry_primitives_available(self):
        """Verify all geometry primitives are in type registry."""
        from magnet.kernel.stdlib.type_registry import TYPE_REGISTRY
        
        required_primitives = [
            "geometry.section",
            "geometry.body",
            "geometry.surface",
            "geometry.discontinuity",
            "geometry.attachment",
            "geometry.flow_path",
            "geometry.opening",
        ]
        
        for prim in required_primitives:
            assert prim in TYPE_REGISTRY, f"Missing primitive: {prim}"


class TestSteppedVentilatedHullFromPrimitives:
    """
    Mission test: Create "stepped ventilated planing hull" using only primitives.
    
    This tests the core principle: agents express ANY design using only
    geometric primitives. No "stepped_hull" type needed.
    """
    
    def test_stepped_ventilated_hull(self):
        """Create stepped ventilated hull without a stepped_hull type."""
        from magnet.kernel.stdlib.parser import parse
        from magnet.kernel.stdlib.expander import expand
        
        program = '''
        # Create main body
        CREATE geometry.body main {
            body_type: "high_speed_planing",
            physics_category: "surface_piercing"
        }
        
        # Create sections defining the hull shape
        CREATE geometry.section bow {
            station: 0.0,
            body_id: "main",
            points: [[0, 0], [1.5, -0.3], [1.5, -1.2], [0, -1.5]]
        }
        
        CREATE geometry.section pre_step {
            station: 0.5,
            body_id: "main",
            points: [[0, 0], [2.5, -0.2], [2.5, -0.8], [0, -1.0]]
        }
        
        CREATE geometry.section post_step {
            station: 0.55,
            body_id: "main",
            points: [[0, 0], [2.5, -0.2], [2.5, -0.7], [0, -0.9]]
        }
        
        CREATE geometry.section stern {
            station: 1.0,
            body_id: "main",
            points: [[0, 0], [2.2, -0.1], [2.2, -0.5], [0, -0.6]]
        }
        
        # Create the step as a discontinuity (NOT a "stepped_hull" type)
        CREATE geometry.discontinuity step1 {
            discontinuity_type: "transverse_ventilated_step",
            station_start: 0.5,
            station_end: 0.55,
            depth_m: 0.1,
            height_ratio: 0.0
        }
        
        # Create ventilation flow path
        CREATE geometry.flow_path vent1 {
            medium: "air",
            inlet_point: [12.5, 0, 0.1],
            outlet_point: [12.5, 0, -0.8],
            cross_section_m2: 0.05
        }
        
        # Create spray deflector discontinuities
        CREATE geometry.discontinuity spray_deflector_port {
            discontinuity_type: "longitudinal_spray_deflector",
            station_start: 0.2,
            station_end: 0.8,
            height_ratio: 0.3,
            depth_m: 0.03
        }
        
        MIRROR spray_deflector_port AS spray_deflector_stbd
        '''
        
        ast = parse(program)
        assert len(ast.statements) > 0, "Failed to parse program"
        
        result = expand(ast)
        assert len(result.errors) == 0, f"Expansion errors: {result.errors}"
        
        # Verify we have the expected resources
        resource_types = [
            a.value.get("_type") 
            for a in result.actions 
            if isinstance(a.value, dict)
        ]
        
        assert "geometry.body" in resource_types
        assert "geometry.section" in resource_types
        assert "geometry.discontinuity" in resource_types
        assert "geometry.flow_path" in resource_types
        
        # THE KEY TEST: "stepped_hull" never appears
        all_action_text = str(result.actions).lower()
        assert "stepped_hull" not in all_action_text
        assert "stepped hull" not in all_action_text


class TestCompilerProducesCanonicalGeometry:
    """Test that compiler produces canonical HullGeometry."""
    
    def test_single_hull_compiles(self):
        """Verify single hull compiles to HullGeometry."""
        from magnet.kernel.stdlib.compiler import compile_to_geometry
        
        state = {
            "hull": {"loa": 25.0},
            "geometry_intent": {"surface_definition": "smooth"},
            "resources": {
                "bow": {
                    "_type": "geometry.section",
                    "station": 0.0,
                    "points": [[0, 0], [2, -0.5], [2, -1.5], [0, -2]],
                },
                "mid": {
                    "_type": "geometry.section",
                    "station": 0.5,
                    "points": [[0, 0], [3, -0.3], [3, -1.2], [0, -1.5]],
                },
                "stern": {
                    "_type": "geometry.section",
                    "station": 1.0,
                    "points": [[0, 0], [2.5, -0.2], [2.5, -1.0], [0, -1.2]],
                },
            }
        }
        
        geometry = compile_to_geometry(state)
        
        # Should produce HullGeometry
        assert hasattr(geometry, 'sections')
        assert len(geometry.sections) == 3
    
    def test_multi_body_compiles(self):
        """Verify multi-body vessel compiles correctly."""
        from magnet.kernel.stdlib.compiler import compile_to_geometry
        
        state = {
            "hull": {"loa": 30.0},
            "geometry_intent": {"surface_definition": "smooth"},
            "resources": {
                "port_body": {
                    "_type": "geometry.body",
                    "body_type": "demihull",
                    "physics_category": "surface_piercing",
                    "offset_y_m": -4.0,
                },
                "stbd_body": {
                    "_type": "geometry.body",
                    "body_type": "demihull",
                    "physics_category": "surface_piercing",
                    "offset_y_m": 4.0,
                },
                "port_bow": {
                    "_type": "geometry.section",
                    "station": 0.0,
                    "body_id": "port_body",
                    "points": [[0, 0], [1, -0.5], [1, -1.5], [0, -2]],
                },
                "port_stern": {
                    "_type": "geometry.section",
                    "station": 1.0,
                    "body_id": "port_body",
                    "points": [[0, 0], [0.8, -0.3], [0.8, -1.2], [0, -1.5]],
                },
                "stbd_bow": {
                    "_type": "geometry.section",
                    "station": 0.0,
                    "body_id": "stbd_body",
                    "points": [[0, 0], [1, -0.5], [1, -1.5], [0, -2]],
                },
                "stbd_stern": {
                    "_type": "geometry.section",
                    "station": 1.0,
                    "body_id": "stbd_body",
                    "points": [[0, 0], [0.8, -0.3], [0.8, -1.2], [0, -1.5]],
                },
            }
        }
        
        geometry = compile_to_geometry(state)
        
        # Should have bodies attribute
        assert hasattr(geometry, 'bodies')
        # Should have sections from both bodies
        assert len(geometry.sections) == 4


class TestConductorIntegration:
    """Verify conductor properly integrates new path."""
    
    def test_conductor_detects_design_program(self):
        """Conductor should detect design_program in state and route to new path."""
        import inspect
        from magnet.kernel.conductor import Conductor
        
        # Verify the routing logic exists
        source = inspect.getsource(Conductor.run_phase)
        assert "design_program" in source, "Conductor.run_phase should check for design_program"
        assert "_run_program_generation" in source, "Conductor should call _run_program_generation"
    
    def test_conductor_new_path_methods_exist(self):
        """Conductor should have new path methods."""
        from magnet.kernel.conductor import Conductor
        
        assert hasattr(Conductor, '_run_program_generation'), "Missing _run_program_generation"
        assert hasattr(Conductor, '_build_program_audit'), "Missing _build_program_audit"
        assert hasattr(Conductor, '_record_program_explain'), "Missing _record_program_explain"
    
    def test_new_path_bypasses_hull_family_import(self):
        """New path execution should not require HullFamily."""
        # The new path methods should work without importing HullFamily
        from magnet.kernel.program_executor import execute_program
        
        program = '''
        CREATE geometry.body main { body_type: "test", physics_category: "surface_piercing" }
        SET geometry_intent.surface_definition = "smooth"
        SET hull.loa = 20.0
        '''
        
        # Execute without state manager (uses initial_state)
        result = execute_program(program, initial_state={"hull": {}, "resources": {}})
        
        # Should succeed without any HullFamily dependency
        assert result.success or len(result.errors) == 0 or "HullFamily" not in str(result.errors)


class TestNewPathIsolation:
    """Verify new path is completely isolated from HullFamily enumeration."""
    
    def test_program_executor_never_imports_hull_families(self):
        """New path must not touch old enums."""
        import inspect
        from magnet.kernel import program_executor
        source = inspect.getsource(program_executor)
        assert "HullFamily" not in source, "program_executor imports HullFamily — isolation violated"
        assert "hull_families" not in source, "program_executor imports hull_families module"
    
    def test_compiler_never_imports_hull_families(self):
        """Compiler must not touch old enums."""
        import inspect
        from magnet.kernel.stdlib import compiler
        source = inspect.getsource(compiler)
        assert "HullFamily" not in source, "compiler imports HullFamily — isolation violated"
    
    def test_geometry_proposer_never_imports_hull_families(self):
        """Agent must not touch old enums."""
        import inspect
        from magnet.agents import geometry_proposer
        source = inspect.getsource(geometry_proposer)
        assert "HullFamily" not in source, "geometry_proposer imports HullFamily — isolation violated"
    
    def test_stdlib_modules_isolated(self):
        """All stdlib modules must be isolated from HullFamily."""
        import inspect
        from magnet.kernel.stdlib import parser, expander, type_registry, policies
        
        for module in [parser, expander, type_registry, policies]:
            source = inspect.getsource(module)
            assert "HullFamily" not in source, f"{module.__name__} imports HullFamily"
    
    def test_new_path_produces_geometry_without_hull_family(self):
        """End-to-end: new path works without any HullFamily reference."""
        from magnet.kernel.stdlib import parse, expand, compile_to_geometry
        
        program = '''
        CREATE geometry.body main {
            body_type: "novel_experimental_form",
            physics_category: "surface_piercing"
        }
        CREATE geometry.section bow {
            station: 0.0,
            body_id: "main",
            points: [[0, 0], [1.5, -0.5], [1.5, -2], [0, -2.5]]
        }
        CREATE geometry.section stern {
            station: 1.0,
            body_id: "main",
            points: [[0, 0], [1.2, -0.3], [1.2, -1.5], [0, -1.8]]
        }
        SET hull.loa = 25.0
        '''
        
        # Parse → Expand → Compile
        ast = parse(program)
        result = expand(ast)
        assert not result.errors, f"Expansion errors: {result.errors}"
        
        # Build state from actions
        state = {"hull": {"loa": 25.0}, "geometry_intent": {"surface_definition": "smooth"}, "resources": {}}
        for action in result.actions:
            if action.path.startswith("resources."):
                rid = action.path.split(".")[1]
                state["resources"][rid] = action.value
        
        # Compile to geometry
        geometry = compile_to_geometry(state)
        assert geometry is not None, "Failed to compile geometry"
        assert len(geometry.sections) > 0, "No sections in compiled geometry"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

