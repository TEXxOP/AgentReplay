# AgentReplay — Time-Travel Debugging for AI Agents

> **Record. Replay. Branch. Debug AI reasoning like Git for thought.**

When AI agents fail at complex multi-step tasks, it's nearly impossible to understand *why*. AgentReplay uses [SuperMemory](https://supermemory.ai) to record every decision an AI agent makes, then lets you **replay, branch from any point, and compare** execution paths — like Git, but for AI agent reasoning.

![AgentReplay Dashboard](https://img.shields.io/badge/Status-Hackathon_Submission-blue)
![Python](https://img.shields.io/badge/Python-3.11+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Key Features

- **Flight Recorder** — Automatically captures every thought, tool call, observation, and answer from any AI agent
- **Time-Travel Replay** — Step through a recorded execution at any speed, like a video debugger
- **Branch & Fork** — Click any step to fork execution with new context and see how different decisions lead to different outcomes
- **Diff Comparison** — Side-by-side comparison showing exactly where two execution paths diverge
- **SuperMemory Knowledge Graph** — All traces are stored as interconnected memories for cross-session pattern matching
- **Real-Time Dashboard** — Live WebSocket streaming shows agent activity as it happens

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Frontend (Vite)                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ Control  │ │ Timeline │ │  Detail Panel    │ │
│  │  Panel   │ │  (Live)  │ │  + Diff Viewer   │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
│          ▲ WebSocket + REST API ▲                │
├─────────────────────────────────────────────────┤
│              Backend (FastAPI)                    │
│  ┌──────────────────────────────────────┐        │
│  │         AgentRecorder (Core)         │        │
│  │  Record → Replay → Branch → Diff    │        │
│  └──────────────┬───────────────────────┘        │
│                 │                                │
│  ┌──────────────▼───────────────────────┐        │
│  │          SuperMemory API             │        │
│  │   Knowledge Graph + RAG Storage      │        │
│  └──────────────────────────────────────┘        │
│                                                  │
│  ┌──────────────┐  ┌──────────────────┐          │
│  │ Research     │  │ Code Debug       │          │
│  │ Agent (Demo) │  │ Agent (Demo)     │          │
│  └──────────────┘  └──────────────────┘          │
└─────────────────────────────────────────────────┘
```

---

## How It Works

1. **Run an Agent** — Select a demo agent (Research or Debug) and provide a task
2. **Watch Live** — The execution timeline streams each step in real-time
3. **Spot the Problem** — When the agent makes a wrong decision, you can see exactly where
4. **Branch** — Click "Branch from here" on any step, provide new context, and re-run
5. **Compare** — Use the Diff Viewer to see exactly how the two execution paths diverged

---

## Setup & Run

### Prerequisites
- Python 3.11+
- Node.js 18+
- (Optional) SuperMemory API key from [supermemory.ai](https://supermemory.ai)
- (Optional) Gemini API key from [aistudio.google.com](https://aistudio.google.com)

### Installation

```bash
# Clone the repository
git clone https://github.com/<your-username>/agentreplay.git
cd agentreplay

# Copy environment variables
cp .env.example .env
# Edit .env and add your API keys (optional — works in local mode without them)

# Backend setup
python -m venv .venv
.venv/Scripts/pip install -r backend/requirements.txt   # Windows
# source .venv/bin/activate && pip install -r backend/requirements.txt  # Linux/Mac

# Frontend setup
cd frontend && npm install && cd ..
```

### Running

```bash
# Terminal 1: Start backend
.venv/Scripts/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Start frontend
cd frontend && npm run dev
```

Open **http://localhost:3000** in your browser.

---

## SuperMemory Integration

AgentReplay uses SuperMemory's Knowledge Graph as the persistence layer for execution traces:

| Relationship | Meaning |
|-------------|---------|
| **Extends** | Step A → Step B (sequential execution chain) |
| **Derives** | Branch step → Original step (fork relationship) |
| **Updates** | Re-run step → Original step (replay with changes) |

This enables:
- **Cross-session pattern matching** — Find similar failures across different agent runs
- **Long-term memory** — Agents learn from past mistakes stored in the knowledge graph
- **Persistent traces** — All executions survive server restarts

---

## Demo Agents

### Research Agent
Searches the web, reads pages, and synthesizes answers. Uses Gemini for real AI reasoning with simulated web tools for reliable demos.

**Try:** *"Research quantum computing applications in security"*

### Debug Agent
Analyzes buggy code, identifies issues, proposes fixes, and verifies them. Includes pre-built bug scenarios (off-by-one, null reference, race condition).

**Try:** *"Debug the off_by_one error in the find_max function"*

---

## Why This Project is Unique

1. **Creates a new category** — No one is building debugging infrastructure for AI agents
2. **SuperMemory is core to the product** — The knowledge graph IS the execution trace
3. **Incredible demo** — Watch an agent fail, time-travel to fix it live
4. **Picks-and-shovels for the agentic AI wave** — Every agent builder needs this

---

## Project Structure

```
agentreplay/
├── backend/
│   ├── main.py              # FastAPI server + WebSocket
│   ├── config.py            # API keys + configuration
│   ├── core/
│   │   ├── models.py        # TraceStep, Trace, DiffResult data models
│   │   ├── memory_client.py # SuperMemory API client
│   │   ├── recorder.py      # Flight recorder + WebSocket manager
│   │   ├── replay_engine.py # Time-travel + branching engine
│   │   └── diff_engine.py   # Trace comparison engine
│   └── agents/
│       ├── research_agent.py # Demo research agent
│       └── debug_agent.py    # Demo code debugger agent
├── frontend/
│   ├── index.html
│   ├── vite.config.js
│   └── src/
│       ├── main.js           # App entry + WebSocket + state
│       ├── styles.css         # Dark developer-tools theme
│       └── components/
│           ├── ControlPanel.js
│           ├── Timeline.js
│           ├── TraceList.js
│           └── DetailPanel.js
├── .env.example
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+ / FastAPI |
| Agent LLM | Google Gemini API |
| Memory & Traces | SuperMemory (Knowledge Graph + RAG) |
| Frontend | Vite + Vanilla JavaScript |
| Real-time | WebSocket |
| Styling | Custom CSS (Dark Dev-Tools Theme) |

---

## Theme

**Agentic AI** — Autonomous AI systems that can plan, reason, and execute tasks with minimal human intervention.

AgentReplay enables observability and debugging for these autonomous systems — making the "black box" of AI agent reasoning transparent, replayable, and improvable.

---

## License

MIT License — Feel free to use, modify, and distribute.

---

*Built for **Hack & Break: Generative AI & Cybersecurity Innovation Challenge** by IIT Bombay*
