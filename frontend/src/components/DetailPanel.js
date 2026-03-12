/**
 * DetailPanel — Right sidebar showing trace info, diff view, and step details
 */

export function renderDetailPanel(trace) {
  const container = document.getElementById('right-panel');
  container.classList.add('panel');

  if (!trace) {
    container.innerHTML = `
      <div class="panel-header">
        <span class="panel-title"><i data-lucide="clipboard-list" class="inline-icon"></i> Details</span>
      </div>
      <div class="panel-body">
        <div class="detail-empty">
          <div class="detail-empty-icon"><i data-lucide="search"></i></div>
          <div style="font-size:12px">Select a trace to view details</div>
          <div style="font-size:11px; margin-top:4px; color: var(--text-muted)">
            Run an agent, then click steps<br>to inspect or branch
          </div>
        </div>
      </div>
    `;
    return;
  }

  const isBranch = !!trace.parent_trace_id;

  container.innerHTML = `
    <div class="panel-header">
      <span class="panel-title"><i data-lucide="clipboard-list" class="inline-icon"></i> Trace Details</span>
    </div>
    <div class="panel-body" id="detail-body">
      <div style="margin-bottom: 16px;">
        <div style="font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); margin-bottom: 4px;">
          TRACE ID
        </div>
        <div style="font-family: var(--font-mono); font-size: 12px; color: var(--accent-bright);">
          ${trace.id.substring(0, 12)}...
        </div>
      </div>

      <div style="margin-bottom: 16px;">
        <div style="font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); margin-bottom: 4px;">
          AGENT
        </div>
        <div style="font-size: 13px;">
          <i data-lucide="${trace.agent_name === 'research' ? 'search' : 'bug'}" class="inline-icon"></i> ${trace.agent_name} agent
        </div>
      </div>

      <div style="margin-bottom: 16px;">
        <div style="font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); margin-bottom: 4px;">
          TASK
        </div>
        <div style="font-size: 12px; line-height: 1.5;">
          ${escapeHtml(trace.task)}
        </div>
      </div>

      <div style="margin-bottom: 16px;">
        <div style="font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); margin-bottom: 4px;">
          STATUS
        </div>
        <span class="trace-status ${trace.status}">${trace.status}</span>
        <span style="font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); margin-left: 8px;">
          ${trace.steps ? trace.steps.length : 0} steps
        </span>
      </div>

      ${isBranch ? `
        <div style="margin-bottom: 16px; padding: 10px; background: rgba(251,146,60,0.1); border: 1px solid rgba(251,146,60,0.3); border-radius: 6px;">
          <div style="font-family: var(--font-mono); font-size: 10px; color: var(--accent-orange); margin-bottom: 4px;">
            <i data-lucide="git-branch" class="inline-icon-small"></i> BRANCHED FROM
          </div>
          <div style="font-size: 11px; color: var(--text-secondary); font-family: var(--font-mono);">
            ${trace.parent_trace_id.substring(0, 12)}...
          </div>
          <button class="step-action-btn" id="btn-diff-parent" style="margin-top: 8px; width: 100%;">
            <i data-lucide="bar-chart-2" class="inline-icon-small"></i> Compare with Original
          </button>
        </div>
      ` : ''}

      <div style="margin-top: 16px; border-top: 1px solid var(--border); padding-top: 16px;">
        <div style="font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); margin-bottom: 8px;">
          STEP BREAKDOWN
        </div>
        ${renderStepBreakdown(trace.steps || [])}
      </div>

      <div id="diff-view-container"></div>
    </div>
  `;

  // Diff with parent
  if (isBranch) {
    const diffBtn = document.getElementById('btn-diff-parent');
    if (diffBtn) {
      diffBtn.addEventListener('click', () => {
        window.__diffTraces(trace.parent_trace_id, trace.id);
      });
    }
  }
}

export function showStepDetail(step) {
  // Currently handled inline in timeline
}

export function showDiffView(diffResult) {
  const container = document.getElementById('diff-view-container');
  if (!container) return;

  const divIdx = diffResult.divergence_step_index;
  const stepsA = diffResult.steps_a || [];
  const stepsB = diffResult.steps_b || [];
  const maxLen = Math.max(stepsA.length, stepsB.length);

  let diffHtml = `
    <div style="margin-top: 16px; border-top: 1px solid var(--border); padding-top: 16px;">
      <div style="font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); margin-bottom: 8px;">
        <i data-lucide="bar-chart-2" class="inline-icon-small"></i> DIFF COMPARISON
      </div>
      <div class="diff-summary">${escapeHtml(diffResult.summary)}</div>
      <div class="diff-columns">
        <div class="diff-col-a">
          <div class="diff-column-header">Original (A)</div>
        </div>
        <div class="diff-col-b">
          <div class="diff-column-header">Branch (B)</div>
        </div>
  `;

  for (let i = 0; i < maxLen; i++) {
    if (i === divIdx) {
      diffHtml += `<div class="divergence-marker"><i data-lucide="zap" class="inline-icon-small"></i> Divergence Point — Step ${i}</div>`;
    }

    const stepA = stepsA[i];
    const stepB = stepsB[i];
    const shared = i < divIdx;

    diffHtml += `<div class="diff-col-a">`;
    if (stepA) {
      diffHtml += `<div class="diff-step ${shared ? 'shared' : 'diverged'}">
        [${stepA.step_type}] ${escapeHtml((stepA.content || '').substring(0, 60))}
      </div>`;
    }
    diffHtml += `</div>`;

    diffHtml += `<div class="diff-col-b">`;
    if (stepB) {
      diffHtml += `<div class="diff-step ${shared ? 'shared' : 'diverged'}">
        [${stepB.step_type}] ${escapeHtml((stepB.content || '').substring(0, 60))}
      </div>`;
    }
    diffHtml += `</div>`;
  }

  diffHtml += `</div></div>`;

  container.innerHTML = diffHtml;
  container.scrollIntoView({ behavior: 'smooth' });
}

function renderStepBreakdown(steps) {
  const counts = {
    thought: 0, tool_call: 0, observation: 0, final_answer: 0, error: 0,
  };
  steps.forEach(s => {
    const t = s.step_type;
    if (t in counts) counts[t]++;
  });

  const colors = {
    thought: 'var(--color-thought)',
    tool_call: 'var(--color-tool)',
    observation: 'var(--color-observation)',
    final_answer: 'var(--color-answer)',
    error: 'var(--color-error)',
  };
  const icons = {
    thought: 'message-square',
    tool_call: 'wrench',
    observation: 'eye',
    final_answer: 'check-circle',
    error: 'x-circle',
  };

  return Object.entries(counts)
    .filter(([_, count]) => count > 0)
    .map(([type, count]) => `
      <div style="display: flex; align-items: center; justify-content: space-between; padding: 4px 0;">
        <span style="font-size: 12px; color: ${colors[type]}; display: flex; align-items: center; gap: 4px;">
          <i data-lucide="${icons[type]}" class="inline-icon-small"></i> ${type.replace('_', ' ')}
        </span>
        <span style="font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary);">
          ${count}
        </span>
      </div>
    `).join('');
}

function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = String(str);
  return div.innerHTML;
}
