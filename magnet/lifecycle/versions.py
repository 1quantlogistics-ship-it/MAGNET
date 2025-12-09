"""
lifecycle/versions.py - Design version management
BRAVO OWNS THIS FILE.

Section 45: Design Lifecycle
v1.1: Deterministic hashes, missing key handling
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
import hashlib
import json


class VersionStatus(Enum):
    """Status of a design version."""
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    RELEASED = "released"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


@dataclass
class DesignVersion:
    """Represents a version of the design."""

    version_id: str = ""

    # Semantic version
    major: int = 0
    minor: int = 0
    patch: int = 0

    status: VersionStatus = VersionStatus.DRAFT

    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""

    # Description
    description: str = ""
    changes: List[str] = field(default_factory=list)

    # State hash for change detection
    state_hash: str = ""

    # Parent version
    parent_version_id: Optional[str] = None

    # State snapshot path (not embedded)
    snapshot_path: Optional[str] = None

    @property
    def version_string(self) -> str:
        """Get version string (e.g., '1.2.3')."""
        return f"{self.major}.{self.minor}.{self.patch}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "version": self.version_string,
            "major": self.major,
            "minor": self.minor,
            "patch": self.patch,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "description": self.description,
            "state_hash": self.state_hash,
            "parent_version_id": self.parent_version_id,
        }


@dataclass
class DesignBranch:
    """A branch of design development."""

    branch_id: str = ""
    name: str = ""

    description: str = ""

    # Base version
    base_version_id: str = ""

    # Current version on this branch
    head_version_id: str = ""

    created_at: datetime = field(default_factory=datetime.utcnow)

    # Branch type
    branch_type: str = "feature"  # main, feature, exploration

    def to_dict(self) -> Dict[str, Any]:
        return {
            "branch_id": self.branch_id,
            "name": self.name,
            "base_version": self.base_version_id,
            "head_version": self.head_version_id,
            "type": self.branch_type,
        }


# v1.1: Fields to exclude from hash (timestamps cause nondeterminism)
HASH_EXCLUDE_FIELDS = {
    "created_at",
    "updated_at",
    "timestamp",
    "last_modified",
    "version_id",
    "snapshot_path",
}


def compute_state_hash(state: Dict[str, Any]) -> str:
    """
    Compute deterministic hash of state.

    v1.1: Excludes timestamp fields for determinism.
    """
    def clean_for_hash(obj: Any, parent_key: str = "") -> Any:
        """Remove timestamp fields recursively."""
        if isinstance(obj, dict):
            return {
                k: clean_for_hash(v, k)
                for k, v in sorted(obj.items())
                if k not in HASH_EXCLUDE_FIELDS
            }
        elif isinstance(obj, list):
            return [clean_for_hash(item) for item in obj]
        elif isinstance(obj, datetime):
            # v1.1: Convert datetime to ISO string for consistency
            return obj.isoformat()
        else:
            return obj

    cleaned = clean_for_hash(state)
    json_str = json.dumps(cleaned, sort_keys=True, default=str)

    return hashlib.sha256(json_str.encode()).hexdigest()[:16]
