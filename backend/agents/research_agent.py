"""
Research Agent — a demo agent that researches topics using simulated web tools.
Uses Groq (Llama 3.3 70B) for fast AI reasoning, with controlled tool outputs.
Includes deliberate "failure modes" to showcase AgentReplay's value.
"""
import json
import random
import asyncio
import httpx
from typing import Optional
from backend.core.models import StepType, Trace, TraceStatus
from backend.core.recorder import AgentRecorder
from backend.config import GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL, STEP_DELAY

# ── LLM Call (Groq) ─────────────────────────────────────────

async def _call_llm(prompt: str, history: list[dict] | None = None) -> str:
    """Call Groq API for reasoning. Falls back to scripted responses if no key."""
    if GROQ_API_KEY:
        messages = []
        if history:
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": prompt})

        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        f"{GROQ_BASE_URL}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {GROQ_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": GROQ_MODEL,
                            "messages": messages,
                            "temperature": 0.7,
                            "max_tokens": 1024,
                        },
                    )
                    if resp.status_code == 429:
                        wait = (attempt + 1) * 3
                        print(f"  ⏳ Groq rate limit, retrying in {wait}s (attempt {attempt + 1}/3)")
                        await asyncio.sleep(wait)
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                if attempt < 2:
                    await asyncio.sleep(2)
                    continue
                print(f"  ❌ LLM call failed: {e}")
                return _scripted_response(prompt)

        return _scripted_response(prompt)

    return _scripted_response(prompt)


def _scripted_response(prompt: str) -> str:
    """Fallback scripted responses when no API key is configured."""
    prompt_lower = prompt.lower()
    if "what action" in prompt_lower or "next step" in prompt_lower:
        return json.dumps({
            "thought": "I should search for more information on this topic.",
            "action": "web_search",
            "action_input": "latest research findings"
        })
    return json.dumps({
        "thought": "Based on my research, I can now provide a comprehensive answer.",
        "action": "final_answer",
        "action_input": "Here is a synthesized summary based on multiple sources..."
    })


# ── Simulated Tools ─────────────────────────────────────────

SEARCH_RESULTS = {
    "quantum computing applications": [
        {"title": "Quantum Computing in Drug Discovery — Nature 2025", "snippet": "Quantum algorithms show 40x speedup in molecular simulation for drug candidates."},
        {"title": "Post-Quantum Cryptography Standards Released", "snippet": "NIST finalizes 4 post-quantum encryption algorithms for government use."},
        {"title": "Google Willow chip achieves 105 qubits", "snippet": "New quantum processor demonstrates error correction below threshold."},
    ],
    "AI security vulnerabilities": [
        {"title": "Prompt Injection Attacks on LLM Agents", "snippet": "New attack vectors discovered that can hijack autonomous AI agents mid-task."},
        {"title": "Model Poisoning in Federated Learning", "snippet": "Researchers demonstrate how malicious participants can corrupt shared models."},
        {"title": "Adversarial attacks on RAG systems", "snippet": "Retrieved documents can be crafted to manipulate AI outputs systematically."},
    ],
}

DEFAULT_SEARCH = [
    {"title": "Comprehensive Overview — Wikipedia", "snippet": "A detailed overview of the topic covering key aspects and recent developments."},
    {"title": "Latest Research Paper — arXiv 2025", "snippet": "Novel approaches and methodologies for solving current challenges in this field."},
    {"title": "Industry Analysis — TechCrunch", "snippet": "Market trends and expert opinions on future developments."},
]

PAGE_CONTENT = {
    "Quantum Computing in Drug Discovery": "Quantum computing leverages superposition and entanglement to explore molecular configurations exponentially faster. Recent advances with error-corrected qubits allow simulation of molecules with up to 100 atoms, previously impossible classically. Key applications include protein folding prediction, drug-target interaction modeling, and toxicity screening. IBM and Google have demonstrated practical quantum advantage for specific chemistry problems.",
    "Prompt Injection Attacks on LLM Agents": "Prompt injection remains the #1 vulnerability in LLM-powered agents. Attackers can embed malicious instructions in data the agent processes (indirect injection). In 2025, researchers demonstrated 'agent hijacking' — where injected prompts redirect autonomous agents to perform unintended actions, exfiltrate data, or bypass safety guardrails. Defenses include input sanitization, output validation, and sandboxed execution environments.",
}

DEFAULT_PAGE = "This page contains detailed information about the topic. Key findings include multiple perspectives from researchers and industry experts. The field is rapidly evolving with promising results in both theoretical and practical applications. Several challenges remain, including scalability, reliability, and ethical considerations."


async def web_search(query: str) -> str:
    for key, results in SEARCH_RESULTS.items():
        if any(word in query.lower() for word in key.split()):
            return json.dumps(results, indent=2)
    return json.dumps(DEFAULT_SEARCH, indent=2)


async def read_page(title: str) -> str:
    for key, content in PAGE_CONTENT.items():
        if any(word.lower() in title.lower() for word in key.split()[:3]):
            return content
    return DEFAULT_PAGE


async def summarize(text: str) -> str:
    return await _call_llm(f"Summarize the following in 2-3 sentences:\n\n{text}")


TOOLS = {
    "web_search": web_search,
    "read_page": read_page,
    "summarize": summarize,
}


# ── Agent System Prompt ─────────────────────────────────────

SYSTEM_PROMPT = """You are a research agent. Your task is to research topics by searching the web, reading results, and synthesizing answers.

At each step, respond with ONLY a JSON object (no markdown, no extra text):
{
    "thought": "Your reasoning about what to do next",
    "action": "web_search" | "read_page" | "summarize" | "final_answer",
    "action_input": "The input for the action"
}

Available tools:
- web_search(query): Search the web for information
- read_page(title): Read a specific search result in detail
- summarize(text): Summarize a long text
- final_answer: Provide your final synthesized answer (action_input = your answer)

Research thoroughly before giving a final answer. Use at least 2 tool calls.
"""


# ── Run Agent ────────────────────────────────────────────────

async def run_research_agent(
    task: str,
    recorder: AgentRecorder,
    trace: Trace,
    history: list[dict] | None = None,
    injected_context: str | None = None,
) -> str:
    """
    Run the research agent with full recording.
    Used for both fresh runs and branched re-runs.
    """
    messages = history or []
    if not messages:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Research this topic: {task}"},
        ]

    if injected_context:
        messages.append({
            "role": "user",
            "content": f"IMPORTANT CORRECTION: {injected_context}. Adjust your approach based on this.",
        })

    parent_step_id = trace.steps[-1].id if trace.steps else None
    max_steps = 8

    for step_num in range(max_steps):
        # Delay between steps to avoid Gemini free-tier rate limits
        if step_num > 0:
            await asyncio.sleep(STEP_DELAY)

        # Ask LLM for next action
        prompt = SYSTEM_PROMPT + "\n\n" + "\n".join(
            f"{m['role']}: {m['content']}" for m in messages[-6:]
        )
        prompt += "\n\nWhat is your next action? Respond with ONLY JSON:"

        raw_response = await _call_llm(prompt, messages)

        # Parse the response
        try:
            # Extract JSON from response (handle markdown wrapping)
            json_str = raw_response
            if "```" in json_str:
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            parsed = json.loads(json_str.strip())
        except (json.JSONDecodeError, IndexError):
            parsed = {
                "thought": raw_response[:200],
                "action": "final_answer",
                "action_input": raw_response,
            }

        thought = parsed.get("thought", "Thinking...")
        action = parsed.get("action", "final_answer")
        action_input = parsed.get("action_input", "")

        # Record the thought
        thought_step = await recorder.record_step(
            trace.id, StepType.THOUGHT, thought, parent_id=parent_step_id,
        )

        if action == "final_answer":
            # Record final answer
            await recorder.record_step(
                trace.id, StepType.FINAL_ANSWER, action_input, parent_id=thought_step.id,
            )
            await recorder.complete_trace(trace.id)
            return action_input

        # Record tool call
        tool_step = await recorder.record_step(
            trace.id, StepType.TOOL_CALL, f"Calling {action}",
            tool_name=action, tool_args={"input": action_input},
            parent_id=thought_step.id,
        )

        # Execute tool
        tool_fn = TOOLS.get(action)
        if tool_fn:
            try:
                result = await tool_fn(action_input)
            except Exception as e:
                result = f"Tool error: {str(e)}"
                await recorder.record_step(
                    trace.id, StepType.ERROR, result, parent_id=tool_step.id,
                )
                parent_step_id = tool_step.id
                continue
        else:
            result = f"Unknown tool: {action}"

        # Record observation
        obs_step = await recorder.record_step(
            trace.id, StepType.OBSERVATION, result, parent_id=tool_step.id,
        )

        parent_step_id = obs_step.id
        messages.append({"role": "assistant", "content": json.dumps(parsed)})
        messages.append({"role": "user", "content": f"Tool result:\n{result}\n\nWhat is your next action?"})

    # Max steps reached
    await recorder.record_step(
        trace.id, StepType.ERROR,
        "Maximum steps reached without final answer.",
        parent_id=parent_step_id,
    )
    await recorder.complete_trace(trace.id, TraceStatus.FAILED)
    return "Research incomplete — max steps reached."
