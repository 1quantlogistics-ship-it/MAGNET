"""
magnet/core/receipts.py

T1.4: Receipt / audit log.

Receipts are lightweight, append-only records describing what was committed and why.
They are designed for:
- debugging / traceability
- UI "what changed" panels
- external export (reports)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Receipt:
    receipt_id: str
    timestamp: str
    source: str
    action: str
    design_id: Optional[str] = None
    design_version: Optional[int] = None
    written_paths: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "timestamp": self.timestamp,
            "source": self.source,
            "action": self.action,
            "design_id": self.design_id,
            "design_version": self.design_version,
            "written_paths": list(self.written_paths),
            "metadata": dict(self.metadata),
        }


def new_receipt(
    *,
    receipt_id: str,
    source: str,
    action: str,
    design_id: Optional[str] = None,
    design_version: Optional[int] = None,
    written_paths: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Receipt:
    ts = datetime.now(timezone.utc).isoformat()
    return Receipt(
        receipt_id=str(receipt_id),
        timestamp=ts,
        source=str(source),
        action=str(action),
        design_id=str(design_id) if design_id is not None else None,
        design_version=int(design_version) if design_version is not None else None,
        written_paths=list(written_paths or []),
        metadata=dict(metadata or {}),
    )

