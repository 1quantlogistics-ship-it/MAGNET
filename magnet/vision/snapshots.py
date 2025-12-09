"""
vision/snapshots.py - Snapshot management v1.1
BRAVO OWNS THIS FILE.

Section 52: Vision Subsystem
Manages visual snapshots for reports and UI.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime, timezone
from pathlib import Path
from enum import Enum
import uuid
import json
import logging

from magnet.ui.utils import snapshot_registry

if TYPE_CHECKING:
    from .geometry import Mesh
    from .renderer import Snapshot

logger = logging.getLogger("vision.snapshots")


class SnapshotFormat(Enum):
    """Supported snapshot image formats."""
    PNG = "png"
    JPEG = "jpeg"
    SVG = "svg"
    PDF = "pdf"


class SnapshotQuality(Enum):
    """Snapshot quality presets."""
    THUMBNAIL = "thumbnail"   # 256x192
    PREVIEW = "preview"       # 512x384
    STANDARD = "standard"     # 1024x768
    HIGH = "high"             # 2048x1536
    PRINT = "print"           # 4096x3072


QUALITY_DIMENSIONS = {
    SnapshotQuality.THUMBNAIL: (256, 192),
    SnapshotQuality.PREVIEW: (512, 384),
    SnapshotQuality.STANDARD: (1024, 768),
    SnapshotQuality.HIGH: (2048, 1536),
    SnapshotQuality.PRINT: (4096, 3072),
}


@dataclass
class SnapshotConfig:
    """Configuration for snapshot generation."""
    width: int = 1024
    height: int = 768
    format: SnapshotFormat = SnapshotFormat.PNG
    quality: SnapshotQuality = SnapshotQuality.STANDARD
    background_color: str = "#FFFFFF"
    transparent: bool = False
    antialiasing: bool = True
    dpi: int = 150

    @classmethod
    def from_quality(cls, quality: SnapshotQuality) -> "SnapshotConfig":
        """Create config from quality preset."""
        width, height = QUALITY_DIMENSIONS.get(quality, (1024, 768))
        return cls(width=width, height=height, quality=quality)

    @classmethod
    def for_report(cls) -> "SnapshotConfig":
        """Create config suitable for reports."""
        return cls(
            width=1200,
            height=900,
            format=SnapshotFormat.PNG,
            quality=SnapshotQuality.HIGH,
            dpi=300,
        )

    @classmethod
    def for_thumbnail(cls) -> "SnapshotConfig":
        """Create config for thumbnails."""
        return cls(
            width=256,
            height=192,
            format=SnapshotFormat.PNG,
            quality=SnapshotQuality.THUMBNAIL,
            antialiasing=False,
        )


@dataclass
class SnapshotMetadata:
    """Metadata for a snapshot."""
    snapshot_id: str = ""
    section_id: str = ""
    phase: str = ""
    view: str = "perspective"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    design_id: str = ""
    version: str = ""

    # File info
    file_path: Optional[str] = None
    file_size: int = 0
    width: int = 0
    height: int = 0
    format: str = "png"

    # Content info
    title: str = ""
    caption: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "section_id": self.section_id,
            "phase": self.phase,
            "view": self.view,
            "created_at": self.created_at.isoformat(),
            "design_id": self.design_id,
            "file_path": self.file_path,
            "width": self.width,
            "height": self.height,
            "format": self.format,
            "title": self.title,
            "caption": self.caption,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SnapshotMetadata":
        meta = cls()
        for key, value in data.items():
            if hasattr(meta, key):
                if key == "created_at" and isinstance(value, str):
                    value = datetime.fromisoformat(value)
                setattr(meta, key, value)
        return meta


class SnapshotManager:
    """
    Manages snapshot creation, storage, and retrieval.

    v1.1: Integrates with global SnapshotRegistry for report access.
    """

    def __init__(self, output_dir: str = "/tmp/magnet_snapshots"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._snapshots: Dict[str, SnapshotMetadata] = {}
        self._by_phase: Dict[str, List[str]] = {}
        self._by_section: Dict[str, str] = {}

        # Load existing metadata
        self._load_metadata()

    def _load_metadata(self) -> None:
        """Load snapshot metadata from storage."""
        meta_file = self.output_dir / "snapshots.json"
        if meta_file.exists():
            try:
                data = json.loads(meta_file.read_text())
                for snap_data in data.get("snapshots", []):
                    meta = SnapshotMetadata.from_dict(snap_data)
                    self._snapshots[meta.snapshot_id] = meta
                    self._index_snapshot(meta)
            except Exception as e:
                logger.error(f"Failed to load snapshot metadata: {e}")

    def _save_metadata(self) -> None:
        """Save snapshot metadata to storage."""
        meta_file = self.output_dir / "snapshots.json"
        data = {
            "snapshots": [s.to_dict() for s in self._snapshots.values()],
        }
        meta_file.write_text(json.dumps(data, indent=2, default=str))

    def _index_snapshot(self, meta: SnapshotMetadata) -> None:
        """Index snapshot for quick lookup."""
        if meta.phase:
            if meta.phase not in self._by_phase:
                self._by_phase[meta.phase] = []
            if meta.snapshot_id not in self._by_phase[meta.phase]:
                self._by_phase[meta.phase].append(meta.snapshot_id)

        if meta.section_id:
            self._by_section[meta.section_id] = meta.snapshot_id

    def create_snapshot(
        self,
        renderer: Any,
        mesh: "Mesh",
        section_id: str,
        phase: str = "",
        view: str = "perspective",
        config: Optional[SnapshotConfig] = None,
        design_id: str = "",
        title: str = "",
        caption: str = "",
    ) -> SnapshotMetadata:
        """
        Create a new snapshot.

        Args:
            renderer: Renderer instance
            mesh: Mesh to render
            section_id: Unique section identifier for reports
            phase: Design phase name
            view: View angle name
            config: Snapshot configuration
            design_id: Design identifier
            title: Snapshot title
            caption: Snapshot caption

        Returns:
            SnapshotMetadata for the created snapshot
        """
        config = config or SnapshotConfig()
        snapshot_id = str(uuid.uuid4())[:8]

        # Generate filename
        filename = f"{section_id}_{snapshot_id}.{config.format.value}"
        file_path = self.output_dir / filename

        # Create metadata
        meta = SnapshotMetadata(
            snapshot_id=snapshot_id,
            section_id=section_id,
            phase=phase,
            view=view,
            design_id=design_id,
            file_path=str(file_path),
            width=config.width,
            height=config.height,
            format=config.format.value,
            title=title or f"{phase} - {view}".title(),
            caption=caption,
        )

        # Render snapshot
        try:
            from .renderer import ViewAngle

            try:
                view_angle = ViewAngle(view)
            except ValueError:
                view_angle = ViewAngle.PERSPECTIVE

            snapshots = renderer.render_views(
                mesh,
                views=[view_angle],
                output_dir=str(self.output_dir),
                width=config.width,
                height=config.height,
            )

            if snapshots and snapshots[0].image_path:
                # Rename to our standard filename
                actual_path = Path(snapshots[0].image_path)
                if actual_path.exists() and actual_path != file_path:
                    actual_path.rename(file_path)

                meta.file_size = file_path.stat().st_size if file_path.exists() else 0

        except Exception as e:
            logger.error(f"Snapshot render failed: {e}")
            # Create placeholder
            self._create_placeholder(file_path, config)

        # Store and index
        self._snapshots[snapshot_id] = meta
        self._index_snapshot(meta)

        # Register with global registry for reports
        if meta.file_path:
            snapshot_registry.register(section_id, meta.file_path, phase)

        self._save_metadata()

        logger.info(f"Created snapshot {snapshot_id} for {section_id}")
        return meta

    def _create_placeholder(self, path: Path, config: SnapshotConfig) -> None:
        """Create a placeholder image when rendering fails."""
        try:
            from PIL import Image, ImageDraw

            img = Image.new('RGB', (config.width, config.height), config.background_color)
            draw = ImageDraw.Draw(img)

            # Draw placeholder text
            text = "Snapshot Unavailable"
            draw.text((config.width // 2 - 80, config.height // 2), text, fill="#999999")

            img.save(str(path))

        except ImportError:
            # Create minimal file
            path.write_bytes(b"")

    def get_snapshot(self, snapshot_id: str) -> Optional[SnapshotMetadata]:
        """Get snapshot by ID."""
        return self._snapshots.get(snapshot_id)

    def get_by_section(self, section_id: str) -> Optional[SnapshotMetadata]:
        """Get snapshot by section ID."""
        snap_id = self._by_section.get(section_id)
        if snap_id:
            return self._snapshots.get(snap_id)
        return None

    def get_for_phase(self, phase: str) -> List[SnapshotMetadata]:
        """Get all snapshots for a phase."""
        snap_ids = self._by_phase.get(phase, [])
        return [self._snapshots[sid] for sid in snap_ids if sid in self._snapshots]

    def get_all(self) -> List[SnapshotMetadata]:
        """Get all snapshots."""
        return list(self._snapshots.values())

    def get_paths_for_report(self, sections: List[str] = None) -> Dict[str, str]:
        """
        Get snapshot paths for report sections.

        v1.1: Also checks global snapshot registry.
        """
        result = {}

        if sections:
            for section in sections:
                # Check local first
                meta = self.get_by_section(section)
                if meta and meta.file_path:
                    result[section] = meta.file_path
                else:
                    # Check global registry
                    path = snapshot_registry.get(section)
                    if path:
                        result[section] = path
        else:
            # Return all
            for section_id, snap_id in self._by_section.items():
                meta = self._snapshots.get(snap_id)
                if meta and meta.file_path:
                    result[section_id] = meta.file_path

            # Merge with global registry
            result.update(snapshot_registry.get_all())

        return result

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot."""
        meta = self._snapshots.get(snapshot_id)
        if not meta:
            return False

        # Delete file
        if meta.file_path:
            path = Path(meta.file_path)
            if path.exists():
                path.unlink()

        # Remove from indexes
        if meta.phase and meta.phase in self._by_phase:
            self._by_phase[meta.phase] = [
                sid for sid in self._by_phase[meta.phase] if sid != snapshot_id
            ]

        if meta.section_id and meta.section_id in self._by_section:
            del self._by_section[meta.section_id]

        del self._snapshots[snapshot_id]
        self._save_metadata()

        return True

    def clear_phase(self, phase: str) -> int:
        """Delete all snapshots for a phase."""
        count = 0
        snap_ids = list(self._by_phase.get(phase, []))
        for snap_id in snap_ids:
            if self.delete_snapshot(snap_id):
                count += 1
        return count

    def clear_all(self) -> int:
        """Delete all snapshots."""
        count = len(self._snapshots)
        for snap_id in list(self._snapshots.keys()):
            self.delete_snapshot(snap_id)
        return count


# Default snapshot manager instance
_default_manager: Optional[SnapshotManager] = None


def get_snapshot_manager(output_dir: str = None) -> SnapshotManager:
    """Get or create the default snapshot manager."""
    global _default_manager
    if _default_manager is None or output_dir:
        _default_manager = SnapshotManager(output_dir or "/tmp/magnet_snapshots")
    return _default_manager
