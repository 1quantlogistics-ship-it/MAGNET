"""
MAGNET Revalidation Scheduler

Module 03 v1.1 - Production-Ready

Schedules validators for re-execution after parameter changes.

This module bridges Module 03 (Dependency Engine) with Module 04 (Validation Pipeline).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Optional, Set, Any, TYPE_CHECKING
from heapq import heappush, heappop
import logging

if TYPE_CHECKING:
    from magnet.validators.executor import PipelineExecutor

logger = logging.getLogger(__name__)


# =============================================================================
# REVALIDATION TASK
# =============================================================================

@dataclass
class RevalidationTask:
    """A task in the revalidation queue."""
    validator_id: str
    priority: int  # Lower = higher priority
    queued_at: datetime = field(default_factory=datetime.utcnow)
    triggered_by: str = ""  # Parameter or event that triggered this
    triggered_by_user: str = ""
    reason: str = ""

    def __lt__(self, other: "RevalidationTask") -> bool:
        """For heap ordering."""
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.queued_at < other.queued_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validator_id": self.validator_id,
            "priority": self.priority,
            "queued_at": self.queued_at.isoformat(),
            "triggered_by": self.triggered_by,
            "triggered_by_user": self.triggered_by_user,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RevalidationTask":
        return cls(
            validator_id=data["validator_id"],
            priority=data.get("priority", 1),
            queued_at=datetime.fromisoformat(data["queued_at"]) if data.get("queued_at") else datetime.utcnow(),
            triggered_by=data.get("triggered_by", ""),
            triggered_by_user=data.get("triggered_by_user", ""),
            reason=data.get("reason", ""),
        )


# =============================================================================
# REVALIDATION SCHEDULER
# =============================================================================

class RevalidationScheduler:
    """
    Schedules validators for re-execution after changes.

    Maintains a priority queue of validators that need to re-run
    due to parameter changes or invalidation events.
    """

    def __init__(self, executor: Optional["PipelineExecutor"] = None):
        self._executor = executor
        self._queue: List[RevalidationTask] = []  # Heap queue
        self._queued_ids: Set[str] = set()  # For deduplication
        self._processed_count = 0
        self._callbacks: List[Callable[[str], None]] = []

    def set_executor(self, executor: "PipelineExecutor") -> None:
        """Set the executor for processing tasks."""
        self._executor = executor

    def queue_validator(
        self,
        validator_id: str,
        triggered_by: str = "",
        priority: int = 1,
        triggered_by_user: str = "",
        reason: str = ""
    ) -> bool:
        """
        Queue a single validator for revalidation.

        Returns True if queued, False if already in queue.
        """
        if validator_id in self._queued_ids:
            logger.debug(f"Validator {validator_id} already queued")
            return False

        task = RevalidationTask(
            validator_id=validator_id,
            priority=priority,
            triggered_by=triggered_by,
            triggered_by_user=triggered_by_user,
            reason=reason,
        )
        heappush(self._queue, task)
        self._queued_ids.add(validator_id)

        logger.debug(f"Queued validator {validator_id} (priority={priority})")
        return True

    def queue_validators(
        self,
        validator_ids: List[str],
        triggered_by: str = "",
        priority: int = 1,
        triggered_by_user: str = "",
        reason: str = ""
    ) -> int:
        """
        Queue multiple validators for revalidation.

        Returns count of validators actually queued (excludes duplicates).
        """
        count = 0
        for vid in validator_ids:
            if self.queue_validator(
                vid,
                triggered_by=triggered_by,
                priority=priority,
                triggered_by_user=triggered_by_user,
                reason=reason
            ):
                count += 1

        logger.info(f"Queued {count}/{len(validator_ids)} validators (triggered by: {triggered_by})")
        return count

    def get_pending(self) -> List[RevalidationTask]:
        """Get all pending tasks (without removing them)."""
        return list(self._queue)

    def get_pending_count(self) -> int:
        """Get count of pending tasks."""
        return len(self._queue)

    def peek_next(self) -> Optional[RevalidationTask]:
        """Peek at the next task without removing it."""
        if self._queue:
            return self._queue[0]
        return None

    def pop_next(self) -> Optional[RevalidationTask]:
        """Pop the highest priority task."""
        if not self._queue:
            return None

        task = heappop(self._queue)
        self._queued_ids.discard(task.validator_id)
        return task

    def process_next(self, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Process the next pending validator.

        Returns validator_id if processed, None if queue empty or no executor.
        """
        if not self._executor:
            logger.warning("No executor set - cannot process tasks")
            return None

        task = self.pop_next()
        if not task:
            return None

        logger.info(f"Processing revalidation: {task.validator_id}")

        # Execute the validator
        execution = self._executor.execute_validators(
            [task.validator_id],
            context=context or {}
        )

        self._processed_count += 1

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(task.validator_id)
            except Exception as e:
                logger.error(f"Callback error: {e}")

        return task.validator_id

    def process_pending(
        self,
        max_count: int = 10,
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Process up to max_count pending validators.

        Returns list of processed validator IDs.
        """
        processed = []
        for _ in range(max_count):
            vid = self.process_next(context)
            if vid is None:
                break
            processed.append(vid)

        return processed

    def process_all(self, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Process all pending validators."""
        return self.process_pending(max_count=len(self._queue) + 1, context=context)

    def clear_queue(self) -> int:
        """Clear all pending tasks. Returns count cleared."""
        count = len(self._queue)
        self._queue.clear()
        self._queued_ids.clear()
        return count

    def remove_validator(self, validator_id: str) -> bool:
        """Remove a specific validator from the queue."""
        if validator_id not in self._queued_ids:
            return False

        self._queue = [t for t in self._queue if t.validator_id != validator_id]
        self._queued_ids.discard(validator_id)

        # Re-heapify after removal
        from heapq import heapify
        heapify(self._queue)

        return True

    def add_callback(self, callback: Callable[[str], None]) -> None:
        """Add a callback to be called after each validator is processed."""
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[str], None]) -> None:
        """Remove a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    @property
    def processed_count(self) -> int:
        """Total validators processed."""
        return self._processed_count

    @property
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._queue) == 0

    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        return {
            "pending_count": len(self._queue),
            "processed_count": self._processed_count,
            "queued_validator_ids": list(self._queued_ids),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize scheduler state."""
        return {
            "queue": [t.to_dict() for t in self._queue],
            "processed_count": self._processed_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RevalidationScheduler":
        """Load scheduler from serialized data."""
        scheduler = cls()
        scheduler._processed_count = data.get("processed_count", 0)

        for task_data in data.get("queue", []):
            task = RevalidationTask.from_dict(task_data)
            heappush(scheduler._queue, task)
            scheduler._queued_ids.add(task.validator_id)

        return scheduler
