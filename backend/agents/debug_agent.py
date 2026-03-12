"""
Code Debug Agent — a demo agent that analyzes buggy code and proposes fixes.
Shows how AgentReplay captures debugging workflows and enables branching to try
different fix strategies.
"""
import json
import asyncio
import httpx
from backend.core.models import StepType, Trace, TraceStatus
from backend.core.recorder import AgentRecorder
from backend.config import GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL, STEP_DELAY


# ── LLM Call (Groq) ─────────────────────────────────────────

async def _call_llm(prompt: str) -> str:
    if GROQ_API_KEY:
        messages = [{"role": "user", "content": prompt}]

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
                        print(f"  ⏳ Groq rate limit, retrying in {wait}s")
                        await asyncio.sleep(wait)
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                if attempt < 2:
                    await asyncio.sleep(2)
                    continue
                return _scripted_response(prompt)

        return _scripted_response(prompt)
    return _scripted_response(prompt)


def _scripted_response(prompt: str) -> str:
    p = prompt.lower()
    if "analyze" in p or "identify" in p:
        return json.dumps({
            "thought": "I can see a potential issue in the code logic.",
            "action": "analyze_code",
            "action_input": "Analyzing the code structure and logic flow"
        })
    if "fix" in p or "propose" in p:
        return json.dumps({
            "thought": "Based on the analysis, I'll propose a fix.",
            "action": "propose_fix",
            "action_input": "Apply boundary check before array access"
        })
    return json.dumps({
        "thought": "The fix has been verified successfully.",
        "action": "final_answer",
        "action_input": "Bug fixed: Added boundary check to prevent index out of range error."
    })


# ── Simulated Tools ─────────────────────────────────────────

BUGGY_CODE_SAMPLES = {
    "off_by_one": {
        "code": """def find_max(arr):
    max_val = arr[0]
    for i in range(1, len(arr) + 1):  # Bug: should be len(arr)
        if arr[i] > max_val:
            max_val = arr[i]
    return max_val""",
        "error": "IndexError: list index out of range",
        "analysis": "Off-by-one error: loop iterates to len(arr) + 1, but valid indices are 0 to len(arr)-1. The range should be range(1, len(arr)).",
        "fix": """def find_max(arr):
    max_val = arr[0]
    for i in range(1, len(arr)):  # Fixed: removed + 1
        if arr[i] > max_val:
            max_val = arr[i]
    return max_val""",
        "test_result": "All tests passed: find_max([3,1,4,1,5]) = 5 ✓",
    },
    "null_reference": {
        "code": """def get_user_email(users, user_id):
    user = users.get(user_id)
    return user['email']  # Bug: user might be None""",
        "error": "TypeError: 'NoneType' object is not subscriptable",
        "analysis": "Null reference error: users.get() returns None when key not found, but code directly accesses ['email'] without checking.",
        "fix": """def get_user_email(users, user_id):
    user = users.get(user_id)
    if user is None:
        return None
    return user['email']""",
        "test_result": "All tests passed: handles missing users correctly ✓",
    },
    "race_condition": {
        "code": """import threading
counter = 0
def increment():
    global counter
    for _ in range(100000):
        counter += 1  # Bug: not thread-safe""",
        "error": "Expected counter=200000, got counter=143762 (race condition)",
        "analysis": "Race condition: counter += 1 is not atomic. Multiple threads read/write simultaneously, causing lost updates. Need a lock or atomic operation.",
        "fix": """import threading
counter = 0
lock = threading.Lock()
def increment():
    global counter
    for _ in range(100000):
        with lock:
            counter += 1""",
        "test_result": "All tests passed: counter=200000 consistently ✓",
    },
}


async def analyze_code(code_or_key: str) -> str:
    for key, sample in BUGGY_CODE_SAMPLES.items():
        if key in code_or_key.lower() or any(word in code_or_key.lower() for word in key.split("_")):
            return json.dumps({
                "code": sample["code"],
                "error": sample["error"],
                "analysis": sample["analysis"],
            }, indent=2)
    # Default to off_by_one
    sample = BUGGY_CODE_SAMPLES["off_by_one"]
    return json.dumps({
        "code": sample["code"],
        "error": sample["error"],
        "analysis": sample["analysis"],
    }, indent=2)


async def propose_fix(analysis: str) -> str:
    for key, sample in BUGGY_CODE_SAMPLES.items():
        if any(word in analysis.lower() for word in key.split("_")):
            return json.dumps({
                "fixed_code": sample["fix"],
                "explanation": sample["analysis"],
            }, indent=2)
    sample = BUGGY_CODE_SAMPLES["off_by_one"]
    return json.dumps({
        "fixed_code": sample["fix"],
        "explanation": sample["analysis"],
    }, indent=2)


async def test_fix(code: str) -> str:
    for key, sample in BUGGY_CODE_SAMPLES.items():
        if any(line.strip() in code for line in sample["fix"].split("\n") if line.strip()):
            return sample["test_result"]
    return "Tests passed with warnings: edge cases may need additional coverage."


async def read_docs(query: str) -> str:
    return "Python documentation: Always validate inputs before processing. Use .get() with default values for dictionary access. Prefer 'ask forgiveness' (try/except) over 'ask permission' (if checks) in Python."


TOOLS = {
    "analyze_code": analyze_code,
    "propose_fix": propose_fix,
    "test_fix": test_fix,
    "read_docs": read_docs,
}


# ── System Prompt ────────────────────────────────────────────

SYSTEM_PROMPT = """You are a code debugging agent. Your task is to analyze buggy code, identify the bug, propose a fix, and verify it.

At each step, respond with ONLY a JSON object:
{
    "thought": "Your reasoning about the bug",
    "action": "analyze_code" | "propose_fix" | "test_fix" | "read_docs" | "final_answer",
    "action_input": "Input for the action"
}

Available tools:
- analyze_code(description): Analyze code for bugs
- propose_fix(analysis): Propose a fix based on analysis
- test_fix(code): Run tests on the fixed code
- read_docs(topic): Read documentation for reference
- final_answer: Your final diagnosis and fix explanation

Follow this workflow: analyze → propose fix → test → report.
"""


# ── Run Agent ────────────────────────────────────────────────

async def run_debug_agent(
    task: str,
    recorder: AgentRecorder,
    trace: Trace,
    history: list[dict] | None = None,
    injected_context: str | None = None,
) -> str:
    messages = history or []
    if not messages:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Debug this issue: {task}"},
        ]

    if injected_context:
        messages.append({
            "role": "user",
            "content": f"IMPORTANT HINT: {injected_context}. Use this to improve your debugging.",
        })

    parent_step_id = trace.steps[-1].id if trace.steps else None
    max_steps = 8

    for step_num in range(max_steps):
        # Delay between steps to avoid Gemini free-tier rate limits
        if step_num > 0:
            await asyncio.sleep(STEP_DELAY)

        prompt = SYSTEM_PROMPT + "\n\n" + "\n".join(
            f"{m['role']}: {m['content']}" for m in messages[-6:]
        )
        prompt += "\n\nWhat is your next action? Respond with ONLY JSON:"

        raw_response = await _call_llm(prompt)

        try:
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

        thought = parsed.get("thought", "Analyzing...")
        action = parsed.get("action", "final_answer")
        action_input = parsed.get("action_input", "")

        thought_step = await recorder.record_step(
            trace.id, StepType.THOUGHT, thought, parent_id=parent_step_id,
        )

        if action == "final_answer":
            await recorder.record_step(
                trace.id, StepType.FINAL_ANSWER, action_input, parent_id=thought_step.id,
            )
            await recorder.complete_trace(trace.id)
            return action_input

        tool_step = await recorder.record_step(
            trace.id, StepType.TOOL_CALL, f"Calling {action}",
            tool_name=action, tool_args={"input": action_input},
            parent_id=thought_step.id,
        )

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

        obs_step = await recorder.record_step(
            trace.id, StepType.OBSERVATION, result, parent_id=tool_step.id,
        )

        parent_step_id = obs_step.id
        messages.append({"role": "assistant", "content": json.dumps(parsed)})
        messages.append({"role": "user", "content": f"Tool result:\n{result}\n\nWhat is your next action?"})

    await recorder.record_step(
        trace.id, StepType.ERROR,
        "Maximum steps reached.",
        parent_id=parent_step_id,
    )
    await recorder.complete_trace(trace.id, TraceStatus.FAILED)
    return "Debugging incomplete."
