"""
domain_hashes.py - Domain Hash Contracts v1.0
BRAVO OWNS THIS FILE.

V1.4 FIX #2: Domain-Specific Hashes
Provides per-domain hash computation for staleness detection.

Domains:
- geometry: Hull geometry, sections, compartments
- arrangement: Interior layout, spaces, zones
- routing: System routing, trunks, penetrations
- phase: Phase states, milestones
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, TYPE_CHECKING
from abc import ABC, abstractmethod
import hashlib
import json

__all__ = [
    'DomainHashes',
    'DomainHashProvider',
    'compute_domain_hash',
    'compute_composite_hash',
]


# =============================================================================
# DOMAIN HASHES
# =============================================================================

@dataclass
class DomainHashes:
    """
    Per-domain hashes for staleness detection.

    V1.4 spec requires these fields in all API responses:
    - geometry_hash: Hash of hull geometry state
    - arrangement_hash: Hash of interior layout state
    - routing_hash: Hash of routing layout state
    - phase_hash: Hash of phase states
    - version: Integer version number
    """

    geometry_hash: Optional[str] = None
    arrangement_hash: Optional[str] = None
    routing_hash: Optional[str] = None
    phase_hash: Optional[str] = None
    version: int = 1

    @property
    def content_hash(self) -> str:
        """
        Composite hash from all domain hashes.

        content_hash = sha256(geometry_hash + arrangement_hash + routing_hash + phase_hash)
        """
        return compute_composite_hash(
            self.geometry_hash,
            self.arrangement_hash,
            self.routing_hash,
            self.phase_hash,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            'geometry_hash': self.geometry_hash,
            'arrangement_hash': self.arrangement_hash,
            'routing_hash': self.routing_hash,
            'phase_hash': self.phase_hash,
            'content_hash': self.content_hash,
            'version': self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DomainHashes':
        """Create from dictionary."""
        return cls(
            geometry_hash=data.get('geometry_hash'),
            arrangement_hash=data.get('arrangement_hash'),
            routing_hash=data.get('routing_hash'),
            phase_hash=data.get('phase_hash'),
            version=data.get('version', 1),
        )


# =============================================================================
# DOMAIN HASH PROVIDER
# =============================================================================

class DomainHashProvider(ABC):
    """
    Abstract provider for computing domain hashes.

    Implementations should connect to state managers and
    compute hashes for their specific domain.
    """

    @property
    @abstractmethod
    def domain(self) -> str:
        """Domain identifier (geometry, arrangement, routing, phase)."""
        pass

    @abstractmethod
    def compute_hash(self, design_id: str) -> Optional[str]:
        """
        Compute hash for the domain state.

        Args:
            design_id: Design identifier

        Returns:
            SHA256 hash string or None if no state
        """
        pass


# =============================================================================
# HASH UTILITIES
# =============================================================================

def compute_domain_hash(data: Any) -> str:
    """
    Compute SHA256 hash for domain data.

    Args:
        data: Data to hash (dict, list, or primitive)

    Returns:
        SHA256 hash string
    """
    if data is None:
        return hashlib.sha256(b'null').hexdigest()

    # Normalize to JSON for consistent hashing
    if isinstance(data, (dict, list)):
        normalized = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    # Handle primitives
    return hashlib.sha256(str(data).encode('utf-8')).hexdigest()


def compute_composite_hash(*hashes: Optional[str]) -> str:
    """
    Compute composite hash from multiple domain hashes.

    Args:
        *hashes: Variable number of hash strings

    Returns:
        Composite SHA256 hash
    """
    # Use empty string for None values
    normalized = [h or '' for h in hashes]
    combined = ''.join(normalized)
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()


# =============================================================================
# GEOMETRY HASH PROVIDER
# =============================================================================

class GeometryHashProvider(DomainHashProvider):
    """Provider for geometry domain hashes."""

    def __init__(self, state_manager: Any = None):
        self._sm = state_manager

    @property
    def domain(self) -> str:
        return 'geometry'

    def compute_hash(self, design_id: str) -> Optional[str]:
        """Compute hash from hull geometry state."""
        if not self._sm:
            return None

        try:
            # Get geometry-related state
            hull_data = self._sm.get(f'hull.{design_id}')
            structure_data = self._sm.get(f'structure.{design_id}')

            if hull_data is None and structure_data is None:
                return None

            combined = {
                'hull': hull_data,
                'structure': structure_data,
            }
            return compute_domain_hash(combined)
        except Exception:
            return None


# =============================================================================
# ARRANGEMENT HASH PROVIDER
# =============================================================================

class ArrangementHashProvider(DomainHashProvider):
    """Provider for arrangement domain hashes."""

    def __init__(self, state_manager: Any = None):
        self._sm = state_manager

    @property
    def domain(self) -> str:
        return 'arrangement'

    def compute_hash(self, design_id: str) -> Optional[str]:
        """Compute hash from interior layout state."""
        if not self._sm:
            return None

        try:
            layout_data = self._sm.get(f'interior.layout.{design_id}')
            if layout_data is None:
                return None

            return compute_domain_hash(layout_data)
        except Exception:
            return None


# =============================================================================
# ROUTING HASH PROVIDER
# =============================================================================

class RoutingHashProvider(DomainHashProvider):
    """Provider for routing domain hashes."""

    def __init__(self, state_manager: Any = None):
        self._sm = state_manager

    @property
    def domain(self) -> str:
        return 'routing'

    def compute_hash(self, design_id: str) -> Optional[str]:
        """Compute hash from routing layout state."""
        if not self._sm:
            return None

        try:
            routing_data = self._sm.get(f'routing.layout.{design_id}')
            if routing_data is None:
                return None

            return compute_domain_hash(routing_data)
        except Exception:
            return None


# =============================================================================
# PHASE HASH PROVIDER
# =============================================================================

class PhaseHashProvider(DomainHashProvider):
    """Provider for phase domain hashes."""

    def __init__(self, state_manager: Any = None):
        self._sm = state_manager

    @property
    def domain(self) -> str:
        return 'phase'

    def compute_hash(self, design_id: str) -> Optional[str]:
        """Compute hash from phase states."""
        if not self._sm:
            return None

        try:
            phase_data = self._sm.get(f'phase_states.{design_id}')
            if phase_data is None:
                return None

            return compute_domain_hash(phase_data)
        except Exception:
            return None


# =============================================================================
# DOMAIN HASH SERVICE
# =============================================================================

@dataclass
class DomainHashService:
    """
    Service for computing and caching domain hashes.

    This service aggregates all domain hash providers and
    provides a unified interface for getting domain hashes.
    """

    _providers: Dict[str, DomainHashProvider] = field(default_factory=dict)

    def __init__(self, state_manager: Any = None):
        """
        Initialize with state manager.

        Args:
            state_manager: State manager instance
        """
        self._providers = {
            'geometry': GeometryHashProvider(state_manager),
            'arrangement': ArrangementHashProvider(state_manager),
            'routing': RoutingHashProvider(state_manager),
            'phase': PhaseHashProvider(state_manager),
        }

    def get_domain_hashes(self, design_id: str) -> DomainHashes:
        """
        Get all domain hashes for a design.

        Args:
            design_id: Design identifier

        Returns:
            DomainHashes with all domain values
        """
        return DomainHashes(
            geometry_hash=self._providers['geometry'].compute_hash(design_id),
            arrangement_hash=self._providers['arrangement'].compute_hash(design_id),
            routing_hash=self._providers['routing'].compute_hash(design_id),
            phase_hash=self._providers['phase'].compute_hash(design_id),
        )

    def get_hash(self, domain: str, design_id: str) -> Optional[str]:
        """
        Get hash for a specific domain.

        Args:
            domain: Domain name (geometry, arrangement, routing, phase)
            design_id: Design identifier

        Returns:
            Hash string or None
        """
        provider = self._providers.get(domain)
        if provider:
            return provider.compute_hash(design_id)
        return None

    def register_provider(self, provider: DomainHashProvider) -> None:
        """
        Register a custom domain hash provider.

        Args:
            provider: Provider instance
        """
        self._providers[provider.domain] = provider
