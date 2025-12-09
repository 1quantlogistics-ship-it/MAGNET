"""
tests/unit/test_ui.py - Tests for UI modules (Modules 51-54)
BRAVO OWNS THIS FILE.

Tests for:
- ui/utils.py - Unified state access
- cli/ - Command line interface
- vision/ - Vision subsystem
- ui/dashboard.py - Dashboard components
- ui/phase_navigator.py - Phase navigation
"""

import pytest
from typing import Dict, Any


# =============================================================================
# UI UTILS TESTS
# =============================================================================

class TestUIFieldAliases:
    """Test UI field alias system."""

    def test_aliases_exist(self):
        from magnet.ui.utils import UI_FIELD_ALIASES
        assert "hull.displacement_mt" in UI_FIELD_ALIASES
        assert "hull.loa" in UI_FIELD_ALIASES
        assert "stability.gm_transverse_m" in UI_FIELD_ALIASES

    def test_displacement_aliases(self):
        from magnet.ui.utils import UI_FIELD_ALIASES
        aliases = UI_FIELD_ALIASES["hull.displacement_mt"]
        assert "weight.full_load_displacement_mt" in aliases
        assert "displacement_tonnes" in aliases


class TestGetNested:
    """Test get_nested function."""

    def test_dict_access(self):
        from magnet.ui.utils import get_nested
        data = {"hull": {"loa": 25.0}}
        assert get_nested(data, "hull.loa") == 25.0

    def test_missing_path(self):
        from magnet.ui.utils import get_nested
        data = {"hull": {"loa": 25.0}}
        assert get_nested(data, "hull.beam") is None

    def test_default_value(self):
        from magnet.ui.utils import get_nested
        data = {"hull": {"loa": 25.0}}
        assert get_nested(data, "hull.beam", 5.0) == 5.0

    def test_deep_nesting(self):
        from magnet.ui.utils import get_nested
        data = {"a": {"b": {"c": {"d": 42}}}}
        assert get_nested(data, "a.b.c.d") == 42

    def test_none_data(self):
        from magnet.ui.utils import get_nested
        assert get_nested(None, "hull.loa", 0) == 0


class TestGetStateValue:
    """Test get_state_value with aliases."""

    def test_direct_path(self):
        from magnet.ui.utils import get_state_value
        state = {"hull": {"loa": 25.0}}
        assert get_state_value(state, "hull.loa") == 25.0

    def test_alias_resolution(self):
        from magnet.ui.utils import get_state_value
        state = {"weight": {"full_load_displacement_mt": 150.0}}
        assert get_state_value(state, "hull.displacement_mt") == 150.0

    def test_displacement_via_weight(self):
        from magnet.ui.utils import get_state_value
        state = {"weight": {"full_load_displacement_mt": 200.0}}
        result = get_state_value(state, "hull.displacement_mt")
        assert result == 200.0

    def test_no_alias_mode(self):
        from magnet.ui.utils import get_state_value
        state = {"weight": {"full_load_displacement_mt": 150.0}}
        result = get_state_value(state, "hull.displacement_mt", use_aliases=False)
        assert result is None

    def test_default_value(self):
        from magnet.ui.utils import get_state_value
        state = {}
        assert get_state_value(state, "hull.loa", 25.0) == 25.0


class TestSetStateValue:
    """Test set_state_value function."""

    def test_set_simple_path(self):
        from magnet.ui.utils import set_state_value
        state = {}
        result = set_state_value(state, "hull.loa", 25.0)
        assert result is True
        assert state["hull"]["loa"] == 25.0

    def test_set_deep_path(self):
        from magnet.ui.utils import set_state_value
        state = {}
        result = set_state_value(state, "a.b.c.d", 42)
        assert result is True
        assert state["a"]["b"]["c"]["d"] == 42


class TestPhaseStateTranslation:
    """Test phase state enum translation."""

    def test_enum_map_exists(self):
        from magnet.ui.utils import PHASE_STATE_ENUM_MAP
        assert PHASE_STATE_ENUM_MAP["LOCKED"] == "completed"
        assert PHASE_STATE_ENUM_MAP["ACTIVE"] == "active"
        assert PHASE_STATE_ENUM_MAP["PENDING"] == "pending"

    def test_get_phase_status_dict(self):
        from magnet.ui.utils import get_phase_status
        state = {"phase_states": {"hull_form": {"status": "completed"}}}
        assert get_phase_status(state, "hull_form") == "completed"

    def test_get_phase_status_enum_translation(self):
        from magnet.ui.utils import get_phase_status
        state = {"phase_states": {"hull_form": {"status": "LOCKED"}}}
        assert get_phase_status(state, "hull_form") == "completed"

    def test_get_phase_status_default(self):
        from magnet.ui.utils import get_phase_status
        state = {}
        assert get_phase_status(state, "hull_form") == "pending"

    def test_set_phase_status(self):
        from magnet.ui.utils import set_phase_status, get_phase_status
        state = {}
        result = set_phase_status(state, "hull_form", "completed")
        assert result is True
        assert get_phase_status(state, "hull_form") == "completed"


class TestSnapshotRegistry:
    """Test snapshot registry."""

    def test_register_and_get(self):
        from magnet.ui.utils import SnapshotRegistry
        registry = SnapshotRegistry()
        registry.register("hull_render", "/tmp/hull.png", "hull_form")
        assert registry.get("hull_render") == "/tmp/hull.png"

    def test_get_for_phase(self):
        from magnet.ui.utils import SnapshotRegistry
        registry = SnapshotRegistry()
        registry.register("hull_render", "/tmp/hull.png", "hull_form")
        registry.register("hull_top", "/tmp/hull_top.png", "hull_form")
        registry.register("stability_chart", "/tmp/stab.png", "stability")

        phase_snaps = registry.get_for_phase("hull_form")
        assert len(phase_snaps) == 2
        assert "hull_render" in phase_snaps

    def test_get_all(self):
        from magnet.ui.utils import SnapshotRegistry
        registry = SnapshotRegistry()
        registry.register("a", "/a.png")
        registry.register("b", "/b.png")
        all_snaps = registry.get_all()
        assert len(all_snaps) == 2

    def test_clear(self):
        from magnet.ui.utils import SnapshotRegistry
        registry = SnapshotRegistry()
        registry.register("a", "/a.png")
        registry.clear()
        assert registry.get("a") is None


class TestPhaseCompletionHooks:
    """Test phase completion hooks."""

    def test_register_and_trigger(self):
        from magnet.ui.utils import PhaseCompletionHooks

        results = []

        def callback(state, phase=None, **kwargs):
            results.append(phase)
            return phase

        PhaseCompletionHooks.clear()
        PhaseCompletionHooks.register("hull_form", callback)
        PhaseCompletionHooks.trigger("hull_form", {})

        assert "hull_form" in results

    def test_clear_hooks(self):
        from magnet.ui.utils import PhaseCompletionHooks

        PhaseCompletionHooks.clear()
        PhaseCompletionHooks.register("test", lambda s, **k: None)
        PhaseCompletionHooks.clear("test")
        results = PhaseCompletionHooks.trigger("test", {})
        assert len(results) == 0


class TestStateSerialization:
    """Test state serialization."""

    def test_serialize_dict(self):
        from magnet.ui.utils import serialize_state
        state = {"hull": {"loa": 25.0}}
        result = serialize_state(state)
        assert result["hull"]["loa"] == 25.0

    def test_load_state_from_dict(self):
        from magnet.ui.utils import load_state_from_dict
        state = {}
        data = {"hull": {"loa": 25.0}}
        result = load_state_from_dict(state, data)
        assert result is True
        assert state["hull"]["loa"] == 25.0


# =============================================================================
# CLI TESTS
# =============================================================================

class TestCLIContext:
    """Test CLI context."""

    def test_context_creation(self):
        from magnet.cli.core import CLIContext, OutputFormat
        ctx = CLIContext()
        assert ctx.output_format == OutputFormat.TEXT

    def test_context_get_value(self):
        from magnet.cli.core import CLIContext
        ctx = CLIContext()
        ctx.state = {"hull": {"loa": 25.0}}
        assert ctx.get_value("hull.loa") == 25.0


class TestCommandResult:
    """Test command result."""

    def test_result_success(self):
        from magnet.cli.core import CommandResult
        result = CommandResult(success=True, message="Done")
        assert result.success is True
        assert result.message == "Done"

    def test_result_to_dict(self):
        from magnet.cli.core import CommandResult
        result = CommandResult(success=True, data={"key": "value"})
        d = result.to_dict()
        assert d["success"] is True
        assert d["data"]["key"] == "value"


class TestCommandRegistry:
    """Test command registry."""

    def test_register_and_get(self):
        from magnet.cli.core import CommandRegistry, CLICommand, CommandResult
        import argparse

        class TestCmd(CLICommand):
            name = "test_cmd"
            description = "Test command"

            def execute(self, ctx, args):
                return CommandResult(success=True)

        registry = CommandRegistry()
        registry.register(TestCmd())
        cmd = registry.get("test_cmd")
        assert cmd is not None
        assert cmd.name == "test_cmd"

    def test_list_commands(self):
        from magnet.cli.core import CommandRegistry, CLICommand, CommandResult

        class TestCmd(CLICommand):
            name = "list_test"
            description = "Test"

            def execute(self, ctx, args):
                return CommandResult(success=True)

        registry = CommandRegistry()
        registry.register(TestCmd())
        cmds = registry.list_commands()
        assert "list_test" in cmds


class TestCLICommands:
    """Test CLI commands."""

    def test_new_command(self):
        from magnet.cli.commands.design import NewCommand
        from magnet.cli.core import CLIContext, CommandResult
        import argparse

        cmd = NewCommand()
        ctx = CLIContext()
        ctx.state = {}
        args = argparse.Namespace(name="Test Design", template=None, output=None)
        result = cmd.execute(ctx, args)
        assert result.success is True
        assert "design_id" in result.data

    def test_status_command_no_state(self):
        from magnet.cli.commands.query import StatusCommand
        from magnet.cli.core import CLIContext
        import argparse

        cmd = StatusCommand()
        ctx = CLIContext()
        args = argparse.Namespace()
        result = cmd.execute(ctx, args)
        assert result.success is False

    def test_get_command(self):
        from magnet.cli.commands.query import GetCommand
        from magnet.cli.core import CLIContext
        import argparse

        cmd = GetCommand()
        ctx = CLIContext()
        ctx.state = {"hull": {"loa": 25.0}}
        args = argparse.Namespace(path="hull.loa", no_alias=False)
        result = cmd.execute(ctx, args)
        assert result.success is True
        assert result.data["value"] == 25.0

    def test_set_command(self):
        from magnet.cli.commands.query import SetCommand
        from magnet.cli.core import CLIContext
        import argparse

        cmd = SetCommand()
        ctx = CLIContext()
        ctx.state = {}
        args = argparse.Namespace(path="hull.loa", value="30.0", type="float")
        result = cmd.execute(ctx, args)
        assert result.success is True
        assert ctx.state["hull"]["loa"] == 30.0


# =============================================================================
# VISION TESTS
# =============================================================================

class TestVisionGeometry:
    """Test vision geometry module."""

    def test_vertex_creation(self):
        from magnet.vision.geometry import Vertex
        v = Vertex(1.0, 2.0, 3.0)
        assert v.x == 1.0
        assert v.y == 2.0
        assert v.z == 3.0
        assert v.to_tuple() == (1.0, 2.0, 3.0)

    def test_face_creation(self):
        from magnet.vision.geometry import Face
        f = Face(vertices=[0, 1, 2])
        assert len(f.vertices) == 3

    def test_mesh_creation(self):
        from magnet.vision.geometry import Mesh, GeometryType, Vertex, Face
        mesh = Mesh(
            mesh_id="test",
            name="Test Mesh",
            geometry_type=GeometryType.HULL,
        )
        mesh.vertices = [Vertex(0, 0, 0), Vertex(1, 0, 0), Vertex(0, 1, 0)]
        mesh.faces = [Face(vertices=[0, 1, 2])]
        assert len(mesh.vertices) == 3
        assert len(mesh.faces) == 1

    def test_hull_generator_defaults(self):
        from magnet.vision.geometry import HullGenerator
        gen = HullGenerator()
        mesh = gen.generate_from_state({})  # Empty state - uses defaults
        assert len(mesh.vertices) > 0
        assert len(mesh.faces) > 0

    def test_hull_generator_with_state(self):
        from magnet.vision.geometry import HullGenerator
        gen = HullGenerator()
        state = {
            "hull": {
                "loa": 30.0,
                "beam": 6.0,
                "draft": 1.5,
            }
        }
        mesh = gen.generate_from_state(state)
        assert len(mesh.vertices) > 0

    def test_geometry_manager(self):
        from magnet.vision.geometry import GeometryManager
        manager = GeometryManager()
        state = {"hull": {"loa": 25.0}}
        mesh = manager.generate_hull_from_state(state)
        assert mesh is not None
        assert manager.get_mesh("hull_main") is not None


class TestVisionRouter:
    """Test vision router."""

    def test_vision_request_creation(self):
        from magnet.vision.router import VisionRequest
        req = VisionRequest(
            request_id="test",
            operation="generate",
            parameters={"key": "value"},
        )
        assert req.request_id == "test"
        assert req.operation == "generate"

    def test_vision_response_creation(self):
        from magnet.vision.router import VisionResponse
        resp = VisionResponse(
            request_id="test",
            success=True,
            result={"key": "value"},
        )
        assert resp.success is True

    def test_router_generate(self):
        from magnet.vision.router import VisionRouter, VisionRequest
        router = VisionRouter(state={"hull": {"loa": 25.0}})
        req = VisionRequest(request_id="test", operation="generate")
        resp = router.process_request(req)
        assert resp.success is True

    def test_router_unknown_operation(self):
        from magnet.vision.router import VisionRouter, VisionRequest
        router = VisionRouter()
        req = VisionRequest(request_id="test", operation="unknown")
        resp = router.process_request(req)
        assert resp.success is False


# =============================================================================
# UI COMPONENTS TESTS
# =============================================================================

class TestDashboard:
    """Test dashboard components."""

    def test_widget_creation(self):
        from magnet.ui.dashboard import Widget, WidgetType
        w = Widget(
            widget_id="test",
            widget_type=WidgetType.METRIC,
            title="Test Widget",
        )
        assert w.widget_id == "test"

    def test_metric_widget(self):
        from magnet.ui.dashboard import MetricWidget
        w = MetricWidget(
            widget_id="loa",
            title="LOA",
            value=25.0,
            unit="m",
        )
        assert w.data["value"] == 25.0
        assert w.data["unit"] == "m"

    def test_progress_widget(self):
        from magnet.ui.dashboard import ProgressWidget
        w = ProgressWidget(
            widget_id="progress",
            title="Progress",
            current=3,
            total=10,
        )
        assert w.data["percent"] == 30.0

    def test_validation_widget(self):
        from magnet.ui.dashboard import ValidationWidget
        w = ValidationWidget(
            widget_id="validation",
            title="Validation",
            passed=True,
            errors=[],
            warnings=[{"msg": "warn"}],
        )
        assert w.data["passed"] is True
        assert w.data["warning_count"] == 1

    def test_dashboard_builder(self):
        from magnet.ui.dashboard import DashboardBuilder
        state = {
            "metadata": {"design_id": "TEST-001"},
            "hull": {"loa": 25.0, "beam": 5.5},
        }
        builder = DashboardBuilder(state)
        widgets = builder.build_overview_dashboard()
        assert len(widgets) > 0


class TestPhaseNavigator:
    """Test phase navigator."""

    def test_phase_status_enum(self):
        from magnet.ui.phase_navigator import PhaseStatus
        assert PhaseStatus.PENDING.value == "pending"
        assert PhaseStatus.COMPLETED.value == "completed"

    def test_phase_info_creation(self):
        from magnet.ui.phase_navigator import PhaseInfo, PhaseStatus
        info = PhaseInfo(
            phase_id="hull_form",
            name="Hull Form",
            status=PhaseStatus.ACTIVE,
        )
        assert info.phase_id == "hull_form"
        assert info.status == PhaseStatus.ACTIVE

    def test_phase_definitions_exist(self):
        from magnet.ui.phase_navigator import PHASE_DEFINITIONS
        assert "mission" in PHASE_DEFINITIONS
        assert "hull_form" in PHASE_DEFINITIONS
        assert "compliance" in PHASE_DEFINITIONS

    def test_navigator_get_all_phases(self):
        from magnet.ui.phase_navigator import PhaseNavigator
        state = {}
        nav = PhaseNavigator(state)
        phases = nav.get_all_phases()
        assert len(phases) == 8

    def test_navigator_get_phase_info(self):
        from magnet.ui.phase_navigator import PhaseNavigator, PhaseStatus
        state = {"phase_states": {"hull_form": {"status": "completed"}}}
        nav = PhaseNavigator(state)
        info = nav.get_phase_info("hull_form")
        assert info.status == PhaseStatus.COMPLETED

    def test_navigator_get_next_phase(self):
        from magnet.ui.phase_navigator import PhaseNavigator
        state = {"phase_states": {"mission": {"status": "completed"}}}
        nav = PhaseNavigator(state)
        next_phase = nav.get_next_phase()
        assert next_phase is not None
        assert next_phase.phase_id == "hull_form"

    def test_navigator_can_start_phase(self):
        from magnet.ui.phase_navigator import PhaseNavigator
        state = {"phase_states": {"mission": {"status": "completed"}}}
        nav = PhaseNavigator(state)
        assert nav.can_start_phase("hull_form") is True
        assert nav.can_start_phase("structure") is False

    def test_navigator_phase_tree(self):
        from magnet.ui.phase_navigator import PhaseNavigator
        state = {}
        nav = PhaseNavigator(state)
        tree = nav.get_phase_tree()
        assert "phases" in tree
        assert "completed_count" in tree
        assert tree["total_count"] == 8

    def test_navigator_render_ascii(self):
        from magnet.ui.phase_navigator import PhaseNavigator
        state = {"phase_states": {"mission": {"status": "completed"}}}
        nav = PhaseNavigator(state)
        output = nav.render_ascii()
        assert "Design Phases" in output
        assert "Mission Definition" in output


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestUIIntegration:
    """Integration tests for UI layer."""

    def test_field_alias_displacement_integration(self):
        """Test displacement alias resolves correctly."""
        from magnet.ui.utils import get_state_value
        state = {"weight": {"full_load_displacement_mt": 150.0}}
        assert get_state_value(state, "hull.displacement_mt") == 150.0

    def test_phase_status_translation_integration(self):
        """Test phase status translation works."""
        from magnet.ui.utils import get_phase_status
        state = {"phase_states": {"hull_form": {"status": "LOCKED"}}}
        assert get_phase_status(state, "hull_form") == "completed"

    def test_snapshot_registry_integration(self):
        """Test snapshot registry singleton works."""
        from magnet.ui.utils import snapshot_registry
        snapshot_registry.clear()
        snapshot_registry.register("hull_render", "/tmp/hull.png", "hull_form")
        assert snapshot_registry.get("hull_render") == "/tmp/hull.png"
        snapshot_registry.clear()

    def test_vision_safe_defaults_integration(self):
        """Test vision generates with empty state."""
        from magnet.vision.geometry import HullGenerator
        gen = HullGenerator()
        mesh = gen.generate_from_state({})  # Empty state
        assert len(mesh.vertices) > 0  # Should use defaults

    def test_cli_to_ui_integration(self):
        """Test CLI uses UI utils correctly."""
        from magnet.cli.core import CLIContext
        from magnet.ui.utils import get_state_value

        ctx = CLIContext()
        ctx.state = {"hull": {"loa": 25.0}}

        # CLI context should use same get_state_value
        assert ctx.get_value("hull.loa") == get_state_value(ctx.state, "hull.loa")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
