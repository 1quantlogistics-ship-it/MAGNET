# CORTEX: Control Plane Implementation Specification

**Version:** 1.0  
**Status:** Implementation Ready  
**Date:** January 2026  
**Prerequisite:** Read CORTEX_THEORY.md first

---

## Executive Summary

This document specifies the implementation of CORTEX's control plane—the architecture for LLM observation and manipulation of existing physical artifacts.

**Existing MAGNET Assets Reused:**
- `magnet/kernel/geometry_observables.py` — Observable registry and measurements (90% reusable)
- `magnet/kernel/shape_document.py` — Shape document generation (100% reusable)
- `magnet/kernel/stdlib/expander.py` — ADJUST/TARGET execution (100% reusable)
- `magnet/kernel/stdlib/compiler.py` — Geometry compilation (100% reusable)
- `magnet/validators/` — Validation framework (80% reusable)
- `magnet/agents/geometry_proposer.py` — Two-pass thinking pattern (70% reusable)
- `magnet/webgl/exporter.py` — Export pipeline (reusable for headless rendering base)

---

## 1. Artifact Graph

### 1.1 Node Schema (Component)

```python
# cortex/artifact_graph/component.py

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import uuid


class ComponentCategory(Enum):
    """High-level component categories."""
    STRUCTURE = "structure"
    MACHINERY = "machinery"
    SYSTEMS = "systems"
    OUTFIT = "outfit"
    HULL = "hull"


@dataclass
class Component:
    """
    A node in the artifact graph representing a physical component.
    
    This is the canonical representation. All CAD imports map to this schema.
    """
    # Identity
    id: str = field(default_factory=lambda: f"comp_{uuid.uuid4().hex[:12]}")
    name: str = ""
    type: str = ""  # Specific type: "fuel_tank", "pump", "frame", etc.
    category: ComponentCategory = ComponentCategory.OUTFIT
    
    # Geometry
    bounds: Optional["BoundingBox"] = None  # AABB
    mesh_id: Optional[str] = None  # Reference to mesh in geometry store
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # Centroid in world coords
    orientation: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # Euler angles (rad)
    dimensions: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # Length, width, height
    
    # Physical properties
    mass_kg: float = 0.0
    material: str = ""
    volume_m3: float = 0.0
    
    # Functional properties
    capacity: Optional[float] = None  # For tanks, batteries, etc.
    capacity_unit: str = ""
    power_kw: Optional[float] = None  # For machinery
    
    # Ports (connection points)
    ports: Dict[str, Tuple[float, float, float]] = field(default_factory=dict)
    # Example: {"inlet": (0.5, 0, 0), "outlet": (-0.5, 0, 0)}
    
    # Constraints
    requires_access: bool = False
    access_directions: List[str] = field(default_factory=list)  # ["top", "front"]
    min_clearance_m: float = 0.0
    structural_support_required: bool = False
    
    # Metadata
    source: str = ""  # "step_import", "manual", "generated"
    source_id: Optional[str] = None  # Original ID from CAD
    system_id: Optional[str] = None  # Which system this belongs to
    zone_id: Optional[str] = None  # Which zone this is in
    parent_id: Optional[str] = None  # For hierarchical components
    tags: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    
    # Versioning
    version: int = 1
    created_at: Optional[str] = None
    modified_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "category": self.category.value,
            "position": list(self.position),
            "dimensions": list(self.dimensions),
            "mass_kg": self.mass_kg,
            "ports": {k: list(v) for k, v in self.ports.items()},
            "system_id": self.system_id,
            "zone_id": self.zone_id,
        }


@dataclass
class BoundingBox:
    """Axis-aligned bounding box."""
    min_x: float = 0.0
    min_y: float = 0.0
    min_z: float = 0.0
    max_x: float = 0.0
    max_y: float = 0.0
    max_z: float = 0.0
    
    @property
    def center(self) -> Tuple[float, float, float]:
        return (
            (self.min_x + self.max_x) / 2,
            (self.min_y + self.max_y) / 2,
            (self.min_z + self.max_z) / 2,
        )
    
    @property
    def volume(self) -> float:
        return (
            (self.max_x - self.min_x) *
            (self.max_y - self.min_y) *
            (self.max_z - self.min_z)
        )
    
    def contains(self, point: Tuple[float, float, float]) -> bool:
        x, y, z = point
        return (
            self.min_x <= x <= self.max_x and
            self.min_y <= y <= self.max_y and
            self.min_z <= z <= self.max_z
        )
    
    def intersects(self, other: "BoundingBox") -> bool:
        return not (
            self.max_x < other.min_x or self.min_x > other.max_x or
            self.max_y < other.min_y or self.min_y > other.max_y or
            self.max_z < other.min_z or self.min_z > other.max_z
        )
    
    def expand(self, margin: float) -> "BoundingBox":
        return BoundingBox(
            min_x=self.min_x - margin,
            min_y=self.min_y - margin,
            min_z=self.min_z - margin,
            max_x=self.max_x + margin,
            max_y=self.max_y + margin,
            max_z=self.max_z + margin,
        )
```

### 1.2 Edge Schema (Relationship)

```python
# cortex/artifact_graph/relationship.py

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum


class RelationshipType(Enum):
    """Types of relationships between components."""
    CONNECTS_TO = "connects_to"      # Physical connection (pipe, wire)
    MOUNTED_ON = "mounted_on"        # Attachment relationship
    ROUTES_THROUGH = "routes_through"  # Path traversal
    CLEARS = "clears"                # Spatial separation
    DEPENDS_ON = "depends_on"        # Logical dependency
    CONTAINS = "contains"            # Hierarchical containment
    ADJACENT_TO = "adjacent_to"      # Spatial adjacency


@dataclass
class Relationship:
    """
    An edge in the artifact graph representing a relationship between components.
    """
    id: str
    type: RelationshipType
    source_id: str
    target_id: str
    
    # Connection details (for CONNECTS_TO)
    source_port: Optional[str] = None
    target_port: Optional[str] = None
    connection_type: Optional[str] = None  # "pipe", "wire", "duct", etc.
    
    # Physical properties
    length_m: Optional[float] = None
    diameter_m: Optional[float] = None
    
    # Spatial properties (for CLEARS)
    clearance_m: Optional[float] = None
    direction: Optional[str] = None  # "above", "below", "forward", etc.
    
    # Metadata
    system_id: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "source_port": self.source_port,
            "target_port": self.target_port,
            "connection_type": self.connection_type,
        }
```

### 1.3 Graph Implementation

```python
# cortex/artifact_graph/graph.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Set, Iterator
import json
import copy
from datetime import datetime

from .component import Component, BoundingBox
from .relationship import Relationship, RelationshipType


@dataclass
class GraphSnapshot:
    """Immutable snapshot of graph state for rollback."""
    components: Dict[str, Dict]
    relationships: Dict[str, Dict]
    timestamp: str
    version: int


class ArtifactGraph:
    """
    The artifact graph is the single source of truth for physical state.
    
    Implementation uses:
    - Dict for O(1) component lookup by ID
    - Adjacency lists for relationship traversal
    - R-tree spatial index for proximity queries (via rtree or scipy.spatial)
    
    REUSES: Concepts from magnet/kernel/stdlib/compiler.py resource management
    """
    
    def __init__(self):
        self._components: Dict[str, Component] = {}
        self._relationships: Dict[str, Relationship] = {}
        
        # Adjacency lists for fast traversal
        self._outgoing: Dict[str, List[str]] = {}  # component_id -> [relationship_ids]
        self._incoming: Dict[str, List[str]] = {}
        
        # Type indices
        self._by_type: Dict[str, Set[str]] = {}  # type -> {component_ids}
        self._by_system: Dict[str, Set[str]] = {}  # system_id -> {component_ids}
        self._by_zone: Dict[str, Set[str]] = {}  # zone_id -> {component_ids}
        
        # Spatial index (lazy initialization)
        self._spatial_index: Optional[Any] = None
        self._spatial_dirty: bool = True
        
        # Versioning
        self._version: int = 0
        self._snapshots: List[GraphSnapshot] = []
        
        # Bounds cache
        self._bounds: Optional[BoundingBox] = None
        self._bounds_dirty: bool = True
    
    # =========================================================================
    # COMPONENT OPERATIONS
    # =========================================================================
    
    def add_component(self, component: Component) -> None:
        """Add a component to the graph."""
        if component.id in self._components:
            raise ValueError(f"Component {component.id} already exists")
        
        self._components[component.id] = component
        self._outgoing[component.id] = []
        self._incoming[component.id] = []
        
        # Update indices
        if component.type:
            self._by_type.setdefault(component.type, set()).add(component.id)
        if component.system_id:
            self._by_system.setdefault(component.system_id, set()).add(component.id)
        if component.zone_id:
            self._by_zone.setdefault(component.zone_id, set()).add(component.id)
        
        self._spatial_dirty = True
        self._bounds_dirty = True
        self._version += 1
    
    def get_component(self, component_id: str) -> Optional[Component]:
        """Get component by ID."""
        return self._components.get(component_id)
    
    def update_component(self, component_id: str, updates: Dict[str, Any]) -> None:
        """Update component properties."""
        component = self._components.get(component_id)
        if not component:
            raise ValueError(f"Component {component_id} not found")
        
        for key, value in updates.items():
            if hasattr(component, key):
                setattr(component, key, value)
        
        component.version += 1
        component.modified_at = datetime.utcnow().isoformat()
        
        self._spatial_dirty = True
        self._bounds_dirty = True
        self._version += 1
    
    def remove_component(self, component_id: str) -> None:
        """Remove component and its relationships."""
        if component_id not in self._components:
            return
        
        # Remove relationships
        for rel_id in list(self._outgoing.get(component_id, [])):
            self._remove_relationship(rel_id)
        for rel_id in list(self._incoming.get(component_id, [])):
            self._remove_relationship(rel_id)
        
        # Remove from indices
        component = self._components[component_id]
        if component.type and component.id in self._by_type.get(component.type, set()):
            self._by_type[component.type].discard(component.id)
        if component.system_id:
            self._by_system.get(component.system_id, set()).discard(component.id)
        if component.zone_id:
            self._by_zone.get(component.zone_id, set()).discard(component.id)
        
        del self._components[component_id]
        del self._outgoing[component_id]
        del self._incoming[component_id]
        
        self._spatial_dirty = True
        self._bounds_dirty = True
        self._version += 1
    
    def list_components(self) -> List[Component]:
        """List all components."""
        return list(self._components.values())
    
    # =========================================================================
    # RELATIONSHIP OPERATIONS
    # =========================================================================
    
    def add_relationship(self, relationship: Relationship) -> None:
        """Add a relationship to the graph."""
        if relationship.source_id not in self._components:
            raise ValueError(f"Source component {relationship.source_id} not found")
        if relationship.target_id not in self._components:
            raise ValueError(f"Target component {relationship.target_id} not found")
        
        self._relationships[relationship.id] = relationship
        self._outgoing[relationship.source_id].append(relationship.id)
        self._incoming[relationship.target_id].append(relationship.id)
        self._version += 1
    
    def add_connection(
        self,
        from_component: str,
        from_port: str,
        to_component: str,
        to_port: str,
        connection_type: str = "pipe",
    ) -> Relationship:
        """Convenience method to add a connection relationship."""
        import uuid
        rel = Relationship(
            id=f"rel_{uuid.uuid4().hex[:8]}",
            type=RelationshipType.CONNECTS_TO,
            source_id=from_component,
            target_id=to_component,
            source_port=from_port,
            target_port=to_port,
            connection_type=connection_type,
        )
        self.add_relationship(rel)
        return rel
    
    def get_relationships(self, component_id: str) -> List[Relationship]:
        """Get all relationships involving a component."""
        rel_ids = (
            self._outgoing.get(component_id, []) +
            self._incoming.get(component_id, [])
        )
        return [self._relationships[rid] for rid in rel_ids if rid in self._relationships]
    
    def _remove_relationship(self, rel_id: str) -> None:
        """Remove a relationship."""
        if rel_id not in self._relationships:
            return
        
        rel = self._relationships[rel_id]
        self._outgoing[rel.source_id].remove(rel_id)
        self._incoming[rel.target_id].remove(rel_id)
        del self._relationships[rel_id]
    
    # =========================================================================
    # QUERY IMPLEMENTATIONS
    # =========================================================================
    
    def query_near(
        self,
        component_id: str,
        radius_m: float,
    ) -> List[Component]:
        """
        Query components within radius of given component.
        
        Uses spatial index for efficiency.
        
        Complexity: O(log n + k) where k is result count
        """
        center_comp = self._components.get(component_id)
        if not center_comp:
            return []
        
        center = center_comp.position
        
        # Rebuild spatial index if needed
        if self._spatial_dirty:
            self._rebuild_spatial_index()
        
        # Query spatial index
        if self._spatial_index is not None:
            # Using rtree
            bbox = (
                center[0] - radius_m, center[1] - radius_m, center[2] - radius_m,
                center[0] + radius_m, center[1] + radius_m, center[2] + radius_m,
            )
            candidate_ids = list(self._spatial_index.intersection(bbox, objects=True))
            
            # Filter by actual distance
            result = []
            for item in candidate_ids:
                comp = self._components.get(item.object)
                if comp and comp.id != component_id:
                    dist = self._distance(center, comp.position)
                    if dist <= radius_m:
                        result.append(comp)
            return result
        else:
            # Fallback to linear scan
            return self._query_near_linear(center, radius_m, exclude=component_id)
    
    def query_in_scope(
        self,
        focus: str,
        scope: str,
    ) -> List[Component]:
        """
        Query components in scope relative to focus.
        
        Scope values:
        - "local_1m", "local_2m", "local_5m": Radius-based
        - "zone": Same zone as focus
        - "system": Same system as focus
        - "full": All components
        """
        focus_comp = self._components.get(focus)
        if not focus_comp:
            return []
        
        if scope.startswith("local_"):
            radius = float(scope.replace("local_", "").replace("m", ""))
            return self.query_near(focus, radius)
        
        elif scope == "zone":
            if focus_comp.zone_id:
                return self.query_by_zone(focus_comp.zone_id)
            return [focus_comp]
        
        elif scope == "system":
            if focus_comp.system_id:
                return self.query_by_system(focus_comp.system_id)
            return [focus_comp]
        
        elif scope == "full":
            return self.list_components()
        
        return [focus_comp]
    
    def query_by_type(self, component_type: str) -> List[Component]:
        """Query components by type."""
        ids = self._by_type.get(component_type, set())
        return [self._components[cid] for cid in ids if cid in self._components]
    
    def query_by_system(self, system_id: str) -> List[Component]:
        """Query components by system."""
        ids = self._by_system.get(system_id, set())
        return [self._components[cid] for cid in ids if cid in self._components]
    
    def query_by_zone(self, zone_id: str) -> List[Component]:
        """Query components by zone."""
        ids = self._by_zone.get(zone_id, set())
        return [self._components[cid] for cid in ids if cid in self._components]
    
    def query_path(
        self,
        from_id: str,
        to_id: str,
    ) -> List[Component]:
        """
        Find path between two components via relationships.
        
        Uses BFS for shortest path.
        """
        if from_id not in self._components or to_id not in self._components:
            return []
        
        if from_id == to_id:
            return [self._components[from_id]]
        
        # BFS
        from collections import deque
        
        visited = {from_id}
        queue = deque([(from_id, [from_id])])
        
        while queue:
            current, path = queue.popleft()
            
            # Check outgoing relationships
            for rel_id in self._outgoing.get(current, []):
                rel = self._relationships.get(rel_id)
                if not rel:
                    continue
                
                neighbor = rel.target_id
                if neighbor == to_id:
                    return [self._components[cid] for cid in path + [neighbor]]
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
            
            # Check incoming relationships
            for rel_id in self._incoming.get(current, []):
                rel = self._relationships.get(rel_id)
                if not rel:
                    continue
                
                neighbor = rel.source_id
                if neighbor == to_id:
                    return [self._components[cid] for cid in path + [neighbor]]
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return []  # No path found
    
    def query_relationships(
        self,
        component_id: str,
        rel_type: Optional[RelationshipType] = None,
    ) -> List[Relationship]:
        """Query relationships for a component, optionally filtered by type."""
        rels = self.get_relationships(component_id)
        if rel_type:
            rels = [r for r in rels if r.type == rel_type]
        return rels
    
    # =========================================================================
    # SPATIAL INDEX
    # =========================================================================
    
    def _rebuild_spatial_index(self) -> None:
        """Rebuild the R-tree spatial index."""
        try:
            from rtree import index
            
            # Create new index
            p = index.Property()
            p.dimension = 3
            self._spatial_index = index.Index(properties=p)
            
            # Insert all components
            for i, (comp_id, comp) in enumerate(self._components.items()):
                if comp.bounds:
                    bbox = (
                        comp.bounds.min_x, comp.bounds.min_y, comp.bounds.min_z,
                        comp.bounds.max_x, comp.bounds.max_y, comp.bounds.max_z,
                    )
                else:
                    # Use position with small epsilon
                    p = comp.position
                    eps = 0.001
                    bbox = (p[0]-eps, p[1]-eps, p[2]-eps, p[0]+eps, p[1]+eps, p[2]+eps)
                
                self._spatial_index.insert(i, bbox, obj=comp_id)
            
            self._spatial_dirty = False
            
        except ImportError:
            # rtree not available, use fallback
            self._spatial_index = None
            self._spatial_dirty = False
    
    def _query_near_linear(
        self,
        center: Tuple[float, float, float],
        radius: float,
        exclude: Optional[str] = None,
    ) -> List[Component]:
        """Linear scan fallback for proximity query."""
        result = []
        for comp in self._components.values():
            if comp.id == exclude:
                continue
            dist = self._distance(center, comp.position)
            if dist <= radius:
                result.append(comp)
        return result
    
    @staticmethod
    def _distance(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
        """Euclidean distance."""
        import math
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
    
    # =========================================================================
    # VERSIONING AND SNAPSHOTS
    # =========================================================================
    
    def snapshot(self) -> GraphSnapshot:
        """Create immutable snapshot for rollback."""
        return GraphSnapshot(
            components={k: copy.deepcopy(v.__dict__) for k, v in self._components.items()},
            relationships={k: copy.deepcopy(v.__dict__) for k, v in self._relationships.items()},
            timestamp=datetime.utcnow().isoformat(),
            version=self._version,
        )
    
    def restore(self, snapshot: GraphSnapshot) -> None:
        """Restore from snapshot."""
        self._components.clear()
        self._relationships.clear()
        self._outgoing.clear()
        self._incoming.clear()
        self._by_type.clear()
        self._by_system.clear()
        self._by_zone.clear()
        
        for comp_id, comp_dict in snapshot.components.items():
            comp = Component(**comp_dict)
            self._components[comp_id] = comp
            self._outgoing[comp_id] = []
            self._incoming[comp_id] = []
            
            if comp.type:
                self._by_type.setdefault(comp.type, set()).add(comp_id)
            if comp.system_id:
                self._by_system.setdefault(comp.system_id, set()).add(comp_id)
            if comp.zone_id:
                self._by_zone.setdefault(comp.zone_id, set()).add(comp_id)
        
        for rel_id, rel_dict in snapshot.relationships.items():
            rel = Relationship(**rel_dict)
            self._relationships[rel_id] = rel
            self._outgoing[rel.source_id].append(rel_id)
            self._incoming[rel.target_id].append(rel_id)
        
        self._version = snapshot.version
        self._spatial_dirty = True
        self._bounds_dirty = True
    
    # =========================================================================
    # BOUNDS
    # =========================================================================
    
    def get_bounds(self) -> Optional[BoundingBox]:
        """Get overall bounding box of all components."""
        if self._bounds_dirty:
            self._compute_bounds()
        return self._bounds
    
    def set_bounds(self, **kwargs) -> None:
        """Manually set bounds (for hull envelope)."""
        self._bounds = BoundingBox(**kwargs)
        self._bounds_dirty = False
    
    def _compute_bounds(self) -> None:
        """Compute bounds from components."""
        if not self._components:
            self._bounds = None
            self._bounds_dirty = False
            return
        
        min_x = min_y = min_z = float('inf')
        max_x = max_y = max_z = float('-inf')
        
        for comp in self._components.values():
            if comp.bounds:
                min_x = min(min_x, comp.bounds.min_x)
                min_y = min(min_y, comp.bounds.min_y)
                min_z = min(min_z, comp.bounds.min_z)
                max_x = max(max_x, comp.bounds.max_x)
                max_y = max(max_y, comp.bounds.max_y)
                max_z = max(max_z, comp.bounds.max_z)
            else:
                p = comp.position
                min_x = min(min_x, p[0])
                min_y = min(min_y, p[1])
                min_z = min(min_z, p[2])
                max_x = max(max_x, p[0])
                max_y = max(max_y, p[1])
                max_z = max(max_z, p[2])
        
        self._bounds = BoundingBox(
            min_x=min_x, min_y=min_y, min_z=min_z,
            max_x=max_x, max_y=max_y, max_z=max_z,
        )
        self._bounds_dirty = False
    
    def compute_volume(self) -> float:
        """Compute total volume from bounds."""
        bounds = self.get_bounds()
        return bounds.volume if bounds else 0.0
    
    # =========================================================================
    # SERIALIZATION
    # =========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize graph to dict."""
        return {
            "version": self._version,
            "components": {k: v.to_dict() for k, v in self._components.items()},
            "relationships": {k: v.to_dict() for k, v in self._relationships.items()},
        }
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), indent=2)
    
    # =========================================================================
    # HELPER METHODS FOR TESTS
    # =========================================================================
    
    def add_component_at(
        self,
        component_id: str,
        position: Tuple[float, float, float],
        dimensions: Tuple[float, float, float] = (0.1, 0.1, 0.1),
    ) -> Component:
        """Helper to add component at position."""
        comp = Component(
            id=component_id,
            position=position,
            dimensions=dimensions,
            bounds=BoundingBox(
                min_x=position[0] - dimensions[0]/2,
                max_x=position[0] + dimensions[0]/2,
                min_y=position[1] - dimensions[1]/2,
                max_y=position[1] + dimensions[1]/2,
                min_z=position[2] - dimensions[2]/2,
                max_z=position[2] + dimensions[2]/2,
            ),
        )
        self.add_component(comp)
        return comp
    
    def get_zone(self, zone_id: str) -> Optional[Any]:
        """Get zone by ID. Override in subclass."""
        return None
```

