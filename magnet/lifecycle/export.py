"""
lifecycle/export.py - Design export capabilities
BRAVO OWNS THIS FILE.

Section 45: Design Lifecycle
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime
from pathlib import Path
from enum import Enum
import json
import logging

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


class ExportFormat(Enum):
    """Export formats."""
    JSON = "json"
    YAML = "yaml"
    XML = "xml"
    CSV = "csv"
    PDF = "pdf"


@dataclass
class ExportConfig:
    """Configuration for export."""

    format: ExportFormat = ExportFormat.JSON

    # What to include
    include_hull: bool = True
    include_propulsion: bool = True
    include_stability: bool = True
    include_structure: bool = True
    include_systems: bool = True
    include_performance: bool = True

    # Metadata
    include_validation_results: bool = True
    include_version_info: bool = True

    # Formatting
    pretty_print: bool = True
    decimal_places: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "format": self.format.value,
            "include_hull": self.include_hull,
            "include_propulsion": self.include_propulsion,
            "include_stability": self.include_stability,
            "include_structure": self.include_structure,
            "include_systems": self.include_systems,
            "include_performance": self.include_performance,
            "include_validation_results": self.include_validation_results,
            "include_version_info": self.include_version_info,
        }


def _serialize_state(state: Any) -> Dict[str, Any]:
    """Serialize state to dict."""
    if hasattr(state, 'to_dict'):
        return state.to_dict()
    elif hasattr(state, '_state'):
        if hasattr(state._state, 'to_dict'):
            return state._state.to_dict()
        elif hasattr(state._state, '__dict__'):
            return dict(state._state.__dict__)
    elif hasattr(state, '__dict__'):
        return dict(state.__dict__)
    return {}


class DesignExporter:
    """
    Exports design data in various formats.
    """

    def __init__(self, state: "StateManager"):
        self.state = state
        self.logger = logging.getLogger("lifecycle.export")

    def export(
        self,
        output_path: str,
        config: ExportConfig = None,
    ) -> bool:
        """Export design to file."""
        config = config or ExportConfig()

        # Get state data
        data = self._prepare_data(config)

        # Export based on format
        try:
            if config.format == ExportFormat.JSON:
                return self._export_json(output_path, data, config)
            elif config.format == ExportFormat.YAML:
                return self._export_yaml(output_path, data, config)
            elif config.format == ExportFormat.CSV:
                return self._export_csv(output_path, data, config)
            else:
                self.logger.error(f"Unsupported format: {config.format}")
                return False
        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            return False

    def _prepare_data(self, config: ExportConfig) -> Dict[str, Any]:
        """Prepare data for export."""
        # v1.1: Use helper
        state_dict = _serialize_state(self.state)

        data = {
            "export_info": {
                "exported_at": datetime.utcnow().isoformat(),
                "format": config.format.value,
            }
        }

        # Filter sections based on config
        sections = {
            "hull": config.include_hull,
            "propulsion": config.include_propulsion,
            "stability": config.include_stability,
            "structure": config.include_structure,
            "systems": config.include_systems,
            "performance": config.include_performance,
        }

        for section, include in sections.items():
            if include and section in state_dict:
                data[section] = state_dict[section]

        # Add version info if requested
        if config.include_version_info:
            data["version_info"] = {
                "created_at": datetime.utcnow().isoformat(),
            }

        return data

    def _export_json(
        self,
        output_path: str,
        data: Dict[str, Any],
        config: ExportConfig,
    ) -> bool:
        """Export to JSON format."""
        indent = 2 if config.pretty_print else None

        path = Path(output_path)
        path.write_text(json.dumps(data, indent=indent, default=str))

        self.logger.info(f"Exported to {output_path}")
        return True

    def _export_yaml(
        self,
        output_path: str,
        data: Dict[str, Any],
        config: ExportConfig,
    ) -> bool:
        """Export to YAML format."""
        try:
            import yaml
            path = Path(output_path)
            with open(path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False)
            return True
        except ImportError:
            # Fallback: simple YAML-like output
            def to_yaml_simple(obj: Any, indent: int = 0) -> str:
                lines = []
                prefix = "  " * indent
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if isinstance(v, (dict, list)):
                            lines.append(f"{prefix}{k}:")
                            lines.append(to_yaml_simple(v, indent + 1))
                        else:
                            lines.append(f"{prefix}{k}: {v}")
                elif isinstance(obj, list):
                    for item in obj:
                        lines.append(f"{prefix}- {item}")
                else:
                    lines.append(f"{prefix}{obj}")
                return "\n".join(lines)

            path = Path(output_path)
            path.write_text(to_yaml_simple(data))
            return True

    def _export_csv(
        self,
        output_path: str,
        data: Dict[str, Any],
        config: ExportConfig,
    ) -> bool:
        """Export to CSV format (flat key-value pairs)."""
        import csv

        # Flatten data
        flat_data = self._flatten_dict(data)

        path = Path(output_path)
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["parameter", "value"])
            for key, value in sorted(flat_data.items()):
                writer.writerow([key, value])

        return True

    def _flatten_dict(
        self,
        d: Dict[str, Any],
        parent_key: str = "",
        sep: str = ".",
    ) -> Dict[str, Any]:
        """Flatten nested dict to dot-notation keys."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep).items())
            elif isinstance(v, list):
                for i, item in enumerate(v):
                    if isinstance(item, dict):
                        items.extend(self._flatten_dict(item, f"{new_key}[{i}]", sep).items())
                    else:
                        items.append((f"{new_key}[{i}]", item))
            else:
                items.append((new_key, v))
        return dict(items)

    def export_summary(self) -> Dict[str, Any]:
        """Generate summary for quick export."""
        state_dict = _serialize_state(self.state)

        summary = {
            "generated_at": datetime.utcnow().isoformat(),
        }

        # Hull summary
        if "hull" in state_dict:
            hull = state_dict["hull"]
            summary["hull"] = {
                "loa_m": hull.get("loa"),
                "beam_m": hull.get("beam"),
                "draft_m": hull.get("draft"),
            }

        # Propulsion summary
        if "propulsion" in state_dict:
            prop = state_dict["propulsion"]
            summary["propulsion"] = {
                "power_kw": prop.get("installed_power_kw") or prop.get("total_installed_power_kw"),
                "type": prop.get("propulsion_type"),
            }

        # Stability summary
        if "stability" in state_dict:
            stab = state_dict["stability"]
            summary["stability"] = {
                "gm_m": stab.get("gm_transverse_m"),
                "gz_max": stab.get("gz_max"),
            }

        return summary
