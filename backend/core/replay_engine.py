"""
Replay & Branch Engine — the time-travel core of AgentReplay.

- replay(): Step through a recorded execution
- branch(): Fork from any step with new context and re-run
"""
import asyncio
from typing import Optional
from .models import Trace, TraceStep, TraceStatus, StepType
from .recorder import AgentRecorder


class ReplayEngine:
    def __init__(self, recorder: AgentRecorder):
        self.recorder = recorder

    async def replay(self, trace_id: str, speed: float = 1.0) -> Optional[Trace]:
        """
        Replay an entire trace step-by-step via WebSocket.
        Speed: 1.0 = real-time, 2.0 = 2x faster, etc.
        """
        original = self.recorder.get_trace(trace_id)
        if not original:
            return None

        # Broadcast replay-start event
        await self.recorder.ws.broadcast({
            "event": "replay_start",
            "trace_id": trace_id,
            "total_steps": len(original.steps),
        })

        for i, step in enumerate(original.steps):
            await self.recorder.ws.broadcast({
                "event": "replay_step",
                "trace_id": trace_id,
                "step_index": i,
                "step": step.model_dump(),
            })
            await asyncio.sleep(0.8 / speed)

        await self.recorder.ws.broadcast({
            "event": "replay_complete",
            "trace_id": trace_id,
        })

        return original

    async def branch(
        self,
        trace_id: str,
        fork_step_id: str,
        new_context: str,
        agent_runner,  # callable(task, recorder, trace) -> runs the agent
    ) -> Optional[Trace]:
        """
        Fork execution at a specific step.
        Copies steps up to fork point, then re-runs the agent with modified context.
        """
        original = self.recorder.get_trace(trace_id)
        if not original:
            return None

        # Create new branched trace
        branch_trace = self.recorder.create_trace(
            agent_name=original.agent_name,
            task=f"{original.task} [BRANCHED: {new_context}]",
            parent_trace_id=trace_id,
            fork_step_id=fork_step_id,
        )

        # Copy steps up to (but not including) the fork point
        steps_to_copy = original.get_steps_until(fork_step_id)
        # Exclude the fork step itself (we'll replace it)
        if steps_to_copy:
            steps_to_copy = steps_to_copy[:-1]

        for step in steps_to_copy:
            copied = TraceStep(
                trace_id=branch_trace.id,
                parent_id=step.parent_id,
                step_type=step.step_type,
                content=step.content,
                tool_name=step.tool_name,
                tool_args=step.tool_args,
                metadata={**step.metadata, "copied_from": step.id},
            )
            branch_trace.steps.append(copied)
            await self.recorder.ws.broadcast({
                "event": "new_step",
                "trace_id": branch_trace.id,
                "step": copied.model_dump(),
            })

        # Broadcast that we're forking
        await self.recorder.ws.broadcast({
            "event": "branch_fork",
            "original_trace_id": trace_id,
            "branch_trace_id": branch_trace.id,
            "fork_step_id": fork_step_id,
            "new_context": new_context,
        })

        # Build conversation history from copied steps for the agent
        history = self._build_history_from_steps(steps_to_copy, new_context)

        # Re-run agent from fork point with new context
        try:
            await agent_runner(
                task=original.task,
                recorder=self.recorder,
                trace=branch_trace,
                history=history,
                injected_context=new_context,
            )
            await self.recorder.complete_trace(branch_trace.id, TraceStatus.COMPLETED)
        except Exception as e:
            await self.recorder.record_step(
                branch_trace.id,
                StepType.ERROR,
                f"Branch execution failed: {str(e)}",
            )
            await self.recorder.complete_trace(branch_trace.id, TraceStatus.FAILED)

        return branch_trace

    @staticmethod
    def _build_history_from_steps(steps: list[TraceStep], new_context: str) -> list[dict]:
        """Convert trace steps back into a conversation history for the LLM."""
        history = []
        for step in steps:
            if step.step_type == StepType.THOUGHT:
                history.append({"role": "assistant", "content": step.content})
            elif step.step_type == StepType.TOOL_CALL:
                history.append({
                    "role": "assistant",
                    "content": f"[Tool Call: {step.tool_name}({step.tool_args})]",
                })
            elif step.step_type == StepType.OBSERVATION:
                history.append({"role": "user", "content": f"Observation: {step.content}"})

        if new_context:
            history.append({
                "role": "user",
                "content": f"IMPORTANT NEW CONTEXT: {new_context}",
            })

        return history
