"""
explain/trace_collector.py - Collect calculation traces for expert explanations
BRAVO OWNS THIS FILE.

Section 42: Explanation Engine
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class CalculationStep:
    """Single step in a calculation trace."""

    step_id: int = 0
    name: str = ""

    formula: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    output: Any = None

    unit: str = ""
    source: str = ""  # Reference (standard, paper, etc.)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step_id,
            "name": self.name,
            "formula": self.formula,
            "inputs": self.inputs,
            "output": self.output,
            "unit": self.unit,
        }


@dataclass
class CalculationTrace:
    """Complete trace of a calculation."""

    trace_id: str = ""
    calculator_name: str = ""

    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    steps: List[CalculationStep] = field(default_factory=list)

    final_result: Any = None

    def add_step(
        self,
        name: str,
        formula: str,
        inputs: Dict[str, Any],
        output: Any,
        unit: str = "",
        source: str = "",
    ) -> CalculationStep:
        """Add a calculation step."""
        step = CalculationStep(
            step_id=len(self.steps) + 1,
            name=name,
            formula=formula,
            inputs=inputs,
            output=output,
            unit=unit,
            source=source,
        )
        self.steps.append(step)
        return step

    def complete(self, result: Any) -> None:
        """Mark trace as complete."""
        self.completed_at = datetime.utcnow()
        self.final_result = result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "calculator": self.calculator_name,
            "steps": [s.to_dict() for s in self.steps],
            "final_result": self.final_result,
        }


class TraceCollector:
    """
    Collects and manages calculation traces.
    """

    def __init__(self):
        self._active_traces: Dict[str, CalculationTrace] = {}
        self._completed_traces: List[CalculationTrace] = []

    def start_trace(
        self,
        trace_id: str,
        calculator_name: str,
    ) -> CalculationTrace:
        """Start a new trace."""
        trace = CalculationTrace(
            trace_id=trace_id,
            calculator_name=calculator_name,
        )
        self._active_traces[trace_id] = trace
        return trace

    def get_trace(self, trace_id: str) -> Optional[CalculationTrace]:
        """Get active or completed trace."""
        if trace_id in self._active_traces:
            return self._active_traces[trace_id]
        for trace in self._completed_traces:
            if trace.trace_id == trace_id:
                return trace
        return None

    def complete_trace(self, trace_id: str, result: Any) -> None:
        """Complete a trace."""
        if trace_id in self._active_traces:
            trace = self._active_traces.pop(trace_id)
            trace.complete(result)
            self._completed_traces.append(trace)

    def get_recent_traces(self, limit: int = 10) -> List[CalculationTrace]:
        """Get recent completed traces."""
        return self._completed_traces[-limit:]

    def clear(self) -> None:
        """Clear all traces."""
        self._active_traces.clear()
        self._completed_traces.clear()
