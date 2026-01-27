"""
TASK-015: Token Efficiency via State Lens

Provide a bounded, geometry-first view of state for LLM prompts.

Rules:
- Prefer rejection over normalization: this lens must not mutate state.
- Include only what the proposer needs: geometry resources + small set of physics outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from typing import Any, Dict, Iterable, List, Optional, Tuple


DEFAULT_FOCUS_PATHS = [
    # Geometry resources (filtered further to geometry.* by _type)
    "resources",
    # Minimal hull params needed for context
    "hull.loa",
    "hull.lwl",
    "hull.beam",
    "hull.draft",
    "hull.depth",
    # Mission / speed regime (continuous)
    "mission.max_speed_kts",
    # Physics outputs that help the agent steer (continuous)
    "physics.hydrostatics",
    "physics.resistance",
]


def _get_nested(d: Dict[str, Any], path: str) -> Any:
    cur: Any = d
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        if part not in cur:
            return None
        cur = cur[part]
    return cur


def _set_nested(out: Dict[str, Any], path: str, value: Any) -> None:
    cur: Dict[str, Any] = out
    parts = path.split(".")
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    cur[parts[-1]] = value


def _matches_focus(path: str, focus: Iterable[str]) -> bool:
    for f in focus:
        # Allow both exact and wildcard matches
        if f == path:
            return True
        if "*" in f and fnmatch(path, f):
            return True
        # Treat a focus prefix like "physics.hydrostatics" as including all children
        if path.startswith(f + "."):
            return True
    return False


def _filter_geometry_resources(resources: Any) -> Dict[str, Any]:
    """
    Keep only geometry.* resources (and ignore deleted).

    State uses `resources` as {resource_id: {...}} with `_type` field.
    """
    if not isinstance(resources, dict):
        return {}

    out: Dict[str, Any] = {}
    for rid, res in resources.items():
        if not isinstance(res, dict):
            continue
        rtype = str(res.get("_type", "") or "")
        if not rtype.startswith("geometry."):
            continue
        if res.get("_deleted"):
            continue
        out[rid] = res
    return out


@dataclass(frozen=True)
class StateLens:
    """
    Extract a bounded view of state for prompt injection.
    """

    focus_paths: List[str] = None  # type: ignore[assignment]

    def extract(self, state: Dict[str, Any], focus_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        focus = focus_paths or self.focus_paths or DEFAULT_FOCUS_PATHS

        out: Dict[str, Any] = {}

        # Always include filtered geometry resources if present
        if "resources" in state and _matches_focus("resources", focus):
            out["resources"] = _filter_geometry_resources(state.get("resources"))

        # Copy requested scalar/subtrees
        for key in focus:
            if key == "resources":
                continue
            if "*" in key:
                # Wildcards are supported only for dotted paths at leaf level;
                # keep implementation minimal for auditability.
                continue
            val = _get_nested(state, key)
            if val is not None:
                _set_nested(out, key, val)

        return out


def extract_lens(state: Dict[str, Any], focus_paths: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Convenience wrapper matching the guide's intent.
    """
    return StateLens().extract(state, focus_paths=focus_paths)

