"""
SuperMemory client — stores agent trace steps as memories in a knowledge graph.
Works in dual mode: local cache (always) + SuperMemory API (when key is available).
"""
import httpx
import json
from typing import Optional, List
from .models import TraceStep
from backend.config import SUPERMEMORY_API_KEY, SUPERMEMORY_BASE_URL


class MemoryClient:
    def __init__(self):
        self.api_key = SUPERMEMORY_API_KEY
        self.base_url = SUPERMEMORY_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        # Always-available local store (primary for demo speed)
        self._store: dict[str, TraceStep] = {}

    @property
    def is_connected(self) -> bool:
        return bool(self.api_key)

    # ── Store ────────────────────────────────────────────────
    async def store_step(self, step: TraceStep) -> str:
        """Store a trace step as a memory node. Returns memory id."""
        self._store[step.id] = step

        if not self.is_connected:
            return step.id

        content = self._step_to_content(step)
        payload = {
            "content": content,
            "metadata": {
                "trace_id": step.trace_id,
                "step_id": step.id,
                "parent_id": step.parent_id or "",
                "step_type": step.step_type.value,
                "tool_name": step.tool_name or "",
                "timestamp": step.timestamp.isoformat(),
            },
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self.base_url}/memories",
                    json=payload,
                    headers=self.headers,
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return data.get("id", step.id)
        except Exception:
            pass  # Fall back to local id

        return step.id

    # ── Search ───────────────────────────────────────────────
    async def search_similar(self, query: str, limit: int = 5) -> List[dict]:
        """Find similar past steps/failures via SuperMemory RAG search."""
        if not self.is_connected:
            return self._local_search(query, limit)

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self.base_url}/search",
                    json={"query": query, "limit": limit},
                    headers=self.headers,
                )
                if resp.status_code == 200:
                    return resp.json().get("results", [])
        except Exception:
            pass

        return self._local_search(query, limit)

    # ── Retrieve ─────────────────────────────────────────────
    def get_step(self, step_id: str) -> Optional[TraceStep]:
        return self._store.get(step_id)

    def get_trace_steps(self, trace_id: str) -> List[TraceStep]:
        return sorted(
            [s for s in self._store.values() if s.trace_id == trace_id],
            key=lambda s: s.timestamp,
        )

    # ── Helpers ──────────────────────────────────────────────
    @staticmethod
    def _step_to_content(step: TraceStep) -> str:
        prefix = f"[{step.step_type.value.upper()}]"
        if step.tool_name:
            prefix = f"[{step.step_type.value.upper()}:{step.tool_name}]"
        return f"{prefix} {step.content}"

    def _local_search(self, query: str, limit: int) -> List[dict]:
        """Simple keyword search over local store."""
        query_lower = query.lower()
        results = []
        for step in self._store.values():
            score = 0
            for word in query_lower.split():
                if word in step.content.lower():
                    score += 1
            if score > 0:
                results.append({"step": step.model_dump(), "score": score})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
