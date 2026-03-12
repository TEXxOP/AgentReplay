/**
 * Timeline — Vertical timeline showing each agent step with connector dots
 * Supports live streaming, replay highlighting, and step actions (branch/expand)
 */

let currentSteps = [];
let currentTraceId = null;

export function renderTimeline(steps, traceId) {
  currentSteps = steps || [];
  currentTraceId = traceId;

  const container = document.getElementById('center-panel');
  container.classList.add('panel');

  if (!traceId || steps.length === 0) {
    container.innerHTML = `
      <div class="panel-header">
        <span class="panel-title">📡 Execution Timeline</span>
        <div class="replay-controls-inline" id="replay-controls" style="display:none"></div>
      </div>
      <div class="panel-body timeline-container">
        <div class="timeline-empty">
          <div class="timeline-empty-icon">⏪</div>
          <div class="timeline-empty-text">Run an agent or select a trace to view its execution</div>
        </div>
      </div>
    `;
    return;
  }

  container.innerHTML = `
    <div class="panel-header">
      <span class="panel-title">📡 Execution Timeline</span>
      <span class="panel-title" style="font-size:10px; opacity:0.6">${steps.length} steps</span>
    </div>
    <div class="panel-body timeline-container" id="timeline-body">
      ${steps.map((step, i) => renderStep(step, i, steps.length)).join('')}
    </div>
    <div class="replay-bar">
      <button class="replay-btn" id="btn-replay" title="Replay">⏪</button>
      <button class="replay-btn" id="btn-replay-fast" title="Fast Replay (2x)">⏩</button>
      <div class="replay-progress">
        <div class="replay-progress-fill" id="replay-progress-fill"></div>
      </div>
      <span class="replay-step-count" id="replay-counter">—</span>
    </div>
  `;

  bindStepEvents();
  bindReplayEvents();
  scrollToBottom();
}

export function addTimelineStep(step) {
  currentSteps.push(step);
  const body = document.getElementById('timeline-body');
  if (!body) {
    // Timeline not rendered yet, do full render
    renderTimeline(currentSteps, currentTraceId);
    return;
  }

  // Remove empty state if present
  const empty = body.querySelector('.timeline-empty');
  if (empty) empty.remove();

  // Update step count
  const panel = document.getElementById('center-panel');
  const counter = panel.querySelector('.panel-header .panel-title:last-child');
  if (counter) counter.textContent = `${currentSteps.length} steps`;

  // Append new step
  const div = document.createElement('div');
  div.innerHTML = renderStep(step, currentSteps.length - 1, currentSteps.length);
  const stepEl = div.firstElementChild;
  body.appendChild(stepEl);

  bindSingleStepEvents(stepEl);
  scrollToBottom();
}

export function clearTimeline() {
  currentSteps = [];
  currentTraceId = null;
}

export function highlightReplayStep(index) {
  const items = document.querySelectorAll('.step-item');
  items.forEach((el, i) => {
    const card = el.querySelector('.step-card');
    if (i === index) {
      card.classList.add('active');
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    } else {
      card.classList.remove('active');
    }
  });

  const fill = document.getElementById('replay-progress-fill');
  const counter = document.getElementById('replay-counter');
  if (fill && items.length > 0) {
    fill.style.width = `${((index + 1) / items.length) * 100}%`;
  }
  if (counter) {
    counter.textContent = `${index + 1} / ${items.length}`;
  }
}

// ── Render Helpers ──────────────────────────────────────────

function renderStep(step, index, total) {
  const type = step.step_type;
  const isLast = index === total - 1;
  const time = new Date(step.timestamp).toLocaleTimeString();
  const typeLabels = {
    thought: '💭 Thought',
    tool_call: '🔧 Tool Call',
    observation: '👁 Observation',
    final_answer: '✅ Final Answer',
    error: '❌ Error',
  };

  let contentHtml = escapeHtml(step.content);
  if (type === 'tool_call' && step.tool_name) {
    contentHtml = `<div class="step-tool-name">→ ${escapeHtml(step.tool_name)}(${step.tool_args ? escapeHtml(JSON.stringify(step.tool_args)) : ''})</div>${contentHtml}`;
  }

  // Try to format JSON content nicely
  if (type === 'observation') {
    try {
      const parsed = JSON.parse(step.content);
      contentHtml = `<pre style="font-size:11px; overflow-x:auto;">${escapeHtml(JSON.stringify(parsed, null, 2))}</pre>`;
    } catch {
      // Not JSON, keep as is
    }
  }

  return `
    <div class="step-item step-type-${type}" data-step-id="${step.id}" data-step-index="${index}">
      <div class="step-connector">
        <div class="step-dot"></div>
        ${!isLast ? '<div class="step-line"></div>' : ''}
      </div>
      <div class="step-card">
        <div class="step-header">
          <span class="step-type-label">${typeLabels[type] || type}</span>
          <span class="step-time">${time}</span>
        </div>
        <div class="step-content">${contentHtml}</div>
        <div class="step-actions">
          <button class="step-action-btn expand-btn" data-step-id="${step.id}">Expand</button>
          ${type !== 'final_answer' && type !== 'error' ? `
            <button class="step-action-btn branch-btn" data-step-id="${step.id}">🌿 Branch from here</button>
          ` : ''}
        </div>
      </div>
    </div>
  `;
}

function scrollToBottom() {
  const body = document.getElementById('timeline-body');
  if (body) {
    requestAnimationFrame(() => {
      body.scrollTop = body.scrollHeight;
    });
  }
}

// ── Event Binding ──────────────────────────────────────────

function bindStepEvents() {
  document.querySelectorAll('.step-item').forEach(el => bindSingleStepEvents(el));
}

function bindSingleStepEvents(el) {
  // Expand
  const expandBtn = el.querySelector('.expand-btn');
  if (expandBtn) {
    expandBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const content = el.querySelector('.step-content');
      content.classList.toggle('expanded');
      expandBtn.textContent = content.classList.contains('expanded') ? 'Collapse' : 'Expand';
    });
  }

  // Branch
  const branchBtn = el.querySelector('.branch-btn');
  if (branchBtn) {
    branchBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      showBranchModal(branchBtn.dataset.stepId);
    });
  }

  // Select step
  el.querySelector('.step-card').addEventListener('click', () => {
    document.querySelectorAll('.step-card').forEach(c => c.classList.remove('active'));
    el.querySelector('.step-card').classList.add('active');
    window.__selectStep(el.dataset.stepId);
  });
}

function bindReplayEvents() {
  const replayBtn = document.getElementById('btn-replay');
  const replayFastBtn = document.getElementById('btn-replay-fast');

  if (replayBtn) {
    replayBtn.addEventListener('click', () => {
      if (currentTraceId) window.__replayTrace(currentTraceId, 1.0);
    });
  }

  if (replayFastBtn) {
    replayFastBtn.addEventListener('click', () => {
      if (currentTraceId) window.__replayTrace(currentTraceId, 2.0);
    });
  }
}

// ── Branch Modal ───────────────────────────────────────────

function showBranchModal(stepId) {
  const modal = document.createElement('div');
  modal.className = 'branch-modal';
  modal.innerHTML = `
    <div class="branch-modal-content">
      <h3>🌿 Branch Execution</h3>
      <p>Fork from this step and re-run with new context. The agent will take a different path based on your correction.</p>
      <textarea id="branch-context" placeholder="Enter new context or correction...&#10;e.g. 'Focus on the security implications instead'&#10;or 'The bug is actually a race condition, not off-by-one'"></textarea>
      <div class="branch-modal-actions">
        <button class="btn-cancel" id="branch-cancel">Cancel</button>
        <button class="btn-branch" id="branch-confirm">🌿 Branch & Re-run</button>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  modal.querySelector('#branch-cancel').addEventListener('click', () => modal.remove());
  modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });

  modal.querySelector('#branch-confirm').addEventListener('click', () => {
    const ctx = modal.querySelector('#branch-context').value.trim();
    if (!ctx) return;
    window.__branchFromStep(currentTraceId, stepId, ctx);
    modal.remove();
  });

  modal.querySelector('#branch-context').focus();
}

function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = String(str);
  return div.innerHTML;
}
