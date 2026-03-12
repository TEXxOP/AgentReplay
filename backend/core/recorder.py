"""
AgentRecorder — the flight-recorder that wraps any agent execution.
Captures every thought, tool call, observation, and answer into SuperMemory.
Streams events via WebSocket for the live dashboard.
"""
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Callable, Any

from .models import TraceStep, Trace, TraceStatus, StepType
from .memory_client import MemoryClient


class WebSocketManager:
    """Manages connected WebSocket clients for live streaming."""

    def __init__(self):
        self.connections: list = []

    async def connect(self, ws):
        self.connections.append(ws)

    def disconnect(self, ws):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, data: dict):
        payload = json.dumps(data, default=str)
        dead = []
        for ws in self.connections:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


class AgentRecorder:
    """
    Core innovation: wraps any agent and records every decision step.
    Steps are stored in SuperMemory and streamed live via WebSocket.
    """

    def __init__(self, memory: MemoryClient, ws_manager: WebSocketManager):
        self.memory = memory
        self.ws = ws_manager
        self.traces: dict[str, Trace] = {}

    # ── Trace Lifecycle ──────────────────────────────────────

    def create_trace(
        self,
        agent_name: str,
        task: str,
        parent_trace_id: Optional[str] = None,
        fork_step_id: Optional[str] = None,
    ) -> Trace:
        trace = Trace(
            agent_name=agent_name,
            task=task,
            parent_trace_id=parent_trace_id,
            fork_step_id=fork_step_id,
        )
        self.traces[trace.id] = trace
        return trace

    async def complete_trace(self, trace_id: str, status: TraceStatus = TraceStatus.COMPLETED):
        if trace_id in self.traces:
            trace = self.traces[trace_id]
            trace.status = status
            trace.completed_at = datetime.now(timezone.utc)
            await self.ws.broadcast({
                "event": "trace_complete",
                "trace_id": trace_id,
                "status": status.value,
            })

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        return self.traces.get(trace_id)

    def list_traces(self) -> List[Trace]:
        return sorted(self.traces.values(), key=lambda t: t.created_at, reverse=True)

    # ── Step Recording ───────────────────────────────────────

    async def record_step(
        self,
        trace_id: str,
        step_type: StepType,
        content: str,
        tool_name: Optional[str] = None,
        tool_args: Optional[dict] = None,
        parent_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> TraceStep:
        step = TraceStep(
            trace_id=trace_id,
            parent_id=parent_id,
            step_type=step_type,
            content=content,
            tool_name=tool_name,
            tool_args=tool_args,
            metadata=metadata or {},
        )

        # Store in SuperMemory
        memory_id = await self.memory.store_step(step)
        step.memory_id = memory_id

        # Add to local trace
        if trace_id in self.traces:
            self.traces[trace_id].steps.append(step)

        # Broadcast to dashboard
        await self.ws.broadcast({
            "event": "new_step",
            "trace_id": trace_id,
            "step": json.loads(step.model_dump_json()),
        })

        # Small delay so dashboard can render step-by-step
        await asyncio.sleep(0.3)

        return step
