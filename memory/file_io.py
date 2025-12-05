"""
MAGNET Memory File I/O
======================

File-based protocol for agent communication.
All agent communication persists to JSON files for auditability.

Design Principles (from Operations Guide):
- File-Based Protocol: All communication persists to JSON for auditability
- Asynchronous Messaging: Agents read/write to shared files, not direct calls
- Schema Enforcement: All messages validated against Pydantic schemas
- Append-Only Logs: Decision history in JSONL for complete audit trails
- Stateless Agents: Each invocation receives full context
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Type, TypeVar
from datetime import datetime
from pydantic import BaseModel
import fcntl

from .schemas import (
    MissionSchema,
    HullParamsSchema,
    SystemStateSchema,
    AgentVoteSchema,
    StructuralDesignSchema,
    WeightEstimateSchema,
    StabilityResultsSchema,
)

T = TypeVar('T', bound=BaseModel)


class MemoryFileIO:
    """
    File I/O operations for MAGNET memory system.

    Provides atomic read/write operations with schema validation.
    Supports both single-file JSON and append-only JSONL logs.
    """

    def __init__(self, memory_path: str = "memory"):
        """
        Initialize memory file I/O.

        Args:
            memory_path: Base directory for memory files
        """
        self.memory_path = Path(memory_path)
        self.memory_path.mkdir(parents=True, exist_ok=True)
        (self.memory_path / "decisions").mkdir(exist_ok=True)

        # File mappings
        self.files = {
            "mission": self.memory_path / "mission.json",
            "hull_params": self.memory_path / "hull_params.json",
            "structural_design": self.memory_path / "structural_design.json",
            "weight_estimate": self.memory_path / "weight_estimate.json",
            "stability_results": self.memory_path / "stability_results.json",
            "resistance_results": self.memory_path / "resistance_results.json",
            "system_state": self.memory_path / "system_state.json",
            "reviews": self.memory_path / "reviews.json",
            "constraints": self.memory_path / "constraints.json",
        }

        # JSONL log files
        self.logs = {
            "voting_history": self.memory_path / "decisions" / "voting_history.jsonl",
            "supervisor_decisions": self.memory_path / "decisions" / "supervisor_decisions.jsonl",
            "design_iterations": self.memory_path / "decisions" / "design_iterations.jsonl",
        }

        # Schema mappings
        self.schemas: Dict[str, Type[BaseModel]] = {
            "mission": MissionSchema,
            "hull_params": HullParamsSchema,
            "structural_design": StructuralDesignSchema,
            "weight_estimate": WeightEstimateSchema,
            "stability_results": StabilityResultsSchema,
            "system_state": SystemStateSchema,
        }

    def read(self, file_key: str) -> Optional[Dict[str, Any]]:
        """
        Read a memory file.

        Args:
            file_key: Key for the file (e.g., "mission", "hull_params")

        Returns:
            Dict contents or None if file doesn't exist
        """
        file_path = self.files.get(file_key)
        if not file_path:
            raise ValueError(f"Unknown file key: {file_key}")

        if not file_path.exists():
            return None

        with open(file_path, 'r') as f:
            return json.load(f)

    def read_validated(self, file_key: str, schema_class: Type[T]) -> Optional[T]:
        """
        Read and validate a memory file against a schema.

        Args:
            file_key: Key for the file
            schema_class: Pydantic schema class to validate against

        Returns:
            Validated schema instance or None
        """
        data = self.read(file_key)
        if data is None:
            return None
        return schema_class(**data)

    def write(self, file_key: str, data: Dict[str, Any], validate: bool = True) -> None:
        """
        Write data to a memory file with atomic write.

        Args:
            file_key: Key for the file
            data: Data to write
            validate: Whether to validate against schema
        """
        file_path = self.files.get(file_key)
        if not file_path:
            raise ValueError(f"Unknown file key: {file_key}")

        # Validate if schema exists
        if validate and file_key in self.schemas:
            schema_class = self.schemas[file_key]
            validated = schema_class(**data)
            data = validated.model_dump(mode='json')

        # Atomic write using temp file
        temp_path = file_path.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        # Atomic rename
        temp_path.rename(file_path)

    def write_schema(self, file_key: str, schema_instance: BaseModel) -> None:
        """
        Write a validated schema instance to file.

        Args:
            file_key: Key for the file
            schema_instance: Validated Pydantic model instance
        """
        file_path = self.files.get(file_key)
        if not file_path:
            raise ValueError(f"Unknown file key: {file_key}")

        data = schema_instance.model_dump(mode='json')

        temp_path = file_path.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        temp_path.rename(file_path)

    def append_log(self, log_key: str, entry: Dict[str, Any]) -> None:
        """
        Append entry to a JSONL log file.

        Args:
            log_key: Key for the log file
            entry: Entry to append
        """
        log_path = self.logs.get(log_key)
        if not log_path:
            raise ValueError(f"Unknown log key: {log_key}")

        # Add timestamp if not present
        if "timestamp" not in entry:
            entry["timestamp"] = datetime.now().isoformat()

        with open(log_path, 'a') as f:
            f.write(json.dumps(entry, default=str) + '\n')

    def append_vote(self, vote: AgentVoteSchema) -> None:
        """
        Append a vote to voting history.

        Args:
            vote: Validated vote schema
        """
        self.append_log("voting_history", vote.model_dump(mode='json'))

    def read_log(self, log_key: str) -> List[Dict[str, Any]]:
        """
        Read all entries from a JSONL log.

        Args:
            log_key: Key for the log file

        Returns:
            List of log entries
        """
        log_path = self.logs.get(log_key)
        if not log_path or not log_path.exists():
            return []

        entries = []
        with open(log_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    def get_system_state(self) -> SystemStateSchema:
        """
        Get current system state, initializing if needed.

        Returns:
            Current system state
        """
        state = self.read_validated("system_state", SystemStateSchema)
        if state is None:
            state = SystemStateSchema()
            self.write_schema("system_state", state)
        return state

    def update_system_state(self, **updates) -> SystemStateSchema:
        """
        Update system state with given fields.

        Args:
            **updates: Fields to update

        Returns:
            Updated system state
        """
        state = self.get_system_state()
        state_dict = state.model_dump()
        state_dict.update(updates)
        state_dict["last_updated"] = datetime.now()
        new_state = SystemStateSchema(**state_dict)
        self.write_schema("system_state", new_state)
        return new_state

    def exists(self, file_key: str) -> bool:
        """Check if a memory file exists."""
        file_path = self.files.get(file_key)
        return file_path is not None and file_path.exists()

    def list_files(self) -> Dict[str, bool]:
        """List all memory files and their existence status."""
        return {key: self.exists(key) for key in self.files.keys()}


# Convenience singleton
_default_memory: Optional[MemoryFileIO] = None


def get_memory(memory_path: str = "memory") -> MemoryFileIO:
    """Get or create the default memory instance."""
    global _default_memory
    if _default_memory is None:
        _default_memory = MemoryFileIO(memory_path)
    return _default_memory
