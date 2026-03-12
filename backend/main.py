"""
AgentReplay — FastAPI Backend
Time-Travel Debugging for AI Agent Workflows
"""
import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from backend.core.memory_client import MemoryClient
from backend.core.recorder import AgentRecorder, WebSocketManager
from backend.core.replay_engine import ReplayEngine
from backend.core.diff_engine import DiffEngine
from backend.core.models import TraceStatus
from backend.agents.research_agent import run_research_agent
from backend.agents.debug_agent import run_debug_agent


# ── Global Instances ─────────────────────────────────────────

ws_manager = WebSocketManager()
memory = MemoryClient()
recorder = AgentRecorder(memory, ws_manager)
replay_engine = ReplayEngine(recorder)
diff_engine = DiffEngine(recorder)

AGENTS = {
    "research": run_research_agent,
    "debug": run_debug_agent,
}


# ── App Setup ────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 AgentReplay backend started")
    print(f"   SuperMemory: {'connected' if memory.is_connected else 'local-only mode'}")
    yield
    print("AgentReplay backend stopped")


app = FastAPI(
    title="AgentReplay",
    description="Time-Travel Debugging for AI Agent Workflows",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request Models ───────────────────────────────────────────

class RunAgentRequest(BaseModel):
    agent: str = "research"
    task: str

class BranchRequest(BaseModel):
    fork_step_id: str
    new_context: str

class ReplayRequest(BaseModel):
    speed: float = 1.0


# ── WebSocket ────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # Keep alive
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)


# ── REST Endpoints ───────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "supermemory": "connected" if memory.is_connected else "local",
    }


@app.post("/api/agents/run")
async def run_agent(req: RunAgentRequest):
    agent_fn = AGENTS.get(req.agent)
    if not agent_fn:
        raise HTTPException(400, f"Unknown agent: {req.agent}. Available: {list(AGENTS.keys())}")

    trace = recorder.create_trace(agent_name=req.agent, task=req.task)

    # Run in background so we can return immediately
    async def _run():
        try:
            await agent_fn(
                task=req.task,
                recorder=recorder,
                trace=trace,
            )
        except Exception as e:
            await recorder.record_step(
                trace.id,
                step_type=__import__('backend.core.models', fromlist=['StepType']).StepType.ERROR,
                content=f"Agent crashed: {str(e)}",
            )
            await recorder.complete_trace(trace.id, TraceStatus.FAILED)

    asyncio.create_task(_run())

    return {
        "trace_id": trace.id,
        "agent": req.agent,
        "task": req.task,
        "status": "running",
    }


@app.get("/api/traces")
async def list_traces():
    traces = recorder.list_traces()
    return {
        "traces": [
            {
                "id": t.id,
                "agent_name": t.agent_name,
                "task": t.task,
                "status": t.status.value,
                "step_count": len(t.steps),
                "parent_trace_id": t.parent_trace_id,
                "fork_step_id": t.fork_step_id,
                "created_at": t.created_at.isoformat(),
            }
            for t in traces
        ]
    }


@app.get("/api/traces/{trace_id}")
async def get_trace(trace_id: str):
    trace = recorder.get_trace(trace_id)
    if not trace:
        raise HTTPException(404, "Trace not found")
    return {
        "id": trace.id,
        "agent_name": trace.agent_name,
        "task": trace.task,
        "status": trace.status.value,
        "parent_trace_id": trace.parent_trace_id,
        "fork_step_id": trace.fork_step_id,
        "steps": [json.loads(s.model_dump_json()) for s in trace.steps],
        "created_at": trace.created_at.isoformat(),
        "completed_at": trace.completed_at.isoformat() if trace.completed_at else None,
    }


@app.post("/api/traces/{trace_id}/replay")
async def replay_trace(trace_id: str, req: ReplayRequest):
    trace = recorder.get_trace(trace_id)
    if not trace:
        raise HTTPException(404, "Trace not found")

    asyncio.create_task(replay_engine.replay(trace_id, req.speed))
    return {"status": "replaying", "trace_id": trace_id}


@app.post("/api/traces/{trace_id}/branch")
async def branch_trace(trace_id: str, req: BranchRequest):
    trace = recorder.get_trace(trace_id)
    if not trace:
        raise HTTPException(404, "Trace not found")

    agent_fn = AGENTS.get(trace.agent_name)
    if not agent_fn:
        raise HTTPException(400, f"Unknown agent: {trace.agent_name}")

    async def _branch():
        await replay_engine.branch(
            trace_id=trace_id,
            fork_step_id=req.fork_step_id,
            new_context=req.new_context,
            agent_runner=agent_fn,
        )

    asyncio.create_task(_branch())

    return {
        "status": "branching",
        "parent_trace_id": trace_id,
        "fork_step_id": req.fork_step_id,
        "new_context": req.new_context,
    }


@app.get("/api/traces/{trace_a_id}/diff/{trace_b_id}")
async def diff_traces(trace_a_id: str, trace_b_id: str):
    result = diff_engine.compare(trace_a_id, trace_b_id)
    return json.loads(result.model_dump_json())


# ── Run ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
