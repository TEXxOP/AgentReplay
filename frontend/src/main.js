/**
 * AgentReplay Dashboard — Main Entry Point
 * Initializes WebSocket, renders all panels, handles state
 */

import { renderControlPanel } from './components/ControlPanel.js';
import { renderTimeline, addTimelineStep, clearTimeline, highlightReplayStep } from './components/Timeline.js';
import { renderTraceList, updateTraceList } from './components/TraceList.js';
import { renderDetailPanel, showStepDetail, showDiffView } from './components/DetailPanel.js';

// ── App State ──────────────────────────────────────────────

const state = {
  ws: null,
  connected: false,
  traces: [],
  activeTraceId: null,
  activeStepId: null,
  selectedAgent: 'research',
  replaying: false,
};

window.__state = state; // Expose for components

// ── WebSocket ──────────────────────────────────────────────

function connectWebSocket() {
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
  const wsUrl = `${protocol}://${location.hostname}:8000/ws`;

  state.ws = new WebSocket(wsUrl);

  state.ws.onopen = () => {
    state.connected = true;
    updateConnectionStatus(true);
    console.log('🔌 WebSocket connected');
  };

  state.ws.onclose = () => {
    state.connected = false;
    updateConnectionStatus(false);
    console.log('🔌 WebSocket disconnected — reconnecting in 3s');
    setTimeout(connectWebSocket, 3000);
  };

  state.ws.onerror = () => {
    state.ws.close();
  };

  state.ws.onmessage = (evt) => {
    try {
      const data = JSON.parse(evt.data);
      handleWSEvent(data);
    } catch (e) {
      console.error('WS parse error:', e);
    }
  };
}

function updateConnectionStatus(connected) {
  const badge = document.getElementById('connection-status');
  const text = badge.querySelector('.status-text');
  if (connected) {
    badge.classList.add('connected');
    badge.classList.remove('disconnected');
    text.textContent = 'Connected';
  } else {
    badge.classList.remove('connected');
    badge.classList.add('disconnected');
    text.textContent = 'Disconnected';
  }
}

// ── WebSocket Event Handler ────────────────────────────────

function handleWSEvent(data) {
  switch (data.event) {
    case 'new_step':
      if (data.trace_id === state.activeTraceId) {
        addTimelineStep(data.step);
      }
      // Refresh trace list (step count update)
      refreshTraces();
      break;

    case 'trace_complete':
      refreshTraces();
      break;

    case 'replay_start':
      state.replaying = true;
      break;

    case 'replay_step':
      if (data.trace_id === state.activeTraceId) {
        highlightReplayStep(data.step_index);
      }
      break;

    case 'replay_complete':
      state.replaying = false;
      break;

    case 'branch_fork':
      refreshTraces();
      // Auto-select the new branch
      setTimeout(() => {
        if (data.branch_trace_id) {
          selectTrace(data.branch_trace_id);
        }
      }, 500);
      break;

    default:
      console.log('Unknown WS event:', data.event);
  }
}

// ── API Helpers ────────────────────────────────────────────

async function api(method, path, body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(`http://${location.hostname}:8000${path}`, opts);
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err);
  }
  return res.json();
}

window.__api = api; // Expose for components

// ── Actions ────────────────────────────────────────────────

async function runAgent(agent, task) {
  try {
    const result = await api('POST', '/api/agents/run', { agent, task });
    state.activeTraceId = result.trace_id;
    clearTimeline();
    renderTimeline([], state.activeTraceId);
    await refreshTraces();
  } catch (e) {
    console.error('Run agent error:', e);
    alert('Failed to run agent. Is the backend running?');
  }
}

window.__runAgent = runAgent;

async function selectTrace(traceId) {
  state.activeTraceId = traceId;
  try {
    const trace = await api('GET', `/api/traces/${traceId}`);
    clearTimeline();
    renderTimeline(trace.steps, traceId);
    updateTraceList(state.traces, traceId);
    renderDetailPanel(trace);
  } catch (e) {
    console.error('Select trace error:', e);
  }
}

window.__selectTrace = selectTrace;

async function replayTrace(traceId, speed = 1.0) {
  try {
    await api('POST', `/api/traces/${traceId}/replay`, { speed });
  } catch (e) {
    console.error('Replay error:', e);
  }
}

window.__replayTrace = replayTrace;

async function branchFromStep(traceId, stepId, newContext) {
  try {
    await api('POST', `/api/traces/${traceId}/branch`, {
      fork_step_id: stepId,
      new_context: newContext,
    });
  } catch (e) {
    console.error('Branch error:', e);
  }
}

window.__branchFromStep = branchFromStep;

async function diffTraces(traceAId, traceBId) {
  try {
    const result = await api('GET', `/api/traces/${traceAId}/diff/${traceBId}`);
    showDiffView(result);
  } catch (e) {
    console.error('Diff error:', e);
  }
}

window.__diffTraces = diffTraces;

async function refreshTraces() {
  try {
    const result = await api('GET', '/api/traces');
    state.traces = result.traces;
    updateTraceList(state.traces, state.activeTraceId);
  } catch (e) {
    // Backend might not be up yet
  }
}

// ── Select Step ────────────────────────────────────────────

function selectStep(stepId) {
  state.activeStepId = stepId;
}

window.__selectStep = selectStep;

// ── Check Health ───────────────────────────────────────────

async function checkHealth() {
  try {
    const h = await api('GET', '/api/health');
    const smBadge = document.getElementById('supermemory-status');
    const smText = smBadge.querySelector('.status-text');
    smText.textContent = h.supermemory === 'connected' ? 'SuperMemory ✓' : 'Local Mode';
  } catch (e) {
    // Backend not running
  }
}

// ── Init ───────────────────────────────────────────────────

function init() {
  renderControlPanel(document.getElementById('control-panel'));
  renderTraceList(document.getElementById('trace-list-panel'), [], null);
  renderTimeline([], null);
  renderDetailPanel(null);

  connectWebSocket();
  checkHealth();

  // Poll traces every 3 seconds
  setInterval(refreshTraces, 3000);
}

document.addEventListener('DOMContentLoaded', init);
