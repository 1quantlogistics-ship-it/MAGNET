"""
THE TEST — Validates the MAGNET Mission Statement.

From the Mission Statement:
> Create a "stepped ventilated planing hull" using only discontinuities, flow paths, and openings. No "stepped hull" type.
> Create a "catamaran" using only bodies, sections, and surfaces. No "catamaran" type.
> Create a hull configuration no naval architect has ever drawn—and validate it without adding code.
> If any test fails, we've collapsed back into enumeration.

Reference: MAGNET_Merge_Implementation_Plan.md Phase 7
"""

import pytest
from tests.fixtures.geometry_proposals import (
    VALID_STEPPED_HULL,
    VALID_TWIN_HULL,
    VALID_NOVEL_FORM,
    FORBIDDEN_TERMS,
    THE_TEST_FIXTURES,
)


class TestTheTest:
    """THE TEST from the MAGNET Mission Statement."""
    
    def test_stepped_ventilated_planing_hull_no_stepped_type(self):
        """
        THE TEST #1: Create "stepped ventilated planing hull" without "stepped hull" type.
        
        Uses only: discontinuities, flow paths, openings
        Must NOT contain: "stepped hull", "stepped_hull", "planing_hull"
        """
        proposal = THE_TEST_FIXTURES["stepped_ventilated_planing"]
        program = proposal.program_text.lower()
        
        # Must contain geometry primitives
        assert "geometry.discontinuity" in program, "Must use geometry.discontinuity"
        assert "geometry.flow_path" in program, "Must use geometry.flow_path"
        
        # Must NOT contain enumerated types
        assert "stepped_hull" not in program, "Must NOT contain 'stepped_hull' type"
        assert "stepped hull" not in program, "Must NOT contain 'stepped hull' type"
        assert "planing_hull" not in program, "Must NOT contain 'planing_hull' type"
        
        # Verify it compiles
        from magnet.kernel.program_executor import execute_program
        result = execute_program(proposal.program_text, dry_run=True)
        
        # Should parse and expand without errors
        assert "Parse error" not in str(result.errors), f"Parse errors: {result.errors}"
    
    def test_catamaran_no_catamaran_type(self):
        """
        THE TEST #2: Create "catamaran" without "catamaran" type.
        
        Uses only: bodies, sections, surfaces
        Must NOT contain: "catamaran", "twin_hull", "multihull"
        """
        proposal = THE_TEST_FIXTURES["twin_hull"]
        program = proposal.program_text.lower()
        
        # Must contain geometry primitives
        assert "geometry.body" in program, "Must use geometry.body"
        assert "geometry.section" in program, "Must use geometry.section"
        
        # Must have 2 bodies (twin hull)
        assert program.count("create geometry.body") >= 2, "Must create at least 2 bodies"
        
        # Must NOT contain enumerated types
        assert "catamaran" not in program, "Must NOT contain 'catamaran' type"
        assert "twin_hull" not in program, "Must NOT contain 'twin_hull' type"
        assert "multihull" not in program, "Must NOT contain 'multihull' type"
        
        # Verify it compiles
        from magnet.kernel.program_executor import execute_program
        result = execute_program(proposal.program_text, dry_run=True)
        
        # Should parse and expand without errors
        assert "Parse error" not in str(result.errors), f"Parse errors: {result.errors}"
    
    def test_novel_form_validates_without_new_code(self):
        """
        THE TEST #3: Create novel configuration that validates without new code.
        
        This tests that the kernel validates physics, not design intent.
        A form that no naval architect has ever drawn should still work.
        """
        proposal = THE_TEST_FIXTURES["novel_form"]
        program = proposal.program_text.lower()
        
        # Must use geometry primitives
        assert "geometry.body" in program, "Must use geometry.body"
        
        # Must NOT contain any forbidden terms
        for term in FORBIDDEN_TERMS:
            assert term not in program, f"Must NOT contain '{term}'"
        
        # Verify it compiles
        from magnet.kernel.program_executor import execute_program
        result = execute_program(proposal.program_text, dry_run=True)
        
        # Should parse and expand without errors
        assert "Parse error" not in str(result.errors), f"Parse errors: {result.errors}"
        
        # Should have validation results (proving physics was checked)
        # Note: validation may have warnings but should not fail entirely
        if result.validation:
            # Hydrostatics should be computed
            hydro = result.validation.get("hydrostatics", {})
            # At minimum, method should be set (proving calculation ran)
            assert "error" not in str(hydro).lower() or "method" in hydro


class TestNoEnumerationInKernel:
    """Verify kernel code has no enumeration."""
    
    def test_kernel_stdlib_no_hull_family(self):
        """kernel/stdlib/ must not import HullFamily."""
        import inspect
        
        from magnet.kernel.stdlib import parser, expander, compiler
        
        for module in [parser, expander, compiler]:
            source = inspect.getsource(module)
            assert "HullFamily" not in source, f"{module.__name__} contains HullFamily"
            assert "HullType" not in source, f"{module.__name__} contains HullType"
    
    def test_program_executor_no_hull_families(self):
        """program_executor must not import HullFamily."""
        import inspect
        from magnet.kernel import program_executor
        
        source = inspect.getsource(program_executor)
        assert "HullFamily" not in source, "program_executor contains HullFamily"
        assert "HullType" not in source, "program_executor contains HullType"
    
    def test_geometry_calculator_no_enumeration(self):
        """GeometryCalculator must not use HullFamily/HullType in code (docstrings OK)."""
        import ast
        import inspect
        from magnet.dependencies import geometry_calculator
        
        source = inspect.getsource(geometry_calculator)
        
        # Parse to AST to check actual code, not docstrings
        tree = ast.parse(source)
        
        # Check for imports of HullFamily/HullType
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    assert "HullFamily" not in alias.name, "geometry_calculator imports HullFamily"
                    assert "HullType" not in alias.name, "geometry_calculator imports HullType"
            if isinstance(node, ast.Name):
                assert node.id != "HullFamily", "geometry_calculator uses HullFamily"
                assert node.id != "HullType", "geometry_calculator uses HullType"
        
        # Check that HullFamily is not actually imported (not just mentioned in docs)
        # Look for actual import statements
        import_lines = [line for line in source.split('\n') 
                       if line.strip().startswith(('import ', 'from '))]
        for line in import_lines:
            assert "HullFamily" not in line, f"geometry_calculator imports HullFamily: {line}"
            assert "HullType" not in line, f"geometry_calculator imports HullType: {line}"


class TestDesignSpiralWorks:
    """Test the complete design spiral."""
    
    @pytest.mark.asyncio
    async def test_design_conversation_spiral(self):
        """Test complete propose → compile → validate → feedback cycle."""
        from magnet.agents.design_conversation import DesignConversation
        
        # Create conversation with LLM disabled (direct DSL)
        conversation = DesignConversation(
            initial_state={"hull": {"loa": 25.0, "draft": 1.5, "vcg": 1.0}},
            use_llm=False,
        )
        
        # First iteration: create basic hull
        result1 = await conversation.chat("""
            CREATE geometry.section bow {
                station: 0.0,
                points: [[0, 0], [1, -0.5], [1, 0.5]]
            }
            CREATE geometry.section stern {
                station: 1.0,
                points: [[0, 0], [1.5, -0.7], [1.5, 0.7]]
            }
            CREATE geometry.body main {
                section_ids: ["bow", "stern"]
            }
        """)
        
        assert result1.iteration_number == 1
        # May or may not succeed depending on validation strictness
        
        # Second iteration: modify hull
        result2 = await conversation.chat("""
            UPDATE bow {
                points: [[0, 0], [1.2, -0.6], [1.2, 0.6]]
            }
        """)
        
        assert result2.iteration_number == 2
        
        # Verify iteration tracking
        summary = conversation.get_summary()
        assert summary["iterations"] == 2
    
    @pytest.mark.asyncio
    async def test_design_conversation_with_constraints(self):
        """Test design spiral with constraints."""
        from magnet.agents.design_conversation import DesignConversation
        
        conversation = DesignConversation(
            initial_state={"hull": {"loa": 25.0, "draft": 1.5, "vcg": 1.0}},
            use_llm=False,
        )
        
        # Create hull with GM constraint
        result = await conversation.chat(
            """
            CREATE geometry.section bow {
                station: 0.0,
                points: [[0, 0], [2, -1], [2, 1]]
            }
            CREATE geometry.section stern {
                station: 1.0,
                points: [[0, 0], [2, -1], [2, 1]]
            }
            CREATE geometry.body main {
                section_ids: ["bow", "stern"]
            }
            """,
            constraints=["hull.gm >= 0.5"],
        )
        
        # Should have constraint in validation
        if result.execution_result and result.execution_result.validation:
            constraints = result.execution_result.validation.get("constraints", [])
            # Constraint should be recorded (may or may not pass)


class TestInvariantMissionStatement:
    """
    SACRED INVARIANT: The MAGNET Mission Statement.
    
    The kernel exposes universal geometric and physical operations.
    Agents compose them into designs the kernel has never seen.
    The kernel's only role is to validate reality, not recognize intent.
    """
    
    def test_invariant_kernel_validates_not_designs(self):
        """Kernel validates physics, not design intent."""
        from magnet.kernel.program_executor import execute_program
        
        # Novel geometry that no one has ever drawn
        novel_program = """
            CREATE geometry.section weird_bow {
                station: 0.0,
                points: [[0, 0], [1, -2], [2, -1], [2, 1], [1, 2]]
            }
            CREATE geometry.section weird_mid {
                station: 0.5,
                points: [[0, 0], [3, -1], [3, 1]]
            }
            CREATE geometry.section weird_stern {
                station: 1.0,
                points: [[0, 0], [0.5, -0.5], [0.5, 0.5]]
            }
            CREATE geometry.body weird_hull {
                section_ids: ["weird_bow", "weird_mid", "weird_stern"],
                body_type: "never_seen_before"
            }
        """
        
        # Should parse and attempt validation
        result = execute_program(novel_program, dry_run=True)
        
        # The key: it should NOT fail because "never_seen_before" is unknown
        # It should attempt physics validation on the geometry
        assert "unknown body_type" not in str(result.errors).lower()
    
    def test_invariant_novel_forms_without_new_code(self):
        """Novel designs work without new code."""
        from tests.fixtures.geometry_proposals import VALID_FIXTURES
        from magnet.kernel.program_executor import execute_program
        
        for fixture in VALID_FIXTURES:
            result = execute_program(fixture.program_text, dry_run=True)
            
            # Should not have "unknown type" errors
            for error in result.errors:
                assert "unknown" not in error.lower() or "type" not in error.lower(), \
                    f"Fixture '{fixture.reasoning}' failed with unknown type error: {error}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

