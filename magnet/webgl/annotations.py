"""
webgl/annotations.py - 3D Annotation persistence v1.1
BRAVO OWNS THIS FILE.

Module 58: WebGL 3D Visualization
Provides annotation storage and decision log integration.
Addresses: FM6 (Annotations not persisted)

Features:
- Annotation3D schema with measurements
- Persistence to design state
- Decision log integration
- Phase filtering
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
import uuid
import json

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger("webgl.annotations")


# =============================================================================
# ENUMS
# =============================================================================

class AnnotationCategory(Enum):
    """Annotation categories."""
    GENERAL = "general"
    MEASUREMENT = "measurement"
    ISSUE = "issue"
    NOTE = "note"
    QUESTION = "question"
    DECISION = "decision"


class MeasurementType(Enum):
    """3D measurement types."""
    DISTANCE = "distance"
    ANGLE = "angle"
    AREA = "area"
    VOLUME = "volume"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Measurement3D:
    """
    3D measurement data.

    Stores measurement geometry and computed value.
    """
    type: MeasurementType
    points: List[Tuple[float, float, float]]
    value: float
    unit: str = "m"
    precision: int = 2

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "points": [list(p) for p in self.points],
            "value": self.value,
            "unit": self.unit,
            "precision": self.precision,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Measurement3D":
        return cls(
            type=MeasurementType(data.get("type", "distance")),
            points=[tuple(p) for p in data.get("points", [])],
            value=data.get("value", 0.0),
            unit=data.get("unit", "m"),
            precision=data.get("precision", 2),
        )

    @property
    def formatted_value(self) -> str:
        """Get formatted measurement value with unit."""
        return f"{self.value:.{self.precision}f} {self.unit}"


@dataclass
class Annotation3D:
    """
    3D annotation with optional measurement.

    v1.1: Persistence and decision log integration (FM6)
    """
    # Identification
    annotation_id: str = ""
    design_id: str = ""

    # Position in 3D space
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    normal: Optional[Tuple[float, float, float]] = None  # Surface normal at annotation point

    # Content
    label: str = ""
    description: str = ""
    category: AnnotationCategory = AnnotationCategory.GENERAL

    # Measurement (optional)
    measurement: Optional[Measurement3D] = None

    # Metadata
    created_by: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

    # Integration
    linked_decision_id: Optional[str] = None
    linked_phase: Optional[str] = None
    linked_component: Optional[str] = None  # e.g., "hull", "deck", "frame_5"

    # Visibility
    visible: bool = True
    color: str = "#ffffff"
    icon: str = "pin"  # pin, measurement, warning, question, note

    def __post_init__(self):
        if not self.annotation_id:
            self.annotation_id = str(uuid.uuid4())[:12]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "annotation_id": self.annotation_id,
            "design_id": self.design_id,
            "position": list(self.position),
            "normal": list(self.normal) if self.normal else None,
            "label": self.label,
            "description": self.description,
            "category": self.category.value,
            "measurement": self.measurement.to_dict() if self.measurement else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "linked_decision_id": self.linked_decision_id,
            "linked_phase": self.linked_phase,
            "linked_component": self.linked_component,
            "visible": self.visible,
            "color": self.color,
            "icon": self.icon,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Annotation3D":
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        else:
            created_at = datetime.now(timezone.utc)

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

        measurement = None
        if data.get("measurement"):
            measurement = Measurement3D.from_dict(data["measurement"])

        return cls(
            annotation_id=data.get("annotation_id", ""),
            design_id=data.get("design_id", ""),
            position=tuple(data.get("position", [0, 0, 0])),
            normal=tuple(data["normal"]) if data.get("normal") else None,
            label=data.get("label", ""),
            description=data.get("description", ""),
            category=AnnotationCategory(data.get("category", "general")),
            measurement=measurement,
            created_by=data.get("created_by", ""),
            created_at=created_at,
            updated_at=updated_at,
            linked_decision_id=data.get("linked_decision_id"),
            linked_phase=data.get("linked_phase"),
            linked_component=data.get("linked_component"),
            visible=data.get("visible", True),
            color=data.get("color", "#ffffff"),
            icon=data.get("icon", "pin"),
        )


# =============================================================================
# ANNOTATION STORE
# =============================================================================

class AnnotationStore:
    """
    Annotation storage and retrieval.

    v1.1: Persists to design state and integrates with decision log.
    """

    def __init__(self, state_manager: Optional["StateManager"] = None):
        self._state_manager = state_manager
        self._annotations: Dict[str, Dict[str, Annotation3D]] = {}  # design_id -> {annotation_id -> Annotation3D}

    def _get_design_annotations(self, design_id: str) -> Dict[str, Annotation3D]:
        """Get or create annotation dict for design."""
        if design_id not in self._annotations:
            self._annotations[design_id] = {}
            # Try to load from state manager
            if self._state_manager:
                self._load_from_state(design_id)
        return self._annotations[design_id]

    def _load_from_state(self, design_id: str) -> None:
        """Load annotations from state manager."""
        if not self._state_manager:
            return

        try:
            annotations_data = self._state_manager.get(f"visualization.annotations.{design_id}", [])
            if isinstance(annotations_data, list):
                for ann_data in annotations_data:
                    ann = Annotation3D.from_dict(ann_data)
                    self._annotations[design_id][ann.annotation_id] = ann
                logger.debug(f"Loaded {len(annotations_data)} annotations for {design_id}")
        except Exception as e:
            logger.warning(f"Failed to load annotations for {design_id}: {e}")

    def _save_to_state(self, design_id: str) -> None:
        """Save annotations to state manager."""
        if not self._state_manager:
            return

        try:
            annotations = list(self._annotations.get(design_id, {}).values())
            annotations_data = [ann.to_dict() for ann in annotations]
            self._state_manager.set(f"visualization.annotations.{design_id}", annotations_data)
            logger.debug(f"Saved {len(annotations_data)} annotations for {design_id}")
        except Exception as e:
            logger.warning(f"Failed to save annotations for {design_id}: {e}")

    def create(self, annotation: Annotation3D) -> Annotation3D:
        """Create a new annotation."""
        design_annotations = self._get_design_annotations(annotation.design_id)

        # Ensure unique ID
        if not annotation.annotation_id:
            annotation.annotation_id = str(uuid.uuid4())[:12]
        while annotation.annotation_id in design_annotations:
            annotation.annotation_id = str(uuid.uuid4())[:12]

        design_annotations[annotation.annotation_id] = annotation
        self._save_to_state(annotation.design_id)

        logger.info(f"Created annotation {annotation.annotation_id} for {annotation.design_id}")
        return annotation

    def get(self, design_id: str, annotation_id: str) -> Optional[Annotation3D]:
        """Get annotation by ID."""
        design_annotations = self._get_design_annotations(design_id)
        return design_annotations.get(annotation_id)

    def list(
        self,
        design_id: str,
        phase_filter: Optional[str] = None,
        category_filter: Optional[AnnotationCategory] = None,
        component_filter: Optional[str] = None,
        visible_only: bool = False,
    ) -> List[Annotation3D]:
        """List annotations for a design with optional filters."""
        design_annotations = self._get_design_annotations(design_id)
        results = list(design_annotations.values())

        if phase_filter:
            results = [a for a in results if a.linked_phase == phase_filter]

        if category_filter:
            results = [a for a in results if a.category == category_filter]

        if component_filter:
            results = [a for a in results if a.linked_component == component_filter]

        if visible_only:
            results = [a for a in results if a.visible]

        # Sort by creation time (newest first)
        results.sort(key=lambda a: a.created_at, reverse=True)

        return results

    def update(self, annotation: Annotation3D) -> Optional[Annotation3D]:
        """Update an existing annotation."""
        design_annotations = self._get_design_annotations(annotation.design_id)

        if annotation.annotation_id not in design_annotations:
            return None

        annotation.updated_at = datetime.now(timezone.utc)
        design_annotations[annotation.annotation_id] = annotation
        self._save_to_state(annotation.design_id)

        logger.info(f"Updated annotation {annotation.annotation_id}")
        return annotation

    def delete(self, design_id: str, annotation_id: str) -> bool:
        """Delete an annotation."""
        design_annotations = self._get_design_annotations(design_id)

        if annotation_id not in design_annotations:
            return False

        del design_annotations[annotation_id]
        self._save_to_state(design_id)

        logger.info(f"Deleted annotation {annotation_id} from {design_id}")
        return True

    def delete_all(self, design_id: str) -> int:
        """Delete all annotations for a design."""
        design_annotations = self._get_design_annotations(design_id)
        count = len(design_annotations)

        design_annotations.clear()
        self._save_to_state(design_id)

        logger.info(f"Deleted {count} annotations from {design_id}")
        return count

    def link_to_decision(
        self,
        design_id: str,
        annotation_id: str,
        decision_id: str,
    ) -> Optional[Annotation3D]:
        """Link annotation to a decision log entry."""
        annotation = self.get(design_id, annotation_id)
        if not annotation:
            return None

        annotation.linked_decision_id = decision_id
        annotation.updated_at = datetime.now(timezone.utc)
        self._save_to_state(design_id)

        logger.info(f"Linked annotation {annotation_id} to decision {decision_id}")
        return annotation

    def get_measurements(
        self,
        design_id: str,
        measurement_type: Optional[MeasurementType] = None,
    ) -> List[Annotation3D]:
        """Get all measurement annotations."""
        annotations = self.list(
            design_id,
            category_filter=AnnotationCategory.MEASUREMENT,
        )

        if measurement_type:
            annotations = [
                a for a in annotations
                if a.measurement and a.measurement.type == measurement_type
            ]

        return annotations

    def export_to_json(self, design_id: str) -> str:
        """Export all annotations to JSON."""
        annotations = self.list(design_id)
        return json.dumps(
            [a.to_dict() for a in annotations],
            indent=2,
        )

    def import_from_json(self, design_id: str, json_data: str) -> int:
        """Import annotations from JSON."""
        data = json.loads(json_data)
        count = 0

        for ann_data in data:
            ann = Annotation3D.from_dict(ann_data)
            ann.design_id = design_id
            ann.annotation_id = ""  # Generate new ID
            self.create(ann)
            count += 1

        return count


# =============================================================================
# GLOBAL STORE
# =============================================================================

_annotation_store: Optional[AnnotationStore] = None


def get_annotation_store(state_manager: Optional["StateManager"] = None) -> AnnotationStore:
    """Get global annotation store."""
    global _annotation_store
    if _annotation_store is None:
        _annotation_store = AnnotationStore(state_manager)
    return _annotation_store


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_distance_measurement(
    design_id: str,
    point1: Tuple[float, float, float],
    point2: Tuple[float, float, float],
    label: str = "",
    created_by: str = "",
) -> Annotation3D:
    """Create a distance measurement annotation."""
    import math

    distance = math.sqrt(
        (point2[0] - point1[0]) ** 2 +
        (point2[1] - point1[1]) ** 2 +
        (point2[2] - point1[2]) ** 2
    )

    # Position at midpoint
    midpoint = (
        (point1[0] + point2[0]) / 2,
        (point1[1] + point2[1]) / 2,
        (point1[2] + point2[2]) / 2,
    )

    measurement = Measurement3D(
        type=MeasurementType.DISTANCE,
        points=[point1, point2],
        value=distance,
        unit="m",
    )

    return Annotation3D(
        design_id=design_id,
        position=midpoint,
        label=label or f"Distance: {distance:.2f} m",
        category=AnnotationCategory.MEASUREMENT,
        measurement=measurement,
        created_by=created_by,
        icon="measurement",
        color="#00ff00",
    )


def create_angle_measurement(
    design_id: str,
    vertex: Tuple[float, float, float],
    point1: Tuple[float, float, float],
    point2: Tuple[float, float, float],
    label: str = "",
    created_by: str = "",
) -> Annotation3D:
    """Create an angle measurement annotation."""
    import math

    # Calculate vectors
    v1 = (point1[0] - vertex[0], point1[1] - vertex[1], point1[2] - vertex[2])
    v2 = (point2[0] - vertex[0], point2[1] - vertex[1], point2[2] - vertex[2])

    # Calculate angle using dot product
    dot = v1[0]*v2[0] + v1[1]*v2[1] + v1[2]*v2[2]
    mag1 = math.sqrt(v1[0]**2 + v1[1]**2 + v1[2]**2)
    mag2 = math.sqrt(v2[0]**2 + v2[1]**2 + v2[2]**2)

    if mag1 > 0 and mag2 > 0:
        cos_angle = max(-1.0, min(1.0, dot / (mag1 * mag2)))
        angle = math.degrees(math.acos(cos_angle))
    else:
        angle = 0.0

    measurement = Measurement3D(
        type=MeasurementType.ANGLE,
        points=[vertex, point1, point2],
        value=angle,
        unit="deg",
        precision=1,
    )

    return Annotation3D(
        design_id=design_id,
        position=vertex,
        label=label or f"Angle: {angle:.1f}°",
        category=AnnotationCategory.MEASUREMENT,
        measurement=measurement,
        created_by=created_by,
        icon="measurement",
        color="#ffff00",
    )
