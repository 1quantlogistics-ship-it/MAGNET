"""
lifecycle/manager.py - Manage design lifecycle
BRAVO OWNS THIS FILE.

Section 45: Design Lifecycle
v1.1: Uses serialize_state(), handles missing keys
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime
from pathlib import Path
import json
import uuid
import logging

from .versions import (
    DesignVersion, DesignBranch, VersionStatus,
    compute_state_hash
)

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


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


class LifecycleManager:
    """
    Manages design versioning and lifecycle.
    """

    def __init__(
        self,
        state: "StateManager",
        storage_path: str = None,
    ):
        self.state = state
        self.storage_path = Path(storage_path) if storage_path else None
        if self.storage_path:
            self.storage_path.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger("lifecycle")

        # Version storage
        self._versions: Dict[str, DesignVersion] = {}
        self._branches: Dict[str, DesignBranch] = {}

        # Current context
        self._current_branch: str = "main"

        if self.storage_path:
            self._load()

    def _load(self) -> None:
        """Load version metadata from storage."""
        if not self.storage_path:
            return
        versions_file = self.storage_path / "versions.json"
        if versions_file.exists():
            try:
                data = json.loads(versions_file.read_text())

                for v_data in data.get("versions", []):
                    # Handle status enum
                    if 'status' in v_data and isinstance(v_data['status'], str):
                        v_data['status'] = VersionStatus(v_data['status'])
                    # Handle datetime
                    if 'created_at' in v_data and isinstance(v_data['created_at'], str):
                        v_data['created_at'] = datetime.fromisoformat(v_data['created_at'])
                    version = DesignVersion(**{k: v for k, v in v_data.items()
                                              if k in DesignVersion.__dataclass_fields__})
                    self._versions[version.version_id] = version

                for b_data in data.get("branches", []):
                    # Handle datetime
                    if 'created_at' in b_data and isinstance(b_data['created_at'], str):
                        b_data['created_at'] = datetime.fromisoformat(b_data['created_at'])
                    branch = DesignBranch(**{k: v for k, v in b_data.items()
                                            if k in DesignBranch.__dataclass_fields__})
                    self._branches[branch.branch_id] = branch
            except Exception as e:
                self.logger.error(f"Failed to load versions: {e}")

    def _save(self) -> None:
        """Save version metadata to storage."""
        if not self.storage_path:
            return
        data = {
            "versions": [v.to_dict() for v in self._versions.values()],
            "branches": [b.to_dict() for b in self._branches.values()],
        }

        versions_file = self.storage_path / "versions.json"
        versions_file.write_text(json.dumps(data, indent=2, default=str))

    def _get_head_version(self) -> Optional[DesignVersion]:
        """Get head version of current branch."""
        branch = self._branches.get(self._current_branch)
        if branch and branch.head_version_id:
            return self._versions.get(branch.head_version_id)
        # Return most recent version
        if self._versions:
            return max(self._versions.values(), key=lambda v: v.created_at)
        return None

    def create_version(
        self,
        description: str = "",
        changes: List[str] = None,
        bump: str = "patch",  # major, minor, patch
    ) -> DesignVersion:
        """
        Create a new version from current state.

        v1.1: Uses serialize_state() helper.
        """
        # v1.1: Use helper for state serialization
        state_dict = _serialize_state(self.state)

        # Compute hash
        state_hash = compute_state_hash(state_dict)

        # Get parent version
        parent = self._get_head_version()

        # Calculate new version number
        if parent:
            major, minor, patch = parent.major, parent.minor, parent.patch
            if bump == "major":
                major += 1
                minor = 0
                patch = 0
            elif bump == "minor":
                minor += 1
                patch = 0
            else:
                patch += 1
        else:
            major, minor, patch = 0, 1, 0

        # Create version
        version_id = str(uuid.uuid4())[:8]
        version = DesignVersion(
            version_id=version_id,
            major=major,
            minor=minor,
            patch=patch,
            status=VersionStatus.DRAFT,
            description=description,
            changes=changes or [],
            state_hash=state_hash,
            parent_version_id=parent.version_id if parent else None,
        )

        # Save snapshot
        if self.storage_path:
            snapshot_path = self.storage_path / f"v{version.version_string}_{version_id}.json"
            snapshot_path.write_text(json.dumps(state_dict, indent=2, default=str))
            version.snapshot_path = str(snapshot_path)

        # Store
        self._versions[version_id] = version

        # Update branch head
        if self._current_branch in self._branches:
            self._branches[self._current_branch].head_version_id = version_id

        self._save()

        self.logger.info(f"Created version {version.version_string}")

        return version

    def get_version(self, version_id: str) -> Optional[DesignVersion]:
        """Get a version by ID."""
        return self._versions.get(version_id)

    def get_version_by_string(self, version_string: str) -> Optional[DesignVersion]:
        """Get version by string (e.g., '1.2.3')."""
        for version in self._versions.values():
            if version.version_string == version_string:
                return version
        return None

    def list_versions(self, limit: int = 20) -> List[DesignVersion]:
        """List versions, most recent first."""
        versions = sorted(
            self._versions.values(),
            key=lambda v: v.created_at,
            reverse=True,
        )
        return versions[:limit]

    def load_version(self, version_id: str) -> bool:
        """Load a version's state."""
        version = self._versions.get(version_id)
        if not version or not version.snapshot_path:
            return False

        try:
            snapshot_path = Path(version.snapshot_path)
            if not snapshot_path.exists():
                return False

            state_dict = json.loads(snapshot_path.read_text())

            if hasattr(self.state, 'load_from_dict'):
                self.state.load_from_dict(state_dict)
                return True

            return False
        except Exception as e:
            self.logger.error(f"Failed to load version {version_id}: {e}")
            return False

    def update_status(
        self,
        version_id: str,
        new_status: VersionStatus,
    ) -> bool:
        """Update version status."""
        version = self._versions.get(version_id)
        if not version:
            return False

        version.status = new_status
        self._save()

        return True

    def create_branch(
        self,
        name: str,
        description: str = "",
        branch_type: str = "feature",
    ) -> DesignBranch:
        """Create a new branch."""
        head = self._get_head_version()

        branch = DesignBranch(
            branch_id=str(uuid.uuid4())[:8],
            name=name,
            description=description,
            base_version_id=head.version_id if head else "",
            head_version_id=head.version_id if head else "",
            branch_type=branch_type,
        )

        self._branches[branch.branch_id] = branch
        self._save()

        return branch

    def switch_branch(self, branch_name: str) -> bool:
        """Switch to a different branch."""
        for branch in self._branches.values():
            if branch.name == branch_name:
                self._current_branch = branch.branch_id
                # Load head version
                if branch.head_version_id:
                    self.load_version(branch.head_version_id)
                return True
        return False

    def get_current_branch(self) -> Optional[DesignBranch]:
        """Get current branch."""
        return self._branches.get(self._current_branch)

    def list_branches(self) -> List[DesignBranch]:
        """List all branches."""
        return list(self._branches.values())

    def compare_versions(
        self,
        version_a_id: str,
        version_b_id: str,
    ) -> Dict[str, Any]:
        """Compare two versions."""
        version_a = self._versions.get(version_a_id)
        version_b = self._versions.get(version_b_id)

        if not version_a or not version_b:
            return {"error": "Version not found"}

        return {
            "version_a": version_a.version_string,
            "version_b": version_b.version_string,
            "same_hash": version_a.state_hash == version_b.state_hash,
            "version_a_status": version_a.status.value,
            "version_b_status": version_b.status.value,
        }
