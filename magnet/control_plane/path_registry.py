"""
MAGNET Control Plane v1.1 — Path Registry

Authoritative metadata for all refinable paths, derived from REFINABLE_SCHEMA.

This is the source of truth for:
- Path → label/description/unit mapping
- Alias generation (synonyms, labels, path segments)
- Path validation (reject hallucinated paths)
- "What is X?" (define intent) responses

The registry is generated, not hand-maintained. Manual overrides go in synonyms.yaml.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, FrozenSet
from pathlib import Path
import logging
import yaml

logger = logging.getLogger("control_plane.path_registry")


# =============================================================================
# PATH METADATA
# =============================================================================

@dataclass(frozen=True)
class PathMetadata:
    """
    Authoritative metadata for a refinable path.
    
    This is the single source of truth for what a path means,
    how to refer to it, and what it affects.
    """
    path: str                           # "hull.beam"
    label: str                          # "Beam"
    description: str                    # "Maximum breadth of the hull"
    unit: Optional[str]                 # "m"
    group: str                          # "hull"
    is_primary: bool                    # True = user-settable
    is_derived: bool                    # True = computed from other values
    synonyms: Tuple[str, ...]           # ("width", "breadth", "b")
    min_value: Optional[float] = None   # Bounds
    max_value: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "path": self.path,
            "label": self.label,
            "description": self.description,
            "unit": self.unit,
            "group": self.group,
            "is_primary": self.is_primary,
            "is_derived": self.is_derived,
            "synonyms": list(self.synonyms),
            "min_value": self.min_value,
            "max_value": self.max_value,
        }


# =============================================================================
# DEFAULT SYNONYMS (embedded, augmented by synonyms.yaml if present)
# =============================================================================

DEFAULT_SYNONYMS: Dict[str, List[str]] = {
    # Hull dimensions
    "hull.beam": ["width", "breadth", "b", "beam width", "hull width"],
    "hull.loa": ["length", "overall length", "loa", "hull length"],
    "hull.lwl": ["waterline length", "lwl", "length waterline"],
    "hull.draft": ["draft", "draught", "d", "hull draft"],
    "hull.depth": ["depth", "hull depth", "d", "moulded depth"],
    "hull.freeboard_m": ["freeboard", "fb"],
    
    # Form coefficients
    "hull.cb": ["block coefficient", "cb", "block coeff"],
    "hull.cp": ["prismatic coefficient", "cp", "prismatic", "prismatic coeff"],
    "hull.cm": ["midship coefficient", "cm", "midship coeff"],
    "hull.cwp": ["waterplane coefficient", "cwp", "waterplane coeff"],
    
    # Hull form
    "hull.deadrise_deg": ["deadrise", "deadrise angle", "bottom angle"],
    "hull.lcb_fraction": ["lcb", "longitudinal center of buoyancy"],
    "hull.transom_beam_ratio": ["transom ratio", "transom width ratio"],
    
    # Displacement & hydrostatics
    "hull.displacement_m3": ["displacement", "volume", "displaced volume"],
    "hull.displacement_mt": ["displacement tonnes", "weight"],
    "hull.wetted_surface_m2": ["wetted surface", "wetted area", "wsa"],
    "hull.waterplane_area_m2": ["waterplane area", "wpa"],
    
    # Stability
    "stability.gm_m": ["gm", "metacentric height", "gm transverse", "stability"],
    "stability.kb_m": ["kb", "center of buoyancy", "vcb"],
    "stability.bm_m": ["bm", "metacentric radius"],
    "stability.km_m": ["km", "height of metacenter"],
    
    # Mission
    "mission.max_speed_kts": ["max speed", "top speed", "maximum speed"],
    "mission.cruise_speed_kts": ["cruise speed", "cruising speed", "service speed"],
    "mission.range_nm": ["range", "endurance", "nautical miles"],
    "mission.crew_berthed": ["crew", "crew size", "manning"],
    "mission.passengers": ["passengers", "pax", "passenger capacity"],
    
    # Propulsion
    "propulsion.total_installed_power_kw": ["power", "installed power", "engine power", "kw"],
}


# =============================================================================
# PATH REGISTRY
# =============================================================================

class PathRegistry:
    """
    Registry of all refinable paths with metadata.
    
    Generated from REFINABLE_SCHEMA, augmented with synonyms.
    """
    
    def __init__(self):
        self._paths: Dict[str, PathMetadata] = {}
        self._alias_index: Dict[str, str] = {}  # alias → path
        self._groups: Dict[str, List[str]] = {}  # group → paths
        self._loaded = False
    
    def load(self) -> None:
        """Load registry from REFINABLE_SCHEMA."""
        if self._loaded:
            return
        
        try:
            from magnet.core.refinable_schema import REFINABLE_SCHEMA
        except ImportError:
            logger.warning("REFINABLE_SCHEMA not available, using minimal registry")
            self._build_minimal_registry()
            return
        
        # Build from schema
        for path, spec in REFINABLE_SCHEMA.items():
            self._register_path(path, spec)
        
        # Load synonym overrides
        self._load_synonym_overrides()
        
        # Build alias index
        self._build_alias_index()
        
        # Build group index
        self._build_group_index()
        
        self._loaded = True
        logger.info(f"PathRegistry loaded: {len(self._paths)} paths, {len(self._alias_index)} aliases")
    
    def _register_path(self, path: str, spec) -> None:
        """Register a single path from schema spec.
        
        Args:
            path: The state path (e.g., "hull.beam")
            spec: Either a dict or a RefinableField dataclass
        """
        # Extract label from path if not provided
        default_label = path.split(".")[-1].replace("_", " ").title()
        
        # Get synonyms from defaults
        synonyms = tuple(DEFAULT_SYNONYMS.get(path, []))
        
        # Handle both dict and RefinableField dataclass
        if hasattr(spec, 'description'):
            # It's a RefinableField dataclass
            description = getattr(spec, 'description', '') or ''
            unit = getattr(spec, 'kernel_unit', None)
            is_derived = getattr(spec, 'derived', False) if hasattr(spec, 'derived') else False
            min_value = getattr(spec, 'min_value', None)
            max_value = getattr(spec, 'max_value', None)
            
            # Try to get keywords from RefinableField and merge with synonyms
            keywords = getattr(spec, 'keywords', ()) or ()
            if keywords:
                synonyms = tuple(set(synonyms) | set(keywords))
        else:
            # It's a dict (legacy or test data)
            description = spec.get("description", "") if isinstance(spec, dict) else ""
            unit = spec.get("unit") if isinstance(spec, dict) else None
            is_derived = spec.get("derived", False) if isinstance(spec, dict) else False
            min_value = spec.get("min") if isinstance(spec, dict) else None
            max_value = spec.get("max") if isinstance(spec, dict) else None
        
        meta = PathMetadata(
            path=path,
            label=default_label,  # Use path-derived label
            description=description,
            unit=unit,
            group=".".join(path.split(".")[:-1]) or path.split(".")[0],
            is_primary=not is_derived,
            is_derived=is_derived,
            synonyms=synonyms,
            min_value=min_value,
            max_value=max_value,
        )
        
        self._paths[path] = meta
    
    def _build_minimal_registry(self) -> None:
        """Build minimal registry from DEFAULT_SYNONYMS when schema unavailable."""
        for path, synonyms in DEFAULT_SYNONYMS.items():
            meta = PathMetadata(
                path=path,
                label=path.split(".")[-1].replace("_", " ").title(),
                description="",
                unit=None,
                group=path.split(".")[0],
                is_primary=True,
                is_derived=False,
                synonyms=tuple(synonyms),
            )
            self._paths[path] = meta
        
        self._build_alias_index()
        self._build_group_index()
        self._loaded = True
    
    def _load_synonym_overrides(self) -> None:
        """Load manual synonym overrides from synonyms.yaml."""
        # Check for synonyms.yaml in config directory
        config_paths = [
            Path(__file__).parent.parent.parent / "config" / "synonyms.yaml",
            Path(__file__).parent / "synonyms.yaml",
        ]
        
        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        overrides = yaml.safe_load(f) or {}
                    
                    for path, synonyms in overrides.items():
                        if path in self._paths:
                            # Merge synonyms
                            existing = set(self._paths[path].synonyms)
                            existing.update(synonyms)
                            
                            # Rebuild PathMetadata with updated synonyms
                            old = self._paths[path]
                            self._paths[path] = PathMetadata(
                                path=old.path,
                                label=old.label,
                                description=old.description,
                                unit=old.unit,
                                group=old.group,
                                is_primary=old.is_primary,
                                is_derived=old.is_derived,
                                synonyms=tuple(sorted(existing)),
                                min_value=old.min_value,
                                max_value=old.max_value,
                            )
                    
                    logger.info(f"Loaded synonym overrides from {config_path}")
                    break
                except Exception as e:
                    logger.warning(f"Failed to load synonyms.yaml: {e}")
    
    def _build_alias_index(self) -> None:
        """Build alias → path lookup index."""
        self._alias_index = {}
        
        for path, meta in self._paths.items():
            # Path itself (exact match)
            self._alias_index[path.lower()] = path
            
            # Last segment (e.g., "beam" from "hull.beam")
            last_segment = path.split(".")[-1].lower()
            if last_segment not in self._alias_index:
                self._alias_index[last_segment] = path
            
            # Label
            label_key = meta.label.lower()
            if label_key not in self._alias_index:
                self._alias_index[label_key] = path
            
            # Synonyms
            for syn in meta.synonyms:
                syn_key = syn.lower()
                if syn_key not in self._alias_index:
                    self._alias_index[syn_key] = path
    
    def _build_group_index(self) -> None:
        """Build group → paths index."""
        self._groups = {}
        for path, meta in self._paths.items():
            if meta.group not in self._groups:
                self._groups[meta.group] = []
            self._groups[meta.group].append(path)
    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    def get(self, path: str) -> Optional[PathMetadata]:
        """Get metadata for a path."""
        self.load()
        return self._paths.get(path)
    
    def exists(self, path: str) -> bool:
        """Check if path exists in registry."""
        self.load()
        return path in self._paths
    
    def resolve_alias(self, alias: str) -> Optional[str]:
        """Resolve an alias to its canonical path."""
        self.load()
        return self._alias_index.get(alias.lower())
    
    def all_paths(self) -> List[str]:
        """Get all registered paths."""
        self.load()
        return list(self._paths.keys())
    
    def paths_in_group(self, group: str) -> List[str]:
        """Get all paths in a group."""
        self.load()
        return self._groups.get(group, [])
    
    def fuzzy_match(self, query: str, limit: int = 20) -> List[Tuple[str, float]]:
        """
        Fuzzy match a query against all aliases.
        
        Returns list of (path, score) sorted by score descending.
        Score is 0.0-1.0 based on similarity.
        """
        self.load()
        query_lower = query.lower().strip()
        
        if not query_lower:
            return []
        
        scores: List[Tuple[str, float]] = []
        seen_paths: Set[str] = set()
        
        for alias, path in self._alias_index.items():
            if path in seen_paths:
                continue
            
            score = self._similarity(query_lower, alias)
            if score > 0.3:  # Threshold
                scores.append((path, score))
                seen_paths.add(path)
        
        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return scores[:limit]
    
    def _similarity(self, query: str, alias: str) -> float:
        """
        Compute similarity between query and alias.
        
        Uses a combination of:
        - Exact match (1.0)
        - Starts with (0.9)
        - Contains (0.7)
        - Word overlap (0.5-0.8)
        """
        if query == alias:
            return 1.0
        
        if alias.startswith(query) or query.startswith(alias):
            return 0.9
        
        if query in alias or alias in query:
            return 0.7
        
        # Word overlap
        query_words = set(query.split())
        alias_words = set(alias.replace("_", " ").split())
        
        if not alias_words:
            return 0.0
        
        overlap = len(query_words & alias_words)
        if overlap > 0:
            return 0.5 + 0.3 * (overlap / max(len(query_words), len(alias_words)))
        
        return 0.0
    
    def get_candidates_for_query(self, query: str, limit: int = 20) -> List[PathMetadata]:
        """
        Get candidate paths for a natural language query.
        
        This is the main entry point for the router to get
        plausible paths before LLM extraction.
        """
        self.load()
        
        # Extract potential entity words from query
        # Remove common stop words
        stop_words = {
            "why", "did", "does", "is", "was", "were", "the", "a", "an",
            "what", "how", "when", "where", "which", "that", "this",
            "change", "changed", "happen", "happened", "affect", "affected",
            "tell", "me", "about", "show", "explain", "it", "its",
        }
        
        words = query.lower().split()
        entity_words = [w for w in words if w not in stop_words and len(w) > 1]
        
        candidates: Dict[str, float] = {}
        
        # Try each entity word
        for word in entity_words:
            # Direct alias lookup
            path = self.resolve_alias(word)
            if path:
                candidates[path] = candidates.get(path, 0) + 1.0
            
            # Fuzzy match
            matches = self.fuzzy_match(word, limit=10)
            for path, score in matches:
                candidates[path] = max(candidates.get(path, 0), score)
        
        # Sort by score
        sorted_candidates = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
        
        # Return PathMetadata objects
        result = []
        for path, score in sorted_candidates[:limit]:
            meta = self._paths.get(path)
            if meta:
                result.append(meta)
        
        return result


# =============================================================================
# SINGLETON
# =============================================================================

_registry: Optional[PathRegistry] = None


def get_path_registry() -> PathRegistry:
    """Get the global PathRegistry singleton."""
    global _registry
    if _registry is None:
        _registry = PathRegistry()
        _registry.load()
    return _registry


def reset_path_registry() -> None:
    """Reset the global PathRegistry (for testing)."""
    global _registry
    _registry = None

