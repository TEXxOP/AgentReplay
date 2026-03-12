"""
Data models for AgentReplay trace system.
Each agent execution is a Trace composed of TraceSteps forming a tree.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum
import uuid


def _new_id() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class StepType(str, Enum):
    THOUGHT = "thought"
    TOOL_CALL = "tool_call"
    OBSERVATION = "observation"
    ERROR = "error"
    FINAL_ANSWER = "final_answer"


class TraceStep(BaseModel):
    id: str = Field(default_factory=_new_id)
    trace_id: str = ""
    parent_id: Optional[str] = None
    step_type: StepType = StepType.THOUGHT
    content: str = ""
    tool_name: Optional[str] = None
    tool_args: Optional[dict] = None
    timestamp: datetime = Field(default_factory=_now)
    metadata: dict = Field(default_factory=dict)
    memory_id: Optional[str] = None


class TraceStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Trace(BaseModel):
    id: str = Field(default_factory=_new_id)
    agent_name: str = ""
    task: str = ""
    status: TraceStatus = TraceStatus.RUNNING
    steps: List[TraceStep] = Field(default_factory=list)
    parent_trace_id: Optional[str] = None
    fork_step_id: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)
    completed_at: Optional[datetime] = None

    def get_step(self, step_id: str) -> Optional[TraceStep]:
        for s in self.steps:
            if s.id == step_id:
                return s
        return None

    def get_steps_until(self, step_id: str) -> List[TraceStep]:
        """Get all steps from start up to and including the given step."""
        result = []
        for s in self.steps:
            result.append(s)
            if s.id == step_id:
                break
        return result


class DiffResult(BaseModel):
    """Result of comparing two traces."""
    trace_a_id: str
    trace_b_id: str
    divergence_step_index: int = 0
    steps_a: List[TraceStep] = Field(default_factory=list)
    steps_b: List[TraceStep] = Field(default_factory=list)
    summary: str = ""
