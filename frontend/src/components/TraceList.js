/**
 * TraceList — Sidebar list of all recorded traces
 */

export function renderTraceList(container, traces, activeTraceId) {
  container.classList.add('panel');
  container.innerHTML = `
    <div class="panel-header">
      <span class="panel-title"><i data-lucide="video" class="inline-icon"></i> Recorded Traces</span>
      <span class="panel-title" style="font-size:10px; opacity:0.6">${traces.length || 0}</span>
    </div>
    <div class="panel-body" id="trace-list-body">
      ${traces.length === 0 ? `
        <div class="detail-empty" style="padding: 20px 0">
          <div class="detail-empty-icon"><i data-lucide="video"></i></div>
          <div style="font-size:11px; color: var(--text-muted)">No traces yet.<br>Run an agent to start recording.</div>
        </div>
      ` : ''}
      ${traces.map(t => renderTraceItem(t, activeTraceId)).join('')}
    </div>
  `;

  // Click handlers
  container.querySelectorAll('.trace-item').forEach(el => {
    el.addEventListener('click', () => {
      window.__selectTrace(el.dataset.traceId);
    });
  });
}

export function updateTraceList(traces, activeTraceId) {
  const container = document.getElementById('trace-list-panel');
  if (container) {
    renderTraceList(container, traces, activeTraceId);
  }
}

function renderTraceItem(trace, activeTraceId) {
  const isActive = trace.id === activeTraceId;
  const isBranch = !!trace.parent_trace_id;
  const time = new Date(trace.created_at).toLocaleTimeString();

  return `
    <div class="trace-item ${isActive ? 'active' : ''}" data-trace-id="${trace.id}">
      <div class="trace-agent">
        <i data-lucide="${trace.agent_name === 'research' ? 'search' : 'bug'}" class="inline-icon"></i> ${trace.agent_name} agent
        ${isBranch ? '<span class="trace-branch-badge"><i data-lucide="git-branch" class="inline-icon-small"></i> branch</span>' : ''}
      </div>
      <div class="trace-task">${escapeHtml(trace.task)}</div>
      <div class="trace-meta">
        <span class="trace-status ${trace.status}">${trace.status}</span>
        <span>${trace.step_count} steps · ${time}</span>
      </div>
    </div>
  `;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
