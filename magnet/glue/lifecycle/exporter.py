"""
glue/lifecycle/exporter.py - Design export functionality

ALPHA OWNS THIS FILE.

Module 45: Design Lifecycle & Export - v1.1
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
import json
import logging

from ..utils import safe_get, serialize_state

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger(__name__)


class ExportFormat(Enum):
    """Export format options."""
    JSON = "json"
    JSON_PRETTY = "json_pretty"
    SUMMARY = "summary"
    REPORT = "report"


@dataclass
class ExportConfig:
    """Configuration for export."""

    format: ExportFormat = ExportFormat.JSON_PRETTY
    include_history: bool = False
    include_metadata: bool = True
    include_performance: bool = True
    include_compliance: bool = True

    # Sections to include (empty = all)
    sections: List[str] = None

    # Output path
    output_path: Optional[str] = None


class DesignExporter:
    """
    Exports design state to various formats.

    v1.1: Handles missing keys gracefully.
    """

    def __init__(self, state: Optional["StateManager"] = None):
        """
        Initialize exporter.

        Args:
            state: StateManager to export from
        """
        self.state = state

    def export(self, config: Optional[ExportConfig] = None) -> str:
        """
        Export design to string.

        Args:
            config: Export configuration

        Returns:
            Exported content as string
        """
        config = config or ExportConfig()

        if config.format == ExportFormat.JSON:
            return self._export_json(config, pretty=False)
        elif config.format == ExportFormat.JSON_PRETTY:
            return self._export_json(config, pretty=True)
        elif config.format == ExportFormat.SUMMARY:
            return self._export_summary(config)
        elif config.format == ExportFormat.REPORT:
            return self._export_report(config)
        else:
            return self._export_json(config, pretty=True)

    def export_to_file(
        self,
        filepath: str,
        config: Optional[ExportConfig] = None,
    ) -> bool:
        """
        Export design to file.

        Args:
            filepath: Output file path
            config: Export configuration

        Returns:
            True if successful
        """
        config = config or ExportConfig()
        config.output_path = filepath

        try:
            content = self.export(config)
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"Exported design to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False

    def _export_json(self, config: ExportConfig, pretty: bool) -> str:
        """Export as JSON."""
        data = self._build_export_data(config)

        if pretty:
            return json.dumps(data, indent=2, default=str)
        else:
            return json.dumps(data, default=str)

    def _export_summary(self, config: ExportConfig) -> str:
        """Export as text summary."""
        lines = []
        lines.append("=" * 60)
        lines.append("DESIGN SUMMARY")
        lines.append("=" * 60)
        lines.append("")

        if self.state:
            # Identity
            design_id = safe_get(self.state, "design_id", "Unknown")
            design_name = safe_get(self.state, "design_name", "Unnamed Design")
            lines.append(f"Design: {design_name}")
            lines.append(f"ID: {design_id}")
            lines.append("")

            # Mission
            lines.append("MISSION")
            lines.append("-" * 40)
            vessel_type = safe_get(self.state, "mission.vessel_type", "Not specified")
            max_speed = safe_get(self.state, "mission.max_speed_kts", 0)
            crew = safe_get(self.state, "mission.crew_size", 0)
            passengers = safe_get(self.state, "mission.passengers", 0)
            lines.append(f"  Vessel Type: {vessel_type}")
            lines.append(f"  Max Speed: {max_speed} kts")
            lines.append(f"  Crew: {crew}")
            lines.append(f"  Passengers: {passengers}")
            lines.append("")

            # Hull
            lines.append("HULL DIMENSIONS")
            lines.append("-" * 40)
            loa = safe_get(self.state, "hull.loa", 0)
            beam = safe_get(self.state, "hull.beam", 0)
            draft = safe_get(self.state, "hull.draft", 0)
            depth = safe_get(self.state, "hull.depth", 0)
            disp = safe_get(self.state, "hull.displacement_mt", 0)
            lines.append(f"  LOA: {loa:.2f} m")
            lines.append(f"  Beam: {beam:.2f} m")
            lines.append(f"  Draft: {draft:.2f} m")
            lines.append(f"  Depth: {depth:.2f} m")
            lines.append(f"  Displacement: {disp:.1f} MT")
            lines.append("")

            # Weight
            lines.append("WEIGHT ESTIMATE")
            lines.append("-" * 40)
            lightship = safe_get(self.state, "weight.lightship_mt", 0)
            vcg = safe_get(self.state, "weight.lightship_vcg_m", 0)
            lines.append(f"  Lightship: {lightship:.1f} MT")
            lines.append(f"  VCG: {vcg:.3f} m")
            lines.append("")

            # Stability
            lines.append("STABILITY")
            lines.append("-" * 40)
            gm = safe_get(self.state, "stability.gm_transverse_m", 0)
            lines.append(f"  GM: {gm:.3f} m")
            lines.append("")

            # Performance (v1.1: handle missing gracefully)
            if config.include_performance:
                lines.append("PERFORMANCE")
                lines.append("-" * 40)
                cruise_power = safe_get(self.state, "performance.cruise_power_kw", 0)
                max_power = safe_get(self.state, "performance.max_power_kw", 0)
                range_nm = safe_get(self.state, "performance.range_nm", 0)
                if cruise_power or max_power or range_nm:
                    lines.append(f"  Cruise Power: {cruise_power:.0f} kW")
                    lines.append(f"  Max Power: {max_power:.0f} kW")
                    lines.append(f"  Range: {range_nm:.0f} nm")
                else:
                    lines.append("  (Not calculated)")
                lines.append("")

            # Compliance (v1.1: handle missing gracefully)
            if config.include_compliance:
                lines.append("COMPLIANCE")
                lines.append("-" * 40)
                verified = safe_get(self.state, "compliance.verified", False)
                status = "Verified" if verified else "Not verified"
                lines.append(f"  Status: {status}")
                lines.append("")

        lines.append("=" * 60)
        lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")

        return "\n".join(lines)

    def _export_report(self, config: ExportConfig) -> str:
        """Export as detailed Markdown report."""
        lines = []
        lines.append("# Design Report")
        lines.append("")

        if self.state:
            design_name = safe_get(self.state, "design_name", "Unnamed Design")
            lines.append(f"**Design:** {design_name}")
            lines.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
            lines.append("")

            # Table of contents
            lines.append("## Table of Contents")
            lines.append("1. [Mission](#mission)")
            lines.append("2. [Hull](#hull)")
            lines.append("3. [Weight](#weight)")
            lines.append("4. [Stability](#stability)")
            lines.append("5. [Performance](#performance)")
            lines.append("6. [Compliance](#compliance)")
            lines.append("")

            # Mission section
            lines.append("## Mission")
            lines.append("")
            lines.append("| Parameter | Value |")
            lines.append("|-----------|-------|")
            lines.append(f"| Vessel Type | {safe_get(self.state, 'mission.vessel_type', 'N/A')} |")
            lines.append(f"| Max Speed | {safe_get(self.state, 'mission.max_speed_kts', 0)} kts |")
            lines.append(f"| Cruise Speed | {safe_get(self.state, 'mission.cruise_speed_kts', 0)} kts |")
            lines.append(f"| Crew | {safe_get(self.state, 'mission.crew_size', 0)} |")
            lines.append(f"| Passengers | {safe_get(self.state, 'mission.passengers', 0)} |")
            lines.append("")

            # Hull section
            lines.append("## Hull")
            lines.append("")
            lines.append("| Parameter | Value | Unit |")
            lines.append("|-----------|-------|------|")
            lines.append(f"| LOA | {safe_get(self.state, 'hull.loa', 0):.2f} | m |")
            lines.append(f"| LWL | {safe_get(self.state, 'hull.lwl', 0):.2f} | m |")
            lines.append(f"| Beam | {safe_get(self.state, 'hull.beam', 0):.2f} | m |")
            lines.append(f"| Draft | {safe_get(self.state, 'hull.draft', 0):.2f} | m |")
            lines.append(f"| Depth | {safe_get(self.state, 'hull.depth', 0):.2f} | m |")
            lines.append(f"| Displacement | {safe_get(self.state, 'hull.displacement_mt', 0):.1f} | MT |")
            lines.append(f"| Block Coefficient | {safe_get(self.state, 'hull.cb', 0):.3f} | - |")
            lines.append("")

            # Weight section
            lines.append("## Weight")
            lines.append("")
            lines.append("| Parameter | Value | Unit |")
            lines.append("|-----------|-------|------|")
            lines.append(f"| Lightship | {safe_get(self.state, 'weight.lightship_mt', 0):.1f} | MT |")
            lines.append(f"| VCG | {safe_get(self.state, 'weight.lightship_vcg_m', 0):.3f} | m |")
            lines.append(f"| LCG | {safe_get(self.state, 'weight.lightship_lcg_m', 0):.3f} | m |")
            lines.append("")

            # Stability section
            lines.append("## Stability")
            lines.append("")
            lines.append("| Parameter | Value | Unit |")
            lines.append("|-----------|-------|------|")
            lines.append(f"| GM | {safe_get(self.state, 'stability.gm_transverse_m', 0):.3f} | m |")
            lines.append(f"| KG | {safe_get(self.state, 'stability.kg_m', 0):.3f} | m |")
            lines.append(f"| KB | {safe_get(self.state, 'stability.kb_m', 0):.3f} | m |")
            lines.append(f"| BM | {safe_get(self.state, 'stability.bm_m', 0):.3f} | m |")
            lines.append("")

            # Performance section
            lines.append("## Performance")
            lines.append("")
            if config.include_performance:
                lines.append("| Parameter | Value | Unit |")
                lines.append("|-----------|-------|------|")
                lines.append(f"| Cruise Power | {safe_get(self.state, 'performance.cruise_power_kw', 0):.0f} | kW |")
                lines.append(f"| Max Power | {safe_get(self.state, 'performance.max_power_kw', 0):.0f} | kW |")
                lines.append(f"| Range | {safe_get(self.state, 'performance.range_nm', 0):.0f} | nm |")
                lines.append(f"| Endurance | {safe_get(self.state, 'performance.endurance_hr', 0):.1f} | hr |")
            else:
                lines.append("*Performance data not included*")
            lines.append("")

            # Compliance section
            lines.append("## Compliance")
            lines.append("")
            if config.include_compliance:
                verified = safe_get(self.state, "compliance.verified", False)
                status = "Verified" if verified else "Not verified"
                lines.append(f"**Status:** {status}")
            else:
                lines.append("*Compliance data not included*")
            lines.append("")

        lines.append("---")
        lines.append("*Report generated by MAGNET Design System*")

        return "\n".join(lines)

    def _build_export_data(self, config: ExportConfig) -> Dict[str, Any]:
        """Build export data dictionary."""
        if not self.state:
            return {"error": "No state available"}

        data = serialize_state(self.state)

        # Filter sections if specified
        if config.sections:
            filtered = {}
            for section in config.sections:
                if section in data:
                    filtered[section] = data[section]
            data = filtered

        # Remove history if not requested
        if not config.include_history:
            data.pop("history", None)

        # Remove metadata if not requested
        if not config.include_metadata:
            data.pop("metadata", None)
            data.pop("created_at", None)
            data.pop("updated_at", None)
            data.pop("created_by", None)

        # Remove performance if not requested (v1.1: handle gracefully)
        if not config.include_performance:
            data.pop("performance", None)

        # Remove compliance if not requested (v1.1: handle gracefully)
        if not config.include_compliance:
            data.pop("compliance", None)

        # Add export metadata
        data["_export"] = {
            "format": config.format.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.1.0",
        }

        return data
