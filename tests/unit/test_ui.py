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
# HULL FORMS TESTS
# =============================================================================

class TestHullForms:
    """Test hull form generation."""

    def test_hull_type_enum(self):
        from magnet.vision.hull_forms import HullType
        assert HullType.PLANING.value == "planing"
        assert HullType.DEEP_V.value == "deep_v"
        assert HullType.STEPPED.value == "stepped"

    def test_hull_parameters_defaults(self):
        from magnet.vision.hull_forms import HullParameters
        params = HullParameters()
        assert params.loa == 25.0
        assert params.beam == 5.5
        assert params.draft == 1.4

    def test_hull_parameters_from_state(self):
        from magnet.vision.hull_forms import HullParameters
        state = {
            "hull": {
                "loa": 30.0,
                "beam": 6.0,
                "draft": 1.8,
            }
        }
        params = HullParameters.from_state(state)
        assert params.loa == 30.0
        assert params.beam == 6.0

    def test_hull_parameters_from_empty_state(self):
        from magnet.vision.hull_forms import HullParameters
        params = HullParameters.from_state({})
        assert params.loa == 25.0  # Default

    def test_hull_parameters_validate(self):
        from magnet.vision.hull_forms import HullParameters
        params = HullParameters(loa=25.0, beam=5.5, draft=1.4)
        params.validate()
        assert params.loa == 25.0

    def test_planing_hull_generator(self):
        from magnet.vision.hull_forms import PlaningHullGenerator, HullParameters
        gen = PlaningHullGenerator()
        params = HullParameters()
        mesh = gen.generate(params)
        assert len(mesh.vertices) > 0
        assert len(mesh.faces) > 0

    def test_deep_v_hull_generator(self):
        from magnet.vision.hull_forms import DeepVHullGenerator, HullParameters
        gen = DeepVHullGenerator()
        params = HullParameters(deadrise_deg=22.0)
        mesh = gen.generate(params)
        assert len(mesh.vertices) > 0

    def test_stepped_hull_generator(self):
        from magnet.vision.hull_forms import SteppedHullGenerator, HullParameters
        gen = SteppedHullGenerator()
        params = HullParameters()
        mesh = gen.generate(params)
        assert len(mesh.vertices) > 0

    def test_displacement_hull_generator(self):
        from magnet.vision.hull_forms import DisplacementHullGenerator, HullParameters
        gen = DisplacementHullGenerator()
        params = HullParameters(cb=0.60)
        mesh = gen.generate(params)
        assert len(mesh.vertices) > 0

    def test_hull_form_factory(self):
        from magnet.vision.hull_forms import HullFormFactory, HullType
        gen = HullFormFactory.get_generator(HullType.PLANING)
        assert gen is not None

    def test_hull_form_factory_from_state(self):
        from magnet.vision.hull_forms import HullFormFactory
        state = {"hull": {"loa": 25.0}}
        mesh = HullFormFactory.generate_from_state(state)
        assert len(mesh.vertices) > 0


# =============================================================================
# SNAPSHOTS TESTS
# =============================================================================

class TestSnapshots:
    """Test snapshot manager."""

    def test_snapshot_format_enum(self):
        from magnet.vision.snapshots import SnapshotFormat
        assert SnapshotFormat.PNG.value == "png"
        assert SnapshotFormat.JPEG.value == "jpeg"

    def test_snapshot_quality_enum(self):
        from magnet.vision.snapshots import SnapshotQuality
        assert SnapshotQuality.STANDARD.value == "standard"
        assert SnapshotQuality.HIGH.value == "high"

    def test_snapshot_config_creation(self):
        from magnet.vision.snapshots import SnapshotConfig, SnapshotQuality
        config = SnapshotConfig()
        assert config.width == 1024
        assert config.height == 768
        assert config.quality == SnapshotQuality.STANDARD

    def test_snapshot_config_from_quality(self):
        from magnet.vision.snapshots import SnapshotConfig, SnapshotQuality
        config = SnapshotConfig.from_quality(SnapshotQuality.HIGH)
        assert config.width == 2048
        assert config.height == 1536

    def test_snapshot_config_for_report(self):
        from magnet.vision.snapshots import SnapshotConfig
        config = SnapshotConfig.for_report()
        assert config.dpi == 300

    def test_snapshot_metadata_creation(self):
        from magnet.vision.snapshots import SnapshotMetadata
        meta = SnapshotMetadata(
            snapshot_id="test_001",
            section_id="hull_render",
            phase="hull_form",
        )
        assert meta.snapshot_id == "test_001"
        assert meta.section_id == "hull_render"

    def test_snapshot_metadata_to_dict(self):
        from magnet.vision.snapshots import SnapshotMetadata
        meta = SnapshotMetadata(
            snapshot_id="test_001",
            section_id="hull_render",
        )
        d = meta.to_dict()
        assert d["snapshot_id"] == "test_001"

    def test_snapshot_manager_creation(self):
        import tempfile
        from magnet.vision.snapshots import SnapshotManager
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SnapshotManager(output_dir=tmpdir)
            assert manager is not None
            assert manager.output_dir is not None

    def test_snapshot_manager_get_snapshot(self):
        import tempfile
        from magnet.vision.snapshots import SnapshotManager
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SnapshotManager(output_dir=tmpdir)
            result = manager.get_snapshot("nonexistent")
            assert result is None

    def test_get_snapshot_manager(self):
        from magnet.vision.snapshots import get_snapshot_manager
        manager = get_snapshot_manager()
        assert manager is not None


# =============================================================================
# MATERIALS TESTS
# =============================================================================

class TestMaterials:
    """Test material library."""

    def test_material_type_enum(self):
        from magnet.vision.materials import MaterialType
        assert MaterialType.METAL.value == "metal"
        assert MaterialType.PAINT.value == "paint"
        assert MaterialType.GLASS.value == "glass"

    def test_color_creation(self):
        from magnet.vision.materials import Color
        c = Color(0.5, 0.6, 0.7)
        assert c.r == 0.5
        assert c.g == 0.6
        assert c.b == 0.7
        assert c.a == 1.0

    def test_color_to_tuple(self):
        from magnet.vision.materials import Color
        c = Color(0.5, 0.6, 0.7)
        assert c.to_tuple() == (0.5, 0.6, 0.7)
        assert c.to_rgba() == (0.5, 0.6, 0.7, 1.0)

    def test_color_to_hex(self):
        from magnet.vision.materials import Color
        c = Color(1.0, 0.0, 0.0)
        assert c.to_hex() == "#ff0000"

    def test_color_from_hex(self):
        from magnet.vision.materials import Color
        c = Color.from_hex("#ff0000")
        assert c.r == 1.0
        assert c.g == 0.0
        assert c.b == 0.0

    def test_color_presets(self):
        from magnet.vision.materials import Color
        assert Color.white().r == 1.0
        assert Color.black().r == 0.0
        assert Color.aluminum().r > 0.7

    def test_material_creation(self):
        from magnet.vision.materials import Material, MaterialType, Color
        m = Material(
            name="Test Material",
            material_type=MaterialType.METAL,
            diffuse=Color.aluminum(),
        )
        assert m.name == "Test Material"
        assert m.material_type == MaterialType.METAL

    def test_material_to_dict(self):
        from magnet.vision.materials import Material, MaterialType
        m = Material(name="Test", material_type=MaterialType.METAL)
        d = m.to_dict()
        assert d["name"] == "Test"
        assert d["type"] == "metal"

    def test_marine_materials(self):
        from magnet.vision.materials import MarineMaterials
        hull = MarineMaterials.aluminum_hull()
        assert hull.name == "Aluminum Hull"
        assert hull.metallic == 1.0

    def test_marine_materials_painted(self):
        from magnet.vision.materials import MarineMaterials, Color
        hull = MarineMaterials.painted_hull(Color.navy_blue())
        assert hull.name == "Painted Hull"
        assert hull.metallic == 0.0

    def test_environment_materials(self):
        from magnet.vision.materials import EnvironmentMaterials
        water = EnvironmentMaterials.ocean_water()
        assert water.name == "Ocean Water"
        assert water.transparency > 0

    def test_material_library(self):
        from magnet.vision.materials import MaterialLibrary
        lib = MaterialLibrary()
        assert lib.get("aluminum_hull") is not None
        assert lib.get("steel") is not None
        assert lib.get("glass") is not None

    def test_material_library_get_hull_material(self):
        from magnet.vision.materials import MaterialLibrary
        lib = MaterialLibrary()
        hull = lib.get_hull_material("aluminum")
        assert hull.name == "Aluminum Hull"

        steel = lib.get_hull_material("steel")
        assert steel.name == "Steel Structure"

    def test_material_library_create_custom(self):
        from magnet.vision.materials import MaterialLibrary
        lib = MaterialLibrary()
        custom = lib.create_custom("Custom Red", "#ff0000", metallic=0.3)
        assert custom.name == "Custom Red"

    def test_get_material_library(self):
        from magnet.vision.materials import get_material_library
        lib1 = get_material_library()
        lib2 = get_material_library()
        assert lib1 is lib2  # Singleton


# =============================================================================
# VALIDATION PANEL TESTS
# =============================================================================

class TestValidationPanel:
    """Test validation panel components."""

    def test_severity_enum(self):
        from magnet.ui.validation_panel import ValidationSeverity
        assert ValidationSeverity.ERROR.value == "error"
        assert ValidationSeverity.WARNING.value == "warning"

    def test_category_enum(self):
        from magnet.ui.validation_panel import ValidationCategory
        assert ValidationCategory.STRUCTURAL.value == "structural"
        assert ValidationCategory.STABILITY.value == "stability"

    def test_validation_message_creation(self):
        from magnet.ui.validation_panel import ValidationMessage, ValidationSeverity
        msg = ValidationMessage(
            message_id="err_001",
            severity=ValidationSeverity.ERROR,
            code="GM-001",
            message="GM is below minimum",
        )
        assert msg.message_id == "err_001"
        assert msg.severity == ValidationSeverity.ERROR

    def test_validation_message_from_dict(self):
        from magnet.ui.validation_panel import ValidationMessage
        data = {
            "message_id": "err_001",
            "severity": "error",
            "code": "GM-001",
            "message": "GM is below minimum",
        }
        msg = ValidationMessage.from_dict(data)
        assert msg.code == "GM-001"

    def test_validation_summary(self):
        from magnet.ui.validation_panel import ValidationSummary
        summary = ValidationSummary(
            total_checks=10,
            passed_checks=8,
            failed_checks=2,
            error_count=2,
        )
        assert summary.total_checks == 10
        assert summary.overall_passed is True

    def test_validation_result(self):
        from magnet.ui.validation_panel import (
            ValidationResult, ValidationMessage, ValidationSeverity
        )
        result = ValidationResult()
        result.add_message(ValidationMessage(
            message_id="err_001",
            severity=ValidationSeverity.ERROR,
            message="Test error",
        ))
        assert result.summary.error_count == 1
        assert result.summary.overall_passed is False

    def test_validation_result_get_errors(self):
        from magnet.ui.validation_panel import (
            ValidationResult, ValidationMessage, ValidationSeverity
        )
        result = ValidationResult()
        result.add_message(ValidationMessage(
            message_id="err_001",
            severity=ValidationSeverity.ERROR,
            message="Error",
        ))
        result.add_message(ValidationMessage(
            message_id="warn_001",
            severity=ValidationSeverity.WARNING,
            message="Warning",
        ))
        errors = result.get_errors()
        assert len(errors) == 1

    def test_validation_panel_load_from_state(self):
        from magnet.ui.validation_panel import ValidationPanel
        state = {
            "compliance": {
                "errors": [{"message": "Error 1"}],
                "warnings": [{"message": "Warning 1"}],
                "overall_passed": False,
            }
        }
        panel = ValidationPanel(state)
        result = panel.load_from_state()
        assert result.summary.error_count == 1
        assert result.summary.warning_count == 1

    def test_validation_panel_render_ascii(self):
        from magnet.ui.validation_panel import ValidationPanel
        state = {
            "compliance": {
                "errors": [{"code": "ERR-001", "message": "Test error"}],
                "overall_passed": False,
            }
        }
        panel = ValidationPanel(state)
        output = panel.render_ascii()
        assert "FAILED" in output
        assert "Errors: 1" in output

    def test_validation_history(self):
        from magnet.ui.validation_panel import ValidationHistory, ValidationResult
        history = ValidationHistory()
        result = ValidationResult()
        history.record(result, "hull_form")
        assert history.get_latest() == result
        assert history.get_for_phase("hull_form") == result

    def test_compliance_matrix(self):
        from magnet.ui.validation_panel import ComplianceMatrix
        state = {
            "compliance": {
                "checks": [
                    {"regulation": "ISO", "passed": True},
                    {"regulation": "ISO", "passed": False},
                    {"regulation": "ABS", "passed": True},
                ]
            }
        }
        matrix = ComplianceMatrix(state)
        result = matrix.load_matrix()
        assert result["summary"]["total"] == 3
        assert result["summary"]["failed"] == 1


# =============================================================================
# UI COMPONENTS TESTS
# =============================================================================

class TestUIComponents:
    """Test UI components."""

    def test_component_style(self):
        from magnet.ui.components import ComponentStyle
        style = ComponentStyle(width="100px", padding="10px")
        css = style.to_css()
        assert "width: 100px" in css
        assert "padding: 10px" in css

    def test_component_base(self):
        from magnet.ui.components import Component, ComponentType
        c = Component(
            component_id="test",
            component_type=ComponentType.DISPLAY,
            label="Test",
        )
        assert c.component_id == "test"
        d = c.to_dict()
        assert d["id"] == "test"

    def test_parameter_input(self):
        from magnet.ui.components import ParameterInput, InputType
        inp = ParameterInput(
            component_id="loa",
            label="Length",
            path="hull.loa",
            input_type=InputType.DECIMAL,
            value=25.0,
            min_value=5.0,
            max_value=200.0,
            unit="m",
        )
        assert inp.value == 25.0
        valid, msg = inp.validate()
        assert valid is True

    def test_parameter_input_validation_required(self):
        from magnet.ui.components import ParameterInput, InputType
        inp = ParameterInput(
            component_id="loa",
            label="Length",
            path="hull.loa",
            input_type=InputType.DECIMAL,
            value=None,
            required=True,
        )
        valid, msg = inp.validate()
        assert valid is False
        assert "required" in msg

    def test_parameter_input_validation_range(self):
        from magnet.ui.components import ParameterInput, InputType
        inp = ParameterInput(
            component_id="loa",
            label="Length",
            path="hull.loa",
            input_type=InputType.DECIMAL,
            value=3.0,
            min_value=5.0,
        )
        valid, msg = inp.validate()
        assert valid is False
        assert ">=" in msg

    def test_parameter_group(self):
        from magnet.ui.components import ParameterGroup, ParameterInput, InputType
        group = ParameterGroup(
            group_id="hull",
            title="Hull Parameters",
        )
        group.add_parameter(ParameterInput(
            component_id="loa",
            label="LOA",
            path="hull.loa",
            input_type=InputType.DECIMAL,
            value=25.0,
        ))
        values = group.get_values()
        assert "hull.loa" in values

    def test_value_display(self):
        from magnet.ui.components import ValueDisplay
        display = ValueDisplay(
            component_id="loa_display",
            label="LOA",
            value=25.123,
            unit="m",
            precision=2,
        )
        assert display.format_value() == "25.12"

    def test_alert_component(self):
        from magnet.ui.components import AlertComponent
        alert = AlertComponent(
            component_id="alert1",
            message="Test alert",
            severity="warning",
        )
        assert alert.icon == "\u26a0"
        output = alert.render_ascii()
        assert "WARNING" in output

    def test_button_component(self):
        from magnet.ui.components import ButtonComponent
        btn = ButtonComponent(
            component_id="save_btn",
            text="Save",
            action="save",
            variant="primary",
        )
        output = btn.render_ascii()
        assert "[Save]" in output

    def test_data_table(self):
        from magnet.ui.components import DataTable, Column
        table = DataTable(
            component_id="params_table",
            columns=[
                Column(key="name", header="Name"),
                Column(key="value", header="Value", align="right"),
            ],
            rows=[
                {"name": "LOA", "value": 25.0},
                {"name": "Beam", "value": 5.5},
            ],
        )
        output = table.render_ascii()
        assert "LOA" in output
        assert "Name" in output

    def test_data_table_pagination(self):
        from magnet.ui.components import DataTable, Column
        rows = [{"id": i} for i in range(25)]
        table = DataTable(
            component_id="test",
            columns=[Column(key="id", header="ID")],
            rows=rows,
            page_size=10,
        )
        assert table.total_pages() == 3
        assert len(table.get_page_rows()) == 10

    def test_progress_bar(self):
        from magnet.ui.components import ProgressBar
        bar = ProgressBar(
            component_id="progress",
            label="Loading",
            current=30,
            total=100,
        )
        assert bar.percent == 30.0
        output = bar.render_ascii()
        assert "30%" in output

    def test_step_progress(self):
        from magnet.ui.components import StepProgress
        steps = StepProgress(
            component_id="wizard",
            steps=["Step 1", "Step 2", "Step 3"],
            current_step=1,
            completed_steps=[0],
        )
        output = steps.render_ascii()
        assert "Step 1" in output

    def test_panel(self):
        from magnet.ui.components import Panel
        panel = Panel(
            component_id="info_panel",
            title="Information",
            content="This is some content",
        )
        output = panel.render_ascii()
        assert "Information" in output

    def test_tab_container(self):
        from magnet.ui.components import TabContainer, Tab
        container = TabContainer(
            component_id="tabs",
            tabs=[
                Tab(tab_id="hull", title="Hull", content="Hull content"),
                Tab(tab_id="propulsion", title="Propulsion", content="Prop content"),
            ],
            active_tab=0,
        )
        output = container.render_ascii()
        assert "Hull" in output

    def test_form_builder(self):
        from magnet.ui.components import FormBuilder
        state = {"hull": {"loa": 25.0, "beam": 5.5}}
        builder = FormBuilder(state)
        hull_form = builder.build_hull_form()
        assert len(hull_form.parameters) > 0

    def test_component_registry(self):
        from magnet.ui.components import ComponentRegistry, Component, ComponentType
        registry = ComponentRegistry()
        registry.register(Component(
            component_id="test_comp",
            component_type=ComponentType.DISPLAY,
        ))
        comp = registry.get("test_comp")
        assert comp is not None
        assert comp.component_id == "test_comp"


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
