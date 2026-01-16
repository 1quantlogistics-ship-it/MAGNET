"""
§SKELETON:DesignStore

DesignStore v2: file-backed persistence for design state.

Storage format (v1): JSON per design at {root_dir}/{design_id}.json
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from magnet.core.state_manager import StateManager


class DesignNotFound(Exception):
    """Raised when a requested design is not available in the store."""
    pass


@dataclass
class VersionConflictError(Exception):
    """
    Raised when an optimistic locking check fails.

    This is the "one narrow bridge" constraint: no silent merge, no last-write-wins.
    """
    design_id: str
    expected: int
    actual: int
    message: str = "Design was modified by another request"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": "version_conflict",
            "design_id": self.design_id,
            "expected_version": self.expected,
            "actual_version": self.actual,
            "message": self.message,
        }


@dataclass
class DesignStoreConfig:
    root_dir: Path

    @classmethod
    def from_env(cls) -> "DesignStoreConfig":
        # Default: repo storage directory.
        #
        # IMPORTANT: resolve relative paths against the repo root so server CWD doesn't matter.
        #
        # Test isolation: when running under pytest, prefer a per-process store unless the
        # test explicitly set MAGNET_DESIGN_STORE_DIR. This MUST be stable across multiple
        # requests within the same process (persistence tests rely on it).
        if "PYTEST_CURRENT_TEST" in os.environ and "MAGNET_DESIGN_STORE_DIR" not in os.environ:
            key = "MAGNET_PYTEST_DESIGN_STORE_DIR"
            if key not in os.environ:
                os.environ[key] = f".pytest_artifacts/design_store_{os.getpid()}"
            base = os.environ[key]
        else:
            base = os.environ.get("MAGNET_DESIGN_STORE_DIR", "storage/designs")
        p = Path(base)
        if not p.is_absolute():
            repo_root = Path(__file__).resolve().parents[2]
            p = (repo_root / p).resolve()
        return cls(root_dir=p)


class DesignStore:
    """
    DesignStore v2: file-backed persistence for design state.

    Storage format (v1): JSON per design at {root_dir}/{design_id}.json
    
    Supports both legacy container-based resolution and new file-based persistence.
    When MAGNET_DESIGN_STORE_V2_ENABLED=true (default), uses file persistence.
    """

    def __init__(self, container: Optional[object] = None, config: Optional[DesignStoreConfig] = None):
        self._container = container
        self._config = config or DesignStoreConfig.from_env()
        self._config.root_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, design_id: str) -> Path:
        return self._config.root_dir / f"{design_id}.json"

    def _dir_for(self, design_id: str) -> Path:
        return self._config.root_dir / design_id

    def _turns_path_for(self, design_id: str) -> Path:
        return self._dir_for(design_id) / "turns.jsonl"

    def exists(self, design_id: str) -> bool:
        return self._path_for(design_id).exists()

    def list_designs(self) -> List[str]:
        return sorted(p.stem for p in self._config.root_dir.glob("*.json"))

    def get_version(self, design_id: str) -> int:
        """
        Return the persisted design_version for a design.
        """
        path = self._path_for(design_id)
        if not path.exists():
            raise DesignNotFound(f"Design {design_id} not found")
        data = json.loads(path.read_text(encoding="utf-8"))
        try:
            return int(data.get("design_version", 0) or 0)
        except Exception:
            return 0

    def save(
        self,
        design_id: str,
        state_manager: Optional[StateManager] = None,
        expected_version: Optional[int] = None,
    ) -> int:
        """
        Persist current StateManager to disk under design_id.
        MUST be atomic: write temp then os.replace().

        If expected_version is provided, enforce optimistic locking:
        - If the persisted version != expected_version → raise VersionConflictError
        - No silent merges.
        """
        sm = state_manager or self._resolve_state_manager()

        # Enforce version lock (the narrow bridge).
        if expected_version is not None:
            if self.exists(design_id):
                current = self.get_version(design_id)
            else:
                current = 0
            if int(current) != int(expected_version):
                raise VersionConflictError(
                    design_id=design_id,
                    expected=int(expected_version),
                    actual=int(current),
                )
            # Sanity check: caller must have advanced version (at least once).
            try:
                dv = int(sm.get("design_version", 0) or 0) if hasattr(sm, "get") else int(sm.state.design_version)
            except Exception:
                dv = int(sm.state.design_version) if hasattr(sm, "state") else 0
            if dv <= int(expected_version):
                raise RuntimeError(
                    f"DesignStore.save version mismatch: expected_version={expected_version} but "
                    f"state_manager.design_version={dv}. Commit before save."
                )

        data = sm.to_dict()
        out = self._path_for(design_id)
        tmp = out.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        os.replace(tmp, out)
        try:
            return int(data.get("design_version", 0) or 0)
        except Exception:
            return 0

    def load(self, design_id: str) -> StateManager:
        """
        Load design state from disk into a StateManager instance.
        """
        path = self._path_for(design_id)
        if not path.exists():
            raise DesignNotFound(f"Design {design_id} not found")
        # IMPORTANT: design loads must be isolated per design_id.
        # Do NOT reuse a container-resolved global StateManager instance here.
        sm = StateManager()
        data = json.loads(path.read_text(encoding="utf-8"))
        sm.load_from_dict(data)
        return sm

    # ==================== Turn Records (Walking Trail Contract 3) ====================

    def append_turn_record(self, design_id: str, record: Dict[str, Any]) -> None:
        """
        Append-only turn record storage (JSON Lines).

        Location: {root}/{design_id}/turns.jsonl
        """
        d = self._dir_for(design_id)
        d.mkdir(parents=True, exist_ok=True)
        turns_path = self._turns_path_for(design_id)

        obj = dict(record or {})
        obj.setdefault("design_id", design_id)
        obj.setdefault("timestamp", datetime.utcnow().isoformat())
        line = json.dumps(obj, default=str)
        with open(turns_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def get_turn_history(self, design_id: str) -> List[Dict[str, Any]]:
        turns_path = self._turns_path_for(design_id)
        if not turns_path.exists():
            return []
        out: List[Dict[str, Any]] = []
        with open(turns_path, "r", encoding="utf-8") as f:
            for line in f:
                line = (line or "").strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        out.append(obj)
                except Exception:
                    continue
        return out

    def delete(self, design_id: str) -> bool:
        path = self._path_for(design_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def _resolve_state_manager(self) -> StateManager:
        if not self._container:
            # For tests, allow creating a standalone StateManager if you have a factory.
            from magnet.core.state_manager import StateManager  # local import to avoid cycles
            return StateManager()
        return self._container.resolve(StateManager)
