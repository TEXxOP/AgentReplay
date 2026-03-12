"""
Diff Engine — compare two execution traces side-by-side.
Finds the divergence point and highlights differences.
"""
from .models import Trace, TraceStep, DiffResult
from .recorder import AgentRecorder


class DiffEngine:
    def __init__(self, recorder: AgentRecorder):
        self.recorder = recorder

    def compare(self, trace_a_id: str, trace_b_id: str) -> DiffResult:
        """
        Compare two traces step-by-step.
        Returns the divergence point and all steps from both traces.
        """
        trace_a = self.recorder.get_trace(trace_a_id)
        trace_b = self.recorder.get_trace(trace_b_id)

        if not trace_a or not trace_b:
            return DiffResult(
                trace_a_id=trace_a_id,
                trace_b_id=trace_b_id,
                summary="One or both traces not found.",
            )

        # Find divergence point
        divergence_idx = 0
        min_len = min(len(trace_a.steps), len(trace_b.steps))

        for i in range(min_len):
            step_a = trace_a.steps[i]
            step_b = trace_b.steps[i]
            if step_a.step_type != step_b.step_type or step_a.content != step_b.content:
                divergence_idx = i
                break
        else:
            divergence_idx = min_len

        # Build summary
        summary = self._build_summary(trace_a, trace_b, divergence_idx)

        return DiffResult(
            trace_a_id=trace_a_id,
            trace_b_id=trace_b_id,
            divergence_step_index=divergence_idx,
            steps_a=trace_a.steps,
            steps_b=trace_b.steps,
            summary=summary,
        )

    @staticmethod
    def _build_summary(trace_a: Trace, trace_b: Trace, div_idx: int) -> str:
        total_a = len(trace_a.steps)
        total_b = len(trace_b.steps)
        shared = div_idx

        lines = [
            f"Trace A ({trace_a.id[:8]}): {total_a} steps, status={trace_a.status.value}",
            f"Trace B ({trace_b.id[:8]}): {total_b} steps, status={trace_b.status.value}",
            f"Shared steps: {shared}",
            f"Divergence at step {div_idx}",
        ]

        if div_idx < total_a and div_idx < total_b:
            step_a = trace_a.steps[div_idx]
            step_b = trace_b.steps[div_idx]
            lines.append(f"  A chose: [{step_a.step_type.value}] {step_a.content[:80]}")
            lines.append(f"  B chose: [{step_b.step_type.value}] {step_b.content[:80]}")

        # Check outcomes
        def _get_outcome(trace: Trace) -> str:
            for step in reversed(trace.steps):
                if step.step_type.value in ("final_answer", "error"):
                    return f"{step.step_type.value}: {step.content[:100]}"
            return trace.status.value

        lines.append(f"Outcome A: {_get_outcome(trace_a)}")
        lines.append(f"Outcome B: {_get_outcome(trace_b)}")

        return "\n".join(lines)
